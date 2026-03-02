---
title: "feat: Finalize Distributed System for Checkpoint 1"
type: feat
status: completed
date: 2026-03-02
---

# Finalize Distributed System for Checkpoint 1

## Overview

Complete all six checkpoint-1 requirements for the distributed systems bookstore project: finish implementation, document code, verify Docker setup, add system logs, commit changes, and create the `checkpoint-1` git tag.

## Current State

The project has 5 services (frontend, orchestrator, fraud_detection, transaction_verification, suggestions) all with basic working implementations. The main gaps are:

- **Logging:** 3 of 4 backend services use `print()` instead of Python's `logging` module
- **Documentation:** `docs/` directory is empty; diagrams exist on a separate branch
- **Docker:** transaction_verification Dockerfile missing protobuf compilation step
- **Minor bugs:** expired default date in frontend, version inconsistency, bare except clause

## Implementation Plan

### Phase 1: Fix Critical Bugs (Docker/Build)

These must be fixed first since they affect whether the system runs correctly.

#### 1.1 Fix transaction_verification Dockerfile

**File:** `transaction_verification/Dockerfile`

The Dockerfile does not run `grpc_tools.protoc` to generate protobuf stubs at startup, unlike all other services. It relies on pre-committed `_pb2.py` files. Add the protoc compilation step to the CMD, matching the pattern used by other services.

```dockerfile
CMD python -m grpc_tools.protoc -I utils/pb/transaction_verification \
    --python_out=utils/pb/transaction_verification \
    --pyi_out=utils/pb/transaction_verification \
    --grpc_python_out=utils/pb/transaction_verification \
    utils/pb/transaction_verification/transaction_verification.proto \
    && python utils/other/hotreload.py "transaction_verification/src/app.py"
```

#### 1.2 Align grpcio version in suggestions service

**File:** `suggestions/requirements.txt`

Change `grpcio==1.73.1` to `grpcio==1.78.0` to match all other services.

#### 1.3 Fix expired default expiration date in frontend

**File:** `frontend/src/index.html` (line 39)

Change `value="12/25"` to `value="12/28"` so the default form submission doesn't fail for graders.

#### 1.4 Fix expiration date comparison bug

**File:** `transaction_verification/src/app.py` (lines 38-49)

Currently `datetime.strptime(request.expiration_date, "%m/%y")` parses "03/26" as March 1, 2026 00:00:00, so a card valid through March 2026 gets rejected on March 2. Fix to compare against end-of-month (add one month to the parsed date, or compare year/month only).

#### 1.5 Fix bare except clause

**File:** `transaction_verification/src/app.py` (line 45)

Change `except:` to `except ValueError:` to avoid catching SystemExit/KeyboardInterrupt.

---

### Phase 2: Add System Logs

Replace all `print()` statements with proper Python `logging` module usage. Add meaningful log messages for service interactions.

#### 2.1 fraud_detection/src/app.py

- Add `import logging` and `logging.basicConfig(level=logging.INFO)`
- Replace `print()` on line 36 (fraud check) with `logging.info()` — **mask card number** (show only last 4 digits)
- Replace `print()` on line 56 (server start) with `logging.info()`
- Add logging for the fraud decision result (is_fraud true/false)

#### 2.2 suggestions/src/app.py

- Add `import logging` and `logging.basicConfig(level=logging.INFO)`
- Replace `print()` on line 19 (request received) with `logging.info()`
- Replace `print()` on line 40 (server start) with `logging.info()`
- Add logging for number of suggestions returned

#### 2.3 transaction_verification/src/app.py

- Add `import logging` and `logging.basicConfig(level=logging.INFO)`
- Replace `print()` on line 100 (server start) with `logging.info()`
- **Add logging inside the VerifyTransaction method** — this is the most complex service and currently has zero logging in its validation logic:
  - Log incoming request receipt (mask sensitive fields)
  - Log each validation step result (email, card format, CVV, expiration, billing address)
  - Log the final verdict (is_valid + message)

#### 2.4 orchestrator/src/app.py

- Replace the stray `print()` on line 144 with `logging.info()`

---

### Phase 3: Documentation

#### 3.1 Create system documentation

**File:** `docs/README.md`

Write concise documentation covering:
- **System architecture** — Mermaid diagram showing services and communication (adapt from `origin/ck1/diagrams` branch, but update to match actual implementation flow: sequential verification → fraud → suggestions)
- **Service descriptions** — what each service does, its port, its gRPC contract
- **Checkout flow** — sequence diagram showing the actual request flow
- **Validation rules** — what transaction_verification checks
- **How to run** — `docker compose up --build`
- **Known limitations** — static suggestions, quantity-based fraud amount, hardcoded items

