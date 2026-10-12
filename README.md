<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg" />
    <img src="assets/logo.svg" width="280" alt="Union Bank Management System logo — blue bank tile and wordmark" />
  </picture>
</p>

<h1 align="center">Union Bank Management System</h1>

<p align="center">
  <strong>Concurrent-safe banking core API with atomic transaction ledgering, defense-in-depth security, and multi-interface access.</strong>
</p>

<p align="center">
  <a href="https://github.com/themanoj-025/Union-Bank/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/themanoj-025/Union-Bank/ci.yml?branch=main&label=CI" alt="CI Status" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License MIT" /></a>
  <a href="https://github.com/themanoj-025/Union-Bank/stargazers"><img src="https://img.shields.io/github/stars/themanoj-025/Union-Bank?style=social" alt="GitHub Stars" /></a>
  <a href="https://github.com/themanoj-025/Union-Bank/issues"><img src="https://img.shields.io/github/issues/themanoj-025/Union-Bank?style=flat-square" alt="GitHub Issues" /></a>
  <a href="https://github.com/themanoj-025/Union-Bank/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square" alt="PRs Welcome" /></a>
</p>

---

## Overview

Union Bank is an institutional-grade, concurrency-safe banking core platform engineered to demonstrate high-reliability financial systems design. It pairs ACID transactional ledger updates with defense-in-depth cryptographic controls (RS256 JWT, TOTP 2FA, CSRF double-submit protection, and request idempotency).

All interfaces — terminal CLI, React 19 web banking SPA, and FastAPI REST endpoints — communicate through a unified domain and application service architecture, ensuring total consistency across money movement workflows.

---

## Table of Contents

