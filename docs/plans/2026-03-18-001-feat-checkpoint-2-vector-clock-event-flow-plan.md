---
title: "feat: Implement checkpoint-2 vector-clock event flow"
type: feat
status: implemented
date: 2026-03-18
---

# feat: Implement checkpoint-2 vector-clock event flow

## Overview

Implement the second-checkpoint execution model for the distributed bookstore so the system uses:

- orchestrator-generated unique `OrderID`s
- explicit initialization/caching in all backend services
- a partially ordered execution flow with at least 6 events
- event-level vector clock propagation and logging
- fail-fast result propagation back to the orchestrator
- optional final clear-data broadcast using the terminal vector clock

The current codebase already has a useful foundation:

- the orchestrator generates a UUID order id and sends it in gRPC metadata
- all three backend services cache per-order data
- vector clocks and event traces already exist in `utils/vector_clock.py`
- transaction verification currently triggers fraud detection, which then triggers suggestions

However, the implementation is still too coarse for the assignment because each service exposes only one overloaded `Initialize...Order` RPC, initialization is mixed with execution, and the event graph is not yet modeled as distinct causally related events.

## Problem Statement

The assignment requires a true event-based distributed execution model, not just a cached request followed by a mostly linear pipeline. The repo currently falls short in four important ways:

1. gRPC contracts are too coarse.
   `utils/pb/transaction_verification/transaction_verification.proto`, `utils/pb/fraud_detection/fraud_detection.proto`, and `utils/pb/suggestions/suggestions.proto` each define only a single `Initialize...Order` RPC, so individual events are not represented in the service interfaces.

2. Initialization and execution are conflated.
   `transaction_verification/src/app.py` caches the order and immediately runs verification inside `InitializeVerificationOrder`, which does not match the required "cache first, execute later" model.

3. Parallelism is weak and poorly represented.
   The orchestrator submits three init tasks in parallel, but it stamps them with strictly increasing orchestrator ticks, which weakens the concurrency story and makes the resulting vector clocks less convincing.

4. Lifecycle cleanup is missing.
   There is no final clear-order broadcast or vector-clock check before deleting cached order data.

## Proposed Solution

Refactor the system into a two-stage protocol:

1. Initialization stage
   The orchestrator generates a unique `OrderID`, creates the initial vector clock, and dispatches parallel init RPCs to transaction verification, fraud detection, and suggestions. Each service stores the order payload, initializes a per-order vector clock, and returns immediately.

2. Execution stage
   A single orchestrator worker waits on a long-running backend execution path rooted at transaction verification. Backend services then trigger one another through event-specific RPCs that encode a 6-event partial order with real overlap between independent branches.

Chosen event graph:

- `a`: transaction verification checks that the order items list is not empty
- `b`: transaction verification checks mandatory user data
- `c`: transaction verification checks credit-card format
- `d`: fraud detection checks user data for fraud risk
- `e`: fraud detection checks card data for fraud risk
- `f`: suggestions generates recommended books

Chosen partial order:

- `a || b`
- `c` depends on `a`
- `d` depends on `b`
- `c || d` is the main cross-service concurrency that vector clocks should capture
- `e` depends on both `c` and `d`
- `f` depends on `e`

This keeps the implementation close to the assignment example, uses exactly 6 meaningful events, and minimizes extra complexity.

## Technical Approach

### Architecture

Keep the current high-level service topology:

- frontend -> orchestrator over HTTP
- orchestrator -> backend services over gRPC
- backend services also communicate directly over gRPC

Refine responsibility boundaries as follows:

- **Orchestrator**
  - Generates `OrderID`
  - Starts parallel init RPCs
  - Starts exactly one long-lived worker that waits for the final outcome
  - Merges vector clocks and event traces for the HTTP response
  - On completion, optionally broadcasts `ClearOrder`

- **Transaction Verification**
  - Owns events `a`, `b`, and `c`
  - Coordinates the beginning of the execution flow after all services are initialized
  - Returns the final success or failure result to the orchestrator