**Important:** Do NOT merge the `origin/ck1/diagrams` branch (it deletes services). Manually incorporate the diagram content and update it to match current implementation.

#### 3.2 Add inline code comments to key service entry points

Add a brief docstring to each gRPC handler and the main checkout endpoint (4 functions total):
- `orchestrator/src/app.py` — `checkout()` function: explain the sequential call chain (verify → fraud → suggestions)
- `transaction_verification/src/app.py` — `VerifyTransaction()`: summarize what fields are validated
- `fraud_detection/src/app.py` — `CheckFraud()`: explain the two fraud rules (amount threshold, card prefix)
- `suggestions/src/app.py` — `GetSuggestions()`: note that suggestions are currently static

One docstring per function. Do not comment individual lines.

---

### Phase 4: Differentiate Denial Reasons in Frontend

Currently, all "Order Denied" results look identical — the user has no idea *why* the order was denied. The orchestrator has two distinct denial paths (transaction verification failure vs fraud detection), but the frontend shows the same red box for both.

#### 4.1 Include denial reason in orchestrator responses

**File:** `orchestrator/src/app.py`

- Transaction verification failure (line 148-156): already has `"reason": "Invalid transaction data"`. Improve to include the specific message from the verification service (e.g., "Invalid email format", "Card expired").
- Fraud detection denial (line 173-177): add a `"reason": "Fraud detected"` field to the response.
- Approved orders: add `"reason": ""` or omit the field.

#### 4.2 Display denial reason in frontend

**File:** `frontend/src/index.html` (lines 132-142)

Update the response rendering to show the denial reason when present:
- **Transaction verification failure:** show in yellow/amber (e.g., `bg-yellow-100 text-yellow-800`) with the specific validation error message
- **Fraud detected:** show in red (e.g., `bg-red-100 text-red-700`) with "Fraud detected" message
- **Approved:** show in green as currently

Use the `reason` field from the response to determine the visual style. Use complete Tailwind class names (not dynamic interpolation) to ensure they work with the CDN.

---

### Phase 5: Docker Verification

#### 5.1 Full rebuild and test

Run `docker compose down && docker compose up --build` and verify:
- [ ] All 5 services start without errors
- [ ] Frontend loads at http://localhost:8080
- [ ] Default form submission results in "Order Approved" (after fixing expiration date)
- [ ] Invalid data (e.g., bad email) results in "Order Denied"
- [ ] Fraud trigger (card starting with "999") results in "Order Denied"
- [ ] "Test Suggestions Service" button returns book list
- [ ] Verification failure shows yellow/amber UI with specific error message
- [ ] Fraud denial shows red UI with "Fraud detected" message
- [ ] All services emit structured logs (not print statements)

---

### Phase 6: Commit and Tag

#### 6.1 Commit all changes

Stage and commit all changes with a descriptive message.

#### 6.2 Merge to master (if on branch)

Ensure all work is on the `master` branch since grading likely checks master.

#### 6.3 Create checkpoint-1 tag

```bash
git tag checkpoint-1
git push origin checkpoint-1
```

---

## Acceptance Criteria (Required)

These map directly to the six checkpoint requirements:

- [ ] All services start successfully with `docker compose up --build`
- [ ] Frontend connects to orchestrator and displays checkout results
- [ ] Default frontend form values produce a successful "Order Approved" result
- [ ] All backend services use Python `logging` module (no `print()` statements)
- [ ] transaction_verification logs each validation step
- [ ] `docs/README.md` contains architecture diagram, service descriptions, and checkout flow
- [ ] Expiration date validation handles end-of-month correctly
- [ ] All services use consistent grpcio version (1.78.0)
- [ ] transaction_verification Dockerfile compiles protobuf stubs at startup
- [ ] Frontend shows distinct visuals for verification failure (yellow/amber) vs fraud denial (red) vs approved (green)
- [ ] Git tag `checkpoint-1` exists on master branch

## Dependencies & Risks

- **Risk:** The `origin/ck1/diagrams` branch diverges significantly from master and deletes services — must NOT be merged directly. Only copy diagram content manually.
- **Risk:** After fixing expiration date logic, existing test scenarios may behave differently.
- **Dependencies:** Docker must be running for verification phase.

## Out of Scope (Future Checkpoints)

- Parallel gRPC calls from orchestrator (concurrent.futures)
- Context-aware suggestions based on cart items
- gRPC deadlines/timeouts
- Processing unused frontend fields (comment, shipping, gift wrapping)
- Request body validation at orchestrator level
- Non-US postal code support
