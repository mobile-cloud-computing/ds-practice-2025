# Distributed Bookstore System

An online bookstore checkout system built with a microservices architecture. The frontend sends checkout requests to an orchestrator, which coordinates transaction verification, fraud detection, and book suggestions via gRPC.

## Architecture

```mermaid
graph TD
    A[User] --> B[Frontend<br/>Port: 8080<br/>Nginx / HTTP]
    B --> C[Orchestrator<br/>Port: 8081<br/>Flask REST API]
    C -->|1. gRPC| D[Transaction Verification<br/>Port: 50052]
    C -->|2. gRPC| E[Fraud Detection<br/>Port: 50051]
    C -->|3. gRPC| F[Suggestions<br/>Port: 50053]
```

All backend services run in Docker containers. The orchestrator calls the three gRPC services **sequentially**: verification must pass before fraud detection runs, and suggestions are fetched last.

## Services

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| **Frontend** | 8080 | HTTP (Nginx) | Static HTML/JS checkout form served by Nginx |
| **Orchestrator** | 8081 | REST (Flask) | Receives checkout requests, coordinates gRPC calls |
| **Transaction Verification** | 50052 | gRPC | Validates email, card number, CVV, expiration date, and billing address |
| **Fraud Detection** | 50051 | gRPC | Flags orders with amount > 1000 or card prefix "999" |
| **Suggestions** | 50053 | gRPC | Returns a static list of recommended books |

## Checkout Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant O as Orchestrator
    participant TV as Transaction Verification
    participant FD as Fraud Detection
    participant S as Suggestions

    U->>F: Submit order form
    F->>O: POST /checkout (JSON)
    O->>TV: gRPC VerifyTransaction
    TV-->>O: is_valid + message
    alt Transaction invalid
        O-->>F: Order Denied (reason from TV)
        F-->>U: Yellow/amber error with specific message
    end
    O->>FD: gRPC CheckFraud
    FD-->>O: is_fraud
    alt Fraud detected
        O-->>F: Order Denied (fraud)
        F-->>U: Red error
    end
    O->>S: gRPC GetSuggestions
    S-->>O: list of books
    O-->>F: Order Approved + suggestions
    F-->>U: Green success with suggested books
```

## Validation Rules (Transaction Verification)

| Field | Rule |
|-------|------|
| Email | Must match `[^@]+@[^@]+\.[^@]+` |
| Card number | Exactly 16 digits |
| CVV | 3 or 4 digits |
| Expiration date | Format `MM/YY`, must not be expired (year/month comparison) |
| Billing street | At least 5 characters |
| Billing city | At least 2 characters |
| Billing state | Alphabetic characters only |
| Billing ZIP | Exactly 5 digits |
| Billing country | At least 2 characters |

## Fraud Detection Rules

| Rule | Trigger |
|------|---------|
| High amount | `order_amount > 1000` (based on total item quantity) |
| Suspicious card | Card number starts with `"999"` |

## How to Run

```bash
docker compose up --build
```

The frontend will be available at [http://localhost:8080](http://localhost:8080).

## Known Limitations

- Suggestions are static and do not depend on the items in the cart
- Order amount for fraud detection is based on item quantity sum, not actual prices
- Item list is hardcoded in the frontend (Book A, Book B)
- Only US ZIP codes (5 digits) are supported for billing address
- The orchestrator assigns a static order ID ("12345")