- **Fraud Detection**
  - Owns events `d` and `e`
  - Receives handoff from transaction verification after upstream checks complete
  - Calls suggestions only when fraud checks pass

- **Suggestions**
  - Owns event `f`
  - Generates the final book recommendations from cached order data

### gRPC Contract Changes

Add explicit event-level RPCs instead of overloading init RPCs.

#### Transaction Verification proto

Add or refactor toward:

- `InitializeVerificationOrder`
- `StartVerificationFlow`
- `CheckItemsNotEmpty`
- `CheckMandatoryUserData`
- `CheckCardFormat`
- `ClearVerificationOrder`

#### Fraud Detection proto

- `InitializeFraudOrder`
- `CheckUserFraud`
- `CheckCardFraud`
- `ClearFraudOrder`

#### Suggestions proto

- `InitializeSuggestionsOrder`
- `GenerateSuggestions`
- `ClearSuggestionsOrder`

Use unary RPCs for all of these. Streaming adds complexity without helping the checkpoint goals.

### Proto Data Availability Fixes

The current proto messages have data gaps that block the event model:

1. **`VerificationRequest` must include items.** Event `a` (check items not empty) requires the order's book list, but the current message only has user/card/address fields. Add a `repeated BookItem items` field to `VerificationRequest` so TV can cache and validate items.

2. **`FraudRequest` must include user data.** Event `d` (check user data fraud) requires name, email, and billing address, but the current message only has `card_number` and `order_amount`. Extend `FraudRequest` (or create a new `InitFraudRequest`) to include user-identifying fields so FD can perform event `d` from cache.

3. **`StartVerificationFlow` response contract.** This is a long-running unary RPC that blocks until the entire a-through-f chain completes. It reuses `VerificationResponse` and tunnels books, final vector clock, and event trace through trailing metadata (`x-suggested-books`, `x-vector-clock`, `x-event-trace`), consistent with the existing pattern.

### Shared Request/Response Shape

To minimize churn, keep `order_id` and vector clock in gRPC metadata, since the repo already uses that pattern in all services.

Standardize request payloads around small explicit messages:

- init requests contain the data each service needs to cache (including the expanded fields above)
- event requests may be mostly empty when the service already has cached state
- clear requests can be an empty body if `order_id` and final vector clock are carried in metadata

Standardize response payloads around:

- `ok` or existing service-specific boolean
- `message` for failure reasons
- optional `books` for suggestions

Keep event traces and final vector clocks in trailing metadata, matching the current implementation style.

### Vector Clock Model

Continue using `utils/vector_clock.py` as the source of truth, but tighten usage rules.

For every init or event RPC:

1. Read `order_id` and incoming vector clock from metadata.
2. Merge incoming clock with the service-local per-order clock.
3. Tick the local service component.
4. Persist the updated local clock for that order.
5. Log the current vector clock for the specific event.
6. Return the updated clock in trailing metadata.

Add a small shared helper layer to remove repeated logic currently spread across:

- `transaction_verification/src/app.py`
- `fraud_detection/src/app.py`
- `suggestions/src/app.py`

Suggested helper responsibilities:

- load cached order or fail with `FAILED_PRECONDITION`
- merge/tick/store the per-order vector clock
- append an event-trace entry
- serialize metadata consistently

### Concurrency Rules

The current orchestrator init stage ticks the orchestrator clock sequentially before each init dispatch. Replace that with a true fan-out model:

- create one parent clock snapshot after `order_id_created`
- dispatch all three init RPCs with the same parent snapshot
- let each service tick its own vector-clock component on receipt

This makes the init-stage concurrency visible in the resulting clocks.

Within the execution stage:

- `a` and `b` can run in parallel in transaction verification
- `c` begins when `a` finishes
- `d` begins when `b` finishes and runs in fraud detection
- `c` and `d` should be allowed to overlap

