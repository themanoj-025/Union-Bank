# Union Bank API Documentation

> **Base URL:** `http://localhost:8000`
> **Interactive Docs:** `http://localhost:8000/docs` (Swagger UI) · `http://localhost:8000/redoc` (ReDoc)
> **OpenAPI Schema:** `http://localhost:8000/openapi.json`

---

## Authentication

All protected endpoints require a Bearer JWT token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens are obtained via the login/register endpoints. Access tokens expire after 15 minutes. Use the refresh endpoint to obtain a new token pair.

---

## API Versions

| Version | Prefix | Envelope | Status |
|---------|--------|----------|--------|
| **v1** | `/api/` | Bare response models | ⚠️ Deprecated — use v2 |
| **v2** | `/api/v2/` | `ApiResponse[T]` envelope | ✅ Current |

### v2 Response Envelope

All v2 endpoints return a standardised envelope:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": { ... }
}
```

---

## Endpoints

### Authentication (`/api/v2/auth`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/api/v2/auth/login` | Customer login | — |
| `POST` | `/api/v2/auth/register` | Register new customer | — |
| `POST` | `/api/v2/auth/admin-login` | Admin login (supports TOTP 2FA) | — |
| `POST` | `/api/v2/auth/refresh` | Refresh access token | Refresh token |

### Customer Account (`/api/v2/account`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v2/account/profile` | Get customer profile | Customer |
| `PUT` | `/api/v2/account/profile` | Update customer profile | Customer |
| `POST` | `/api/v2/account/change-password` | Change password | Customer |
| `POST` | `/api/v2/account/close` | Close account (soft-delete) | Customer |
| `GET` | `/api/v2/account/balance` | Get account balance | Customer |
| `POST` | `/api/v2/account/deposit` | Deposit funds | Customer |
| `POST` | `/api/v2/account/withdraw` | Withdraw funds | Customer |
| `POST` | `/api/v2/account/transfer` | Transfer funds to another account | Customer |

### Transactions (`/api/v2/account/statements`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v2/account/statements` | Get transaction history (cursor-based) | Customer |
| `GET` | `/api/v2/account/statements/mini` | Get mini statement (last 10) | Customer |
| `GET` | `/api/v2/account/statements/keyset` | Keyset-cursor paginated statements | Customer |
| `GET` | `/api/v2/account/export-csv` | Export transactions as CSV | Customer |

### Savings Goals (`/api/v2/savings`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v2/savings` | List savings goals | Customer |
| `POST` | `/api/v2/savings` | Create savings goal | Customer |
| `POST` | `/api/v2/savings/{goal_id}/contribute` | Contribute to a savings goal | Customer |
| `DELETE` | `/api/v2/savings/{goal_id}` | Delete savings goal | Customer |

### Loans (`/api/v2/loans`)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v2/loans` | Loan summary for current customer | Customer |
| `POST` | `/api/v2/loans` | Apply for a loan | Customer |
| `GET` | `/api/v2/loans/{loan_id}` | Get loan details | Customer |
| `POST` | `/api/v2/loans/{loan_id}/pay-emi` | Pay loan EMI | Customer |
| `POST` | `/api/v2/loans/calculate-emi` | Calculate EMI preview | Customer |

### Admin — Accounts

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v2/admin/accounts` | List all accounts (paginated) | Admin |
| `GET` | `/api/v2/admin/accounts/search` | Search accounts by name/email/mobile | Admin |
| `POST` | `/api/v2/admin/accounts/{acc_no}/freeze` | Freeze an account | Admin |
| `POST` | `/api/v2/admin/accounts/{acc_no}/unfreeze` | Unfreeze an account | Admin |
| `DELETE` | `/api/v2/admin/accounts/{acc_no}` | Soft-delete an account | Admin |
| `GET` | `/api/v2/admin/statistics` | Get system statistics | Admin |

### Admin — Loans

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v2/admin/loans` | Loan admin statistics | Admin |
| `GET` | `/api/v2/admin/loans/pending` | List pending loan applications | Admin |
| `POST` | `/api/v2/admin/loans/{loan_id}/approve` | Approve a loan | Admin |
| `POST` | `/api/v2/admin/loans/{loan_id}/reject` | Reject a loan | Admin |
| `GET` | `/api/v2/admin/loans/all` | List all loans | Admin |

