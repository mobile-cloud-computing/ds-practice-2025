# 📎 Order Executor Working

```
┌──────────────┐     gRPC     ┌────────────────────┐
│ Order Queue  ├────────────▶│  Order Executor     │
└──────────────┘             │  (replicated)       │
                             └──────┬──────────────┘
                                    │
                                    │ gRPC
       ┌────────────────────────────┼────────────────────────────┐
       │                            │                            │
┌───────────────┐         ┌────────────────────┐       ┌────────────────────┐
│ fraud_detection│◀──────▶│ transaction_verif. │◀────▶│    suggestions      │
└───────────────┘         └────────────────────┘       └────────────────────┘
```

### Keeping Orchestrator and Order Executor separate:
1. `orchestrator` is for HTTP requests from frontend.
2. `order_executor` is for background tasks, handled internally in the system.

```
[Frontend Browser] ---> [Orchestrator (Flask)] ---> [Microservices via gRPC]

[Background System / Queue] ---> [Order Executor (Worker)] ---> [Microservices via gRPC]
```

### Dequeues
```
              [ Order Queue ] ← shared (e.g., Redis)
                    ↑
          ┌─────────▼─────────┐
          │                   │
   [order_executor_1]   [order_executor_2]
        (Leader)            (Follower)
          │
     Dequeues + Executes
```

# 📜 Project Documentation

This document explains the architecture and inner workings of the order-processing system involving multiple microservices, Redis-based leader election, and vector clocks.

---

## 🕉 System Model

### 📦 Architecture Type
- **Architecture**: Microservice-based architecture
- **Communication**: Services interact via gRPC
- **Coordination**: Leader election and job coordination via Redis

### 🔗 Components
- **Order Executor**: Multiple replicas, one elected as leader to handle orders.
- **Redis**: Centralized coordination for:
  - Leader election (via `SETNX` pattern)
  - Order queue (`LPUSH`/`LPOP`)
- **Fraud Detection Service**: Validates the legitimacy of an order.
- **Transaction Verification Service**: Verifies payment details.
- **Suggestion Service**: Recommends related books for the order.
- **PostgreSQL**: Stores book and order information.
- **Orchestrator**: Acts as frontend API layer.

### ♻ Flow of Events
1. Client places order via frontend.
2. Order is pushed to Redis queue.
3. OrderExecutor leader pops from queue and dispatches it to the relevant services.
4. Each service responds back with data.
5. Logs are maintained per service for audit/debug.

### 💥 Failure Modes
- **OrderExecutor crash**: Redis automatically allows other replicas to contend for leadership.
- **Redis failure**: Coordination and queue operations halt until Redis is restored.
- **Microservice crash**: gRPC call fails; logged by OrderExecutor and retried/reported.

---

## ♻ Leader Election Diagram

### Algorithm Used: Redis-based lock (`SETNX`)

```
[Initial State]
No leader → All executors try to acquire lock

[Frame 1]
Executor-2 acquires lock:
  Redis key: leader_lock = Executor-2
  Logs: [Executor-2] Became leader

[Frame 2]
Executor-1, Executor-3:
  Check Redis → Not leader
  Logs: [Executor-X] Not leader. Waiting...

[Frame 3]
Executor-2 renews the lock every 10 seconds
If it crashes, key expires → New election happens
```

---

## ⏱ Vector Clocks Diagram

### Scenario: Order is placed and processed through services

```
Processes: E (Executor), F (Fraud), T (Transaction), S (Suggestion)

[Event 1] Order placed by user
E: [1,0,0,0]

[Event 2] Executor sends to Fraud
E: [2,0,0,0] → F: [2,1,0,0]

[Event 3] Executor sends to Transaction
E: [3,1,0,0] → T: [3,1,1,0]

[Event 4] Executor sends to Suggestion
E: [4,1,1,0] → S: [4,1,1,1]

[Event 5] Executor processes responses
E: [5,1,1,1]
```

Each number represents the logical clock of that process. Vector clock updates ensure causality and ordering.

---

## 📌 Notes
- Vector clocks and leader election are simplified representations based on lecture models.
- gRPC ensures reliable structured communication.
- Redis lock + TTL gives fault tolerance during leadership handoff.
- Microservices are loosely coupled and easily scalable.

---

## 📂 Directory Reference
```
/utils/pb/*                  ← Generated gRPC protobufs
/order_executor/src/app.py  ← Leader election and dispatcher
/order_executor/src/debug.py← Flask-based debug server
/fraud_detection/src/*      ← Fraud analysis logic
/suggestions/src/*          ← Book recommendation engine
/transaction_verification/src/* ← Payment check logic
/orchestrator/src/*         ← Main API handler
```