- [Key Features](#key-features)
- [Architecture & Domain Model](#architecture--domain-model)
- [Supported Interfaces](#supported-interfaces)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Quick Start](#installation--quick-start)
- [Security Architecture](#security-architecture)
- [Configuration](#configuration)
- [Testing & Fault Injection](#testing--fault-injection)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

---

## Key Features

- **Strictly Atomic Transactions**: Money movements run inside isolated database transactions with automated compensating rollbacks; proven safe against simulated mid-write crashes.
- **Defense-in-Depth Security**: Enforces asymmetric RS256 JWTs with token rotation, RFC 6238 TOTP two-factor authentication, and signed httpOnly cookies.
- **Idempotent API Execution**: Every financial transfer accepts a unique idempotency key preventing duplicate fund withdrawals under network retries.
- **Comprehensive Observability**: Out-of-the-box Prometheus metrics exporter, OpenTelemetry distributed tracing hooks, and structured JSON logs.
- **Asynchronous Task Workers**: Background job orchestration backed by Redis queues with Dead Letter Queue handling.

---

## Architecture & Domain Model

```text
               Client Ingress (Web SPA / CLI / API)
                                │
                                ▼
         FastAPI Layer (src/unionbank/entrypoints/api)
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
  Auth & Security       Idempotency Gate        Rate Limiting
  (RS256 + TOTP)        (Redis Key Store)       (SlowAPI Limits)
       │                        │                        │
       └────────────────────────┼────────────────────────┘
                                │
                                ▼
                     Application Services
           (src/unionbank/application/services)
                                │
                                ▼
                     Domain Ledger Entities
              (src/unionbank/domain/entities)
                                │
                                ▼
                     Async SQLAlchemy ORM
                   (PostgreSQL 16 / SQLite)
```

---

## Supported Interfaces

| Interface | Implementation | Target Audience |
| :--- | :--- | :--- |
| **Terminal CLI** | Typer + Rich (`unionbank.entrypoints.cli`) | System administrators, audit officers, automated batch pipelines |
| **Web Dashboard** | React 19 + TypeScript SPA (`frontend/`) | Online banking retail customers and branch operations staff |
| **REST API** | FastAPI 0.135+ (`unionbank.entrypoints.api`) | Multi-interface core backend and programmatic integrations |

---

## Project Structure

```text
UNION-BANK-/
├── frontend/               # React 19 + Vite web banking single-page app
├── src/
│   └── unionbank/          # Core Python domain package
│       ├── application/    # Application use-case services and workflows
│       ├── domain/         # Core business entities and ledger constraints
│       ├── entrypoints/    # FastAPI REST server and Typer CLI commands
│       │   ├── api/        # REST routes, schemas, and main.py entry
│       │   └── cli/        # Command-line interface definitions
│       ├── infrastructure/ # Database repositories, cache, and external adapters
│       └── utils/          # Encryption, hashing, and token helpers
├── tests/                  # Pytest unit, integration, and fault-injection suites
├── alembic/                # Database migration revisions
├── docker-compose.yml      # Multi-container orchestration (API, Frontend, DB, Redis)
├── pyproject.toml          # Build backend and quality tool configuration
├── requirements.txt        # Backend dependencies
└── README.md               # Project documentation
```

---

## Prerequisites

- **Python**: `>= 3.11`
- **Node.js**: `>= 20.0` (required for web frontend)
- **Database**: PostgreSQL 16 (or SQLite for local development)
- **Redis**: `>= 7.0` (for token revocation and idempotency locks)

---

## Installation & Quick Start

### 1. Clone & Set Up Backend

```bash
# Clone repository
git clone https://github.com/themanoj-025/Union-Bank.git
cd Union-Bank

# Create virtual environment
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt

# Run migrations
alembic upgrade head
```

### 2. Configure Environment

```bash
cp .env.example .env
```

### 3. Launch Services

**Run FastAPI Backend**:
```bash
uvicorn unionbank.entrypoints.api.main:app --host 0.0.0.0 --port 8000 --reload
```
*Access interactive Swagger documentation at http://localhost:8000/docs.*

**Run React Web Banking Interface**:
```bash
cd frontend
npm install
npm run dev
```
*Access web interface at http://localhost:5173.*

**Run Command-Line Banking Interface**:
```bash
python -m unionbank.entrypoints.cli.main --help
```

---

## Security Architecture

- **RS256 Asymmetric Tokens**: API access tokens signed with private keys; microservices verify using public keys.
- **Hardware/Software TOTP**: Compatible with Google Authenticator, 1Password, and Authy.
- **State-Changing CSRF Gates**: Enforces double-submit cookie validation across browser sessions.
- Refer to [SECURITY.md](SECURITY.md) for vulnerability disclosure protocols.

---

## Configuration

| Environment Variable | Default | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./unionbank.db` | Development relational database URI |
| `DATABASE_URL_POSTGRES`| `postgresql+asyncpg://...`| Production PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Cache, idempotency lock, and worker broker |
| `JWT_SECRET` | `""` | Signing secret for access tokens |
| `TOTP_SECRET` | `""` | TOTP issuer secret seed |
| `CSRF_SECRET` | `""` | Cryptographic secret for signing CSRF tokens |
| `LOG_LEVEL` | `info` | Logging verbosity |

---

## Testing & Fault Injection

The test suite includes dedicated concurrency and fault-injection suites to verify ledger durability under chaos conditions:

```bash
# Run complete test suite (386+ tests)
pytest tests/ -v

# Run fault-injection and atomicity tests
pytest tests/test_atomicity.py -v
```

---

## Roadmap

- [x] Concurrent-safe ledger transfers with rollback guarantees
- [x] RS256 JWT, TOTP 2FA, and double-submit CSRF security
- [x] Prometheus metrics and OpenTelemetry instrumentation
- [x] Unified service layer powering CLI, Web, and REST API
- [ ] Multi-region active-active database failover <!-- TODO: Track via GitHub issue -->
- [ ] ISO 20022 financial messaging format integration <!-- TODO: Track via GitHub issue -->

---

## Contributing

Contributions are welcomed! Please review [CONTRIBUTING.md](CONTRIBUTING.md) for branch and commit standards.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Support

- 🐛 **Issue Tracker**: [GitHub Issues](https://github.com/themanoj-025/Union-Bank/issues)
- 💡 **Discussions & Pull Requests**: [GitHub Pull Requests](https://github.com/themanoj-025/Union-Bank/pulls)