### Admin — Transactions & 2FA

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v2/admin/transactions` | View all transactions | Admin |
| `GET` | `/api/v2/admin/2fa/status` | Check 2FA status | Admin |
| `GET` | `/api/v2/admin/2fa/setup` | Generate TOTP secret + provisioning URI | Admin |
| `POST` | `/api/v2/admin/2fa/verify` | Verify TOTP code to enable 2FA | Admin |
| `POST` | `/api/v2/admin/2fa/disable` | Disable 2FA (requires current TOTP) | Admin |

### Utility

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/v2/categories` | List transaction categories | — |
| `POST` | `/api/v2/analyzr/query` | Natural language account query | Customer |
| `GET` | `/api/v2/health` | Health check | — |

### Infrastructure

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/api/health` | v1 health check | — |
| `GET` | `/api/healthz` | Liveness probe | — |
| `GET` | `/api/readyz` | Readiness probe | — |
| `GET` | `/metrics` | Prometheus metrics | — |

---

## Rate Limiting

| Endpoint Category | Limit |
|-------------------|-------|
| Login / Register | 5/min per IP |
| Password operations | 10/min per account |
| Admin actions | 20/min per admin |
| General API | 100/min per IP |

Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## Error Responses

All errors follow a consistent shape:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Email or password is incorrect"
  }
}
```

### Common Error Codes

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 400 | `VALIDATION_ERROR` | Request body failed validation |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT token |
| 401 | `INVALID_CREDENTIALS` | Wrong email/password |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `CONFLICT` | Duplicate resource (e.g. email already registered) |
| 428 | `TOTP_REQUIRED` | TOTP 2FA code required for admin login |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

---

## Security Features

- **RS256 JWT** — Asymmetric signing with private/public key pair
- **Token version invalidation** — Password changes instantly invalidate all sessions
- **TOTP 2FA** — Optional two-factor authentication for admin accounts
- **CSRF origin logging** — Cross-origin requests are logged for monitoring
- **Idempotency keys** — Optional `idempotency_key` on deposit/withdraw/transfer prevents double-spend on retries
- **Soft-delete** — Account deletion preserves transaction history for regulatory compliance
- **Rate limiting** — Per-IP and per-account rate limits via SlowAPI
- **Input validation** — Pydantic models enforce strong passwords, valid emails, and phone formats

---

## Quick Start

```bash
# 1. Start the server
uvicorn unionbank.entrypoints.api.main:app --reload --host 0.0.0.0 --port 8000

# 2. Open interactive docs
open http://localhost:8000/docs

# 3. Register a customer
curl -X POST http://localhost:8000/api/v2/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com", "password": "SecurePass123!", "mobile": "+1234567890"}'

# 4. Login and use the token
curl -X POST http://localhost:8000/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com", "password": "SecurePass123!"}'

# 5. Access protected endpoint
curl http://localhost:8000/api/v2/account/balance \
  -H "Authorization: Bearer <your_token>"
```

---

## Architecture

```
Client → FastAPI (api/main.py)
         ├── /api/v2/* → v2.py router (ApiResponse envelope)
         ├── /api/*    → main.py (legacy v1, deprecated)
         └── /metrics  → Prometheus
              │
              ├── Auth Layer (common.py)
              │   ├── JWT verify (RS256)
              │   ├── Token version check
              │   └── Rate limiting
              │
              ├── DI Container (container.py)
              │   ├── TransactionService
              │   ├── AccountService
              │   ├── AdminService
              │   ├── SavingsGoalService
              │   ├── LoanService
              │   └── AuthService
              │
              └── Repositories (infrastructure/)
                  ├── SqlAlchemyAccountRepository
                  ├── SqlAlchemyTransactionRepository
                  ├── SqlAlchemyRefreshTokenRepository
                  └── SqlAlchemyIdempotencyRepository
```

---

*Generated from FastAPI OpenAPI schema · Last updated: August 2026*