This overlap is the clearest demonstration that vector clocks are modeling partial order instead of a single linear chain.

### Join-Point Clock Merge at `e`

The most complex vector-clock operation in the flow is the merge before dispatching event `e`. Two concurrent branches produce independent clocks:

- Branch 1: `a → c` produces `clock_c` (TV's local clock after event `c`)
- Branch 2: `b → d` produces `clock_d` (returned from FD after event `d`)

At the join point, TV merges both branch endpoints and ticks before dispatching `e`:

```
clock_for_e = tick(merge_clocks(clock_c, clock_d), "transaction_verification")
```

This merged clock is sent to FD as the incoming clock for event `e`, ensuring the vector clock correctly reflects that `e` causally depends on both `c` and `d`.

### Concurrent Failure Cancellation

When `a` and `b` run in parallel, one branch may fail while the other is still in progress.

Strategy: use a shared cancellation flag within `StartVerificationFlow`.

- If `a` fails: set the flag. The `b` branch checks the flag before dispatching `d` to FD. If `b` has already dispatched `d`, let the in-flight RPC complete but discard the result.
- If `b` fails: set the flag. The `a` branch checks the flag before running `c`.
- If both fail: whichever future completes first sets the failure reason. Accept nondeterminism in which reason is surfaced (both are valid).

After the flag is set, `StartVerificationFlow` short-circuits and returns the failure immediately without dispatching downstream events (`e`, `f`).

### Suggestions Failure Semantics

A failure in event `f` (suggestions generation) is treated as non-fatal. The order is still approved with an empty suggestions list. A warning is logged. This means event `f` is not on the critical path for order approval — only events `a` through `e` determine success or failure.

### Failure Handling

Adopt fail-fast semantics across all stages.

Rules:

- Any init failure is returned to the orchestrator immediately.
- Any event failure aborts downstream work as soon as possible.
- The first failure reason becomes the user-visible denial reason.
- Suggestions are generated only if all earlier checks succeed.

Implementation detail:

- keep a shared cancellation or terminal-state flag in the orchestrator worker logic
- downstream services should check whether the order is already in a terminal failed state before doing expensive work
- late-arriving event RPCs for a cleared order should return `FAILED_PRECONDITION`

### Clear Broadcast Bonus

Implement the bonus cleanup path after the main checkpoint behavior is stable.

Flow:

1. Orchestrator computes final merged vector clock `VCf`.
2. Orchestrator broadcasts `Clear*Order` RPCs to all three services in parallel.
3. Each service compares its local clock for `order_id` against `VCf`.
4. If `local_vc <= VCf`, the service deletes the cached order.
5. Otherwise, it logs and returns a cleanup ordering error.

This should be the final event in the flow for both success and failure paths, **including init-failure scenarios**. If one init RPC fails but the other two succeeded, the orchestrator must still broadcast clear to the services that have cached data. This prevents orphaned cache entries from leaking memory.

## Implementation Phases

### Phase 1: Define the event model and proto contracts

Files:

- `utils/pb/transaction_verification/transaction_verification.proto`
- `utils/pb/fraud_detection/fraud_detection.proto`
- `utils/pb/suggestions/suggestions.proto`

Tasks:

- define event-specific RPCs for the 6 required events
- add clear-order RPCs for the bonus cleanup flow
- standardize request and response messages
- regenerate `_pb2.py`, `_pb2_grpc.py`, and `.pyi` stubs for all services

Success criteria:

- all services compile with the new generated stubs
- there is a one-to-one mapping between the planned business events and the gRPC surface

### Phase 2: Separate initialization from execution

Files:

- `orchestrator/src/app.py`
- `transaction_verification/src/app.py`
- `fraud_detection/src/app.py`
- `suggestions/src/app.py`

Tasks:

- make each `Initialize...Order` RPC cache data and return immediately
- stop `InitializeVerificationOrder` from running the entire verification flow
- persist a per-order record in each service containing cached payload, local vector clock, trace, terminal status, and a set of completed event names
- make missing-cache access fail consistently with `FAILED_PRECONDITION`
- duplicate event RPCs for the same order should be rejected using the completed-events set

Success criteria:

- init calls no longer trigger business logic
- backend services can survive init-before-execute ordering cleanly
- duplicate event calls are detected and rejected

### Phase 3: Implement the 6-event partial-order execution flow

Files:

- `transaction_verification/src/app.py`
- `fraud_detection/src/app.py`
- `suggestions/src/app.py`

Tasks:

- implement `a`, `b`, and `c` in transaction verification
- implement `d` and `e` in fraud detection
- implement `f` in suggestions
- add a coordination entrypoint such as `StartVerificationFlow`
- ensure `c` and `d` receive merged predecessor clocks and can overlap
- propagate failure reasons and merged clocks through every handoff

Recommended event ownership:

- `StartVerificationFlow` in transaction verification creates two worker futures for `a` and `b`
- when `a` finishes, transaction verification runs or triggers `c`
- when `b` finishes, transaction verification calls fraud detection for `d`
- once `c` and `d` are both complete, transaction verification calls fraud detection for `e`
- fraud detection calls suggestions for `f`
- final result propagates suggestions -> fraud detection -> transaction verification -> orchestrator

Success criteria:

- the flow has at least 6 named events
- at least one meaningful concurrent region exists and is reflected in vector clocks
- only successful end-to-end orders produce recommended books

### Phase 4: Tighten vector-clock and trace handling

Files:

- `utils/vector_clock.py`
- `transaction_verification/src/app.py`
- `fraud_detection/src/app.py`
- `suggestions/src/app.py`
- `orchestrator/src/app.py`

Tasks:

- introduce helper functions so every event uses the same merge/tick/record pattern
- log vector clock state on every init, event, dispatch, receive, terminal response, and clear operation
- make orchestrator merge returned clocks deterministically before replying to the frontend
- preserve an `eventTrace` that is useful for demonstration during grading

Success criteria:

- logs clearly show the current vector clock for each event and order id
- event trace is readable and consistent with the intended partial order

### Phase 5: Orchestrator worker lifecycle and cleanup

Files:

- `orchestrator/src/app.py`

Tasks:

- keep three short-lived init workers and one long-lived execution worker
- fail fast when any init worker fails
- terminate or cancel remaining workers once the final outcome is known
- optionally broadcast the final clear-order RPCs using `VCf`

Success criteria:

- the orchestrator no longer waits on unnecessary workers after terminal success or failure
- clear-order broadcast happens only after the terminal result is known

### Phase 6: Simplify dummy logic and documentation

Files:

- `fraud_detection/src/app.py`
- `suggestions/src/app.py`
- `README.md`

Tasks:

- replace or isolate AI-dependent logic with deterministic dummy logic for checkpoint grading reliability
- keep validation and fraud logic simple and explicit
- update the README so it matches the actual event graph and RPC names
- document the chosen partial order and cleanup semantics

Rationale:

The assignment explicitly says the inner functionality is not important and suggests using dummy logic. Using deterministic checks will make the flow easier to demonstrate and less likely to fail because of networked AI calls or prompt variability.

Success criteria:

- demo behavior is stable without depending on GenAI output quality or latency
- documentation matches the final implementation

## Alternative Approaches Considered

### 1. Keep the current overloaded `Initialize...Order` RPC model

Rejected because it hides the event graph inside service internals and does not satisfy the assignment's request for extra gRPC functions for each event.

### 2. Make the orchestrator call every event directly

Possible, but not preferred. It would satisfy the RPC requirement, but it keeps too much orchestration logic centralized and weakens the "relations between intermediate events" requirement. The current codebase is already trending toward backend-to-backend chaining, so this would be a step backward.

### 3. Use streaming RPCs for event progress

Rejected as unnecessary complexity. Unary RPCs are enough for the checkpoint and align with the existing codebase.

## System-Wide Impact

### Interaction Graph

Primary success path:

- frontend `POST /checkout`
- orchestrator generates `OrderID`
- orchestrator sends parallel init RPCs to TV, FD, and Suggestions
- orchestrator calls `StartVerificationFlow`
- TV runs `a` and `b`
- TV runs `c` after `a`
- TV triggers FD `d` after `b`
- TV triggers FD `e` after both `c` and `d`
- FD triggers Suggestions `f`
- Suggestions returns books
- FD returns fraud outcome plus books
- TV returns final validity plus books
- orchestrator returns HTTP response
- orchestrator optionally broadcasts `Clear*Order`

Primary failure path:

- any init failure returns immediately to the orchestrator
- any event failure short-circuits downstream execution
- orchestrator returns denial reason
- orchestrator optionally broadcasts `Clear*Order`

### Error & Failure Propagation

Expected failure classes:

- `FAILED_PRECONDITION` for missing cached order or out-of-order event
- service-specific validation failures returned as normal business responses
- transport errors from gRPC surfaced to orchestrator as terminal denial reasons

Requirements:

- do not swallow gRPC transport errors
- preserve the first meaningful business failure message
- log the order id and vector clock when a failure is detected

### State Lifecycle Risks

Main risks:

- one service caches an order while another init fails
- a failure occurs after some downstream services have already advanced their local clocks
- a late RPC arrives after a service has cleared local state
- duplicate execution RPCs race on the same `order_id`

Mitigations:

- per-order locks or atomic state transitions around cache updates
- explicit terminal status in each cached order record
- idempotent clear-order handling
- consistent `FAILED_PRECONDITION` behavior for stale or already-cleared orders

### API Surface Parity

The following interfaces all need to stay aligned:

- orchestrator client calls to each backend stub
- service-to-service gRPC calls between TV -> FD and FD -> Suggestions
- README diagrams and RPC documentation
- frontend expectations for `orderId`, `status`, `reason`, `suggestedBooks`, `vectorClock`, and `eventTrace`

### Integration Test Scenarios

Minimum end-to-end scenarios:

1. Successful order
   Valid payload completes all 6 events and returns suggested books plus final vector clock.

2. Failure during `a`
   Empty items list fails early, prevents `c`, `d`, `e`, and `f`, and returns a denial reason.

3. Failure during `b`
   Missing required user data fails before fraud user-data check.

4. Failure during `e`
   Earlier validation succeeds, fraud detection fails at the combined fraud stage, and suggestions never run.

5. Cleanup ordering check
   Clear broadcast succeeds only when local service clocks are `<= VCf`.

6. Out-of-order RPC
   Call an execution event before init and verify the service returns `FAILED_PRECONDITION`.

## SpecFlow Analysis

### Resolved flow decisions

- The orchestrator blocks on all init acknowledgements before starting `StartVerificationFlow`.
- Duplicate event RPCs for the same `order_id` are rejected (per-order completed-events set).
- `eventTrace` entries are appended in receipt order; causal order can be reconstructed from vector clocks.
- Cleanup errors are logged in service logs, not shown to the frontend user.
- Suggestions failure (event `f`) is non-fatal — order is approved with empty book list.
- When both `a` and `b` fail concurrently, whichever finishes first sets the denial reason.
- The clear broadcast runs after any terminal result, including init failures.
- At the `c`/`d` join point: `clock_for_e = tick(merge(clock_c, clock_d), "transaction_verification")`.

### Open questions

- Define how long a service should wait before declaring another service unavailable (timeout/deadline strategy).
- This checkpoint favors deterministic dummy logic over LLM-based behavior.

## Acceptance Criteria

### Functional Requirements

- [x] The orchestrator generates a unique `OrderID` for every checkout request.
- [x] The orchestrator sends parallel init RPCs to transaction verification, fraud detection, and suggestions.
- [x] Each backend service caches order data and initializes a per-order vector clock without executing business logic during init.
- [x] The system implements at least 6 named backend events with the planned partial order.
- [x] At least one meaningful concurrent region exists in the event graph and is visible in vector clocks.
- [x] Each event is exposed through an explicit gRPC function rather than a single overloaded init RPC.
- [x] Vector clocks are updated, propagated, and logged on every event for the relevant `order_id`.
- [x] Any failure in an intermediate event is propagated back to the orchestrator immediately.
- [x] Successful orders return recommended books to the frontend.
- [x] Failed orders do not execute unnecessary downstream events.
- [x] The orchestrator stops or cancels worker threads once the terminal result is known.
- [x] Bonus: the orchestrator broadcasts a final clear-order command with `VCf`, and services clear only when `local_vc <= VCf`.

### Non-Functional Requirements

- [x] The implementation uses deterministic dummy logic where possible so demos are stable.
- [x] gRPC metadata usage stays within documented custom-metadata constraints.
- [x] Service logs are sufficient to explain the vector-clock progression during grading.

### Quality Gates

- [x] Protobuf stubs regenerate cleanly for all services.
- [ ] `docker compose up --build` starts all services successfully.
- [ ] Manual end-to-end verification covers success, early failure, late failure, and cleanup paths.
- [x] `README.md` reflects the final event graph, RPC names, and flow semantics.

## Success Metrics

- The implementation can be demonstrated in a grading session without relying on external AI responses.
- Logs clearly show the causal relationship between events and the concurrent overlap between `c` and `d`.
- The final HTTP response consistently includes `orderId`, terminal `status`, `reason`, final `vectorClock`, and `eventTrace`.

## Dependencies & Prerequisites

- Docker Compose environment remains the main execution path.
- Protobuf generation must keep working in all Dockerfiles.
- The team should decide whether to preserve the current GenAI code paths behind feature flags or replace them outright for checkpoint 2.

## Risk Analysis & Mitigation

### Risk: race conditions in per-order state

Mitigation:

- use per-order locking or a lock around cache state transitions
- centralize vector-clock update logic

### Risk: vector clocks do not visibly show concurrency

Mitigation:

- fork init RPCs from the same orchestrator parent clock
- ensure `c` and `d` are allowed to overlap across services

### Risk: cleanup clears state too early

Mitigation:

- run cleanup only after terminal result
- compare `local_vc` against `VCf` before deletion

### Risk: AI-backed fraud/suggestions introduce nondeterminism

Mitigation:

- replace them with deterministic placeholder logic for checkpoint 2
- if AI is retained, isolate it behind a simple fallback path

## Documentation Plan

Update `README.md` to include:

- the final 6-event partial order
- the list of new RPCs in each service
- an updated sequence diagram
- a brief explanation of vector-clock propagation
- cleanup-broadcast behavior if implemented

## Sources & References

### Internal References

- `orchestrator/src/app.py` - current worker model, init dispatch, and response assembly
- `transaction_verification/src/app.py` - current cache plus execute coupling and fraud handoff
- `fraud_detection/src/app.py` - current cache plus execute coupling and suggestions handoff
- `suggestions/src/app.py` - current cached suggestions model
- `utils/vector_clock.py` - existing vector-clock and trace helpers
- `README.md` - current documented architecture and event flow

### External References

- gRPC Python basics: https://grpc.io/docs/languages/python/basics/
- gRPC metadata guide: https://grpc.io/docs/guides/metadata/
- gRPC core concepts: https://grpc.io/docs/what-is-grpc/core-concepts/

### Notes From Local Research

- No relevant brainstorm document was found in `docs/brainstorms/`.
- No institutional learnings were found in `docs/solutions/` or `docs/learnings/`.
- The existing code already contains useful vector-clock scaffolding, so the work is a refactor and expansion rather than a full rewrite.
