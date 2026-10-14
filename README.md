# Union Bank Management System

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <img src="assets/logo.svg" width="280" alt="Union Bank Management System logo — blue bank tile and wordmark">
  </picture>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python version requirement: 3.11 or newer">
  <img src="https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white" alt="FastAPI version: 0.115 or newer">
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0%2B-d71f00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy version: 2.0 or newer">
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white" alt="React version: 19">
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL version: 16">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License: MIT"></a>
</p>

> A concurrent-safe banking core API and multi-interface management platform built with atomic financial transactions, defense-in-depth authentication (JWT + TOTP 2FA + CSRF), async SQLAlchemy over SQLite and PostgreSQL, Prometheus observability, and a 733-test automated validation suite.

**Status:** Prototype portfolio project. Built to demonstrate senior backend engineering and concurrent financial system design; not intended for production banking operations without an independent security audit.

<!-- TODO[L2-01]: Add Grafana observability dashboard screenshot to docs/assets/screenshots/grafana.png (owner: Maintainer) -->

<p align="center">
  <a href="#what-this-demonstrates">What This Demonstrates</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#tech-stack">Tech Stack</a> •
  <a href="#engineering-case-studies">Case Studies</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#testing">Testing</a> •
  <a href="docs/reference/SELF_AUDIT.md">Self-Audit</a>
</p>

---

## Screenshots

| Marketing Landing Page | Customer Login & 2FA | Interactive API Documentation |
|:---:|:---:|:---:|
| ![Marketing landing page showing headline and navigation](docs/assets/screenshots/landing.png) | ![Customer authentication screen with login credentials](docs/assets/screenshots/login.png) | ![FastAPI Swagger documentation interface with route list](docs/assets/screenshots/api-docs.png) |

---

## Quick Facts

| Dimension | Specification | Evidence Source |
|:---|:---|:---|
| Project Type | Full-Stack Web Application / Banking Core API | `pyproject.toml`, `frontend/package.json` |
| Primary Language | Python (>= 3.11), JavaScript / JSX | `pyproject.toml`, `frontend/package.json` |
| Primary Frameworks | FastAPI, React 19, Typer, SQLAlchemy 2.0 (Async) | `pyproject.toml`, `frontend/package.json` |
| Primary Database | SQLite (development), PostgreSQL 16 (Docker / production) | `src/unionbank/config.py`, `docker-compose.yml` |
| Cache & Broker | Redis 7.2 (optional caching and rate limiting) | `docker-compose.yml`, `src/unionbank/config.py` |
| Test Suite | 733 collected tests across unit, integration, and property suites | `tests/` directory (`pytest`) |
| License | MIT License | `LICENSE` file |

---

## What This Demonstrates

Union Bank implements a shared Domain-Driven Design (DDD) service core exposed across three distinct entry points:

| Interface | Technology | Primary Audience | Key Capability |
|:---|:---|:---|:---|
| **REST API** | FastAPI (`/api/v2/` envelope format) | External clients, SPAs, integrations | 50+ endpoints with JWT, TOTP, rate-limiting, and idempotency |
| **Web Dashboard** | React 19 + Vite SPA | Account holders and bank administrators | Visual account management, transfers, statements, and 2FA |
| **CLI Client** | Typer + Rich | Bank staff, administrators, batch operators | Interactive terminal-based account opening, transactions, and admin controls |

All business rules (ledger immutability, double-entry consistency, interest calculation, and account freezing) reside exclusively in `src/unionbank/application/` and `src/unionbank/domain/`, preventing duplicated logic across interfaces.

---

## Architecture

```mermaid
flowchart TB
    subgraph Clients["Entrypoints"]
        WEB["React 19 SPA (Vite)"]
        CLI["CLI Tool (Typer + Rich)"]
        API["FastAPI App (/api/v2/)"]
    end

    subgraph Security["Defense-in-Depth Middleware"]
        RATE["SlowAPI Rate Limiter"]
        CSRF["Double-Submit CSRF Cookie"]
        AUTH["RS256/HS256 JWT & TOTP 2FA"]
    end

    subgraph Application["Application Layer (Domain-Driven Design)"]
        AUTH_SVC["AuthService"]
        TX_SVC["TransactionService"]
        ACC_SVC["AccountService"]
        ADMIN_SVC["AdminService"]
        LOAN_SVC["LoanService"]
    end

    subgraph Domain["Domain Layer"]
        ENTITIES["Entities (Account, Transaction, Loan)"]
        INTEREST["Interest Engine & Clock"]
    end

    subgraph Infrastructure["Infrastructure & Persistence"]
        REPOS["SQLAlchemy Repositories (Async / Sync)"]
        DB[("Database (PostgreSQL 16 / SQLite)")]
        CACHE[("Redis Cache")]
        PROM["Prometheus Metrics (/metrics)"]
    end

    WEB --> API
    CLI --> Application
    API --> Security --> Application
    Application --> Domain
    Application --> Infrastructure
    REPOS --> DB
    REPOS --> CACHE
    API --> PROM
```

*Data flow summary: User requests pass through defense-in-depth middleware (rate limiting, CSRF validation, and JWT/TOTP authentication) to application services. Application services coordinate domain logic and persist atomic balance updates through SQLAlchemy repositories to PostgreSQL or SQLite, while emitting Prometheus metrics.*

---

## Tech Stack

### Backend
- **Runtime:** Python 3.11+
- **API Framework:** FastAPI (v0.115+) with Uvicorn
- **ORM / Database Access:** SQLAlchemy 2.0 (Asyncio) with `asyncpg` and `psycopg2-binary`
- **Schema Migrations:** Alembic
- **CLI Interface:** Typer and Rich
- **Security & Cryptography:** `python-jose` (JWT), `passlib` (bcrypt), `cryptography` (Fernet token encryption)
- **Observability:** Prometheus client (`/metrics`), structured logging with `structlog`

### Frontend
- **Framework:** React 19 (`^19.2.7`) with React Router 7
- **Build Tool:** Vite (`^8.3.2`)
- **Styling & UI:** Tailwind CSS, Framer Motion, Lucide React icons
- **Testing & Quality:** Vitest, Testing Library, Oxlint

### Infrastructure & Operations
- **Containerization:** Docker multi-stage builds (`Dockerfile`), Docker Compose
- **Databases:** PostgreSQL 16, SQLite 3
- **Cache:** Redis 7.2
- **Orchestration Manifests:** Kubernetes deployment, service, ingress, and HPA (`k8s/`)

---

## Engineering Case Studies

### Atomic Transactions Under Concurrency
Financial transfers debit one account and credit another. A partial failure (power cut, network timeout, database lock conflict) must never leave funds deducted without crediting the destination.

- **Mechanism:** Transfers execute inside atomic database transactions managed by `TransactionService` using database savepoints and transaction rollback handlers.
- **Verification:** Automated fault-injection tests in [`tests/test_features.py`](tests/test_features.py) simulate mid-execution exceptions prior to commit, verifying that both sender and recipient balances remain byte-for-byte unchanged. Concurrent transfer tests in [`tests/test_integration_part2.py`](tests/test_integration_part2.py) verify that simultaneous transactions avoid lost updates.

### Defense in Depth
The authentication model uses multiple complementary security barriers:
- **Authentication:** Short-lived JWT access tokens (15-minute expiration) paired with refresh tokens.
- **Two-Factor Authentication:** TOTP (RFC 6238) algorithm with encrypted seed secrets in the database via Fernet symmetric keys.
- **CSRF Protection:** Double-submit cookie verification for state-changing browser requests.
- **Rate Limiting:** IP-based and account-specific rate limits (e.g., 5 login attempts before temporary lockout) powered by SlowAPI.
- **Idempotency Keys:** Money-movement endpoints accept unique idempotency keys in request headers to protect against accidental double-submissions.

### Observability and Resilience
- **Prometheus Metrics:** Standardized application metrics available at `/metrics`, tracking HTTP request duration (p50, p95, p99), endpoint hit rates, and database query timings.
- **Structured Logging:** Context-aware JSON logs via `structlog`, embedding `request_id`, user identity, and execution timestamps without leaking credentials or card numbers.
- **Circuit Breakers:** External dependency calls wrap execution inside `pybreaker` circuit breakers (`circuit_breaker.py`) to prevent cascade failures.

---

## Prerequisites

Before running the application locally, ensure you have installed:
- **Python:** Version 3.11 or newer (`python --version`)
- **Node.js:** Version 20.19 or newer (`node --version`) and `npm` (for the React web dashboard)
- **Docker & Docker Compose:** Optional, required for containerized PostgreSQL and Redis setup

---

## Quick Start

### Local Development (SQLite)

This path runs the application with a local SQLite database requiring zero external services.

#### 1. Clone the repository
```bash
git clone https://github.com/themanoj-025/Union-Bank.git
cd Union-Bank
```

#### 2. Configure Python environment

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

**On Linux / macOS (Bash):**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

#### 3. Set environment configuration
```bash
cp .env.example .env
```
*(On Windows cmd: `copy .env.example .env`). Edit `.env` to configure your `JWT_SECRET` and `FLASK_SECRET_KEY`.*

#### 4. Apply database migrations
```bash
alembic upgrade head
```

#### 5. Seed initial demo data (Optional)
```bash
python seed_data.py
```

#### 6. Start the FastAPI REST service
```bash
uvicorn unionbank.entrypoints.api.main:app --reload --port 8000
```

Expected terminal output:
```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```
Access the interactive Swagger documentation at `http://localhost:8000/docs`.

#### 7. Start the Web Dashboard (Separate terminal)
```bash
cd frontend
npm install
npm run dev
```

Expected terminal output:
```text
  VITE v8.3.2  ready in 280 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```
Open `http://localhost:5173` in your browser.

#### 8. Launch the Terminal CLI (Optional)
```bash
python -m unionbank.entrypoints.cli.main
```

---

### Full Stack (Docker Compose)

To run the complete production-like environment with PostgreSQL 16, Redis 7.2, and the FastAPI application in containers:

```bash
# 1. Prepare environment variables
cp .env.example .env

# 2. Build and launch services
docker compose up --build -d

# 3. View logs
docker compose logs -f api
```

The containerized API will be live on `http://localhost:8000`. To stop containers:
```bash
docker compose down
```

---

## Configuration

Configuration values are parsed in [`src/unionbank/config.py`](src/unionbank/config.py) from environment variables or a local `.env` file:

| Variable | Required | Default | Description | Secret |
|:---|:---:|:---|:---|:---:|
| `JWT_SECRET` | **Yes** (Prod/Dev) | None | Secret key used for signing JWT authentication tokens (min 32 chars) | **Yes** |
| `FLASK_SECRET_KEY` | **Yes** (Prod/Dev) | None | Secret key used for signing web session cookies | **Yes** |
| `DATABASE_URL` | No (Dev) / Yes (Prod) | `None` (falls back to local SQLite) | Database connection URL (`postgresql+asyncpg://user:pass@host:5432/dbname`) | **Yes** |
| `REDIS_URL` | No | `None` | Redis connection URL (`redis://redis:6379/0`) for distributed caching | **Yes** |
| `JWT_ALGORITHM` | No | `HS256` (Dev) / `RS256` (Prod) | Cryptographic algorithm for JWT signatures (`RS256` requires RSA keys) | No |
| `TOKEN_ENCRYPTION_KEY` | No | `""` | Fernet symmetric key for encrypting stored TOTP secrets | **Yes** |
| `CORS_ALLOWED_ORIGINS` | No | `http://localhost:5000,http://localhost:8000,http://localhost:5173,...` | Comma-separated list of allowed browser origins | No |
| `ENV` | No | `development` | Runtime environment: `development`, `testing`, or `production` | No |
| `DB_POOL_SIZE` | No | `10` | SQLAlchemy PostgreSQL connection pool size | No |
| `DB_MAX_OVERFLOW` | No | `20` | Max overflow connections above pool size | No |

---

## Project Structure

```text
UNION-BANK-/
├── alembic/                       # Alembic schema migrations and version history
│   └── versions/                  # Individual database migration scripts
├── assets/                        # Brand vectors and light/dark mode SVGs
├── docs/                          # Architecture documentation, audits, and assets
│   ├── assets/screenshots/        # UI captures (landing, login, API docs)
│   └── reference/                 # Architectural deep-dives and SELF_AUDIT.md
├── frontend/                      # React 19 + Vite web dashboard application
│   ├── src/                       # Components, pages, hooks, and services
│   └── package.json               # Frontend dependencies and npm scripts
├── k8s/                           # Kubernetes deployment, service, ingress, and HPA
├── monitoring/                    # Prometheus scrape configuration and Grafana dashboards
├── src/unionbank/                 # Core backend application package (DDD layout)
│   ├── application/               # Application service layer (transfer, auth, accounts)
│   ├── domain/                    # Pure business entities, interest logic, clock
│   ├── entrypoints/               # Delivery mechanisms:
│   │   ├── api/                   # FastAPI application, v2 envelope routes, models
│   │   └── cli/                   # Typer terminal client (bank, admin, account menus)
│   ├── infrastructure/            # Repositories, database session, cache, metrics
│   └── config.py                  # Dataclass configuration and fail-fast environment checks
├── tests/                         # Automated test suite (733 tests across 38 modules)
├── .env.example                   # Annotated template for environment variables
├── docker-compose.yml             # Local multi-container Docker composition
├── Dockerfile                     # Multi-stage container build definition
├── pyproject.toml                 # Python package configuration and tool settings
├── requirements.txt               # Pinned project dependencies
└── seed_data.py                   # Script to populate database with demo accounts
```

---

## Testing

The test suite validates data consistency, fault recovery, API route contracts, and security rules across 38 modules:

```bash
# Set testing environment variables to bypass strict secret checks during test runs
# Windows (PowerShell):
$env:UNION_BANK_TESTING="1"; $env:JWT_SECRET="test"; $env:FLASK_SECRET_KEY="test"; pytest tests/ -v

# Linux / macOS (Bash):
UNION_BANK_TESTING=1 JWT_SECRET=test FLASK_SECRET_KEY=test pytest tests/ -v
```

### Specialized Test Execution

```bash
# Run tests with code coverage report
pytest tests/ -v --cov=unionbank --cov-report=term-missing

# Run property-based invariant tests (Hypothesis)
pytest tests/test_property_based.py -v

# Run password leak defense checks (ensures response models never serialize passwords)
pytest tests/test_password_leak.py -v --no-cov

# Run documentation anchor, link, and fence verification
python .github/scripts/lint_readme.py
```

---

## Limitations and Threat Model

- **Simulated Financial Environment:** This codebase is an educational and portfolio demonstration of banking architecture. It does not integrate with external payment networks (SWIFT, ACH, SEPA) or real banking clearing houses.
- **Auditing Requirement:** While cryptographic controls (JWT, TOTP, bcrypt) and transactional rollback patterns adhere to standard engineering best practices, this software has not undergone external third-party penetration testing or compliance certification (PCI-DSS / SOC 2).
- **SQLite Concurrency:** In default local development mode, SQLite provides thread-level locking. For concurrent multi-client load testing, run against PostgreSQL (`docker compose up`).

---

## Contributing

Contributions, feedback, and issue reports are welcome! Please review [CONTRIBUTING.md](./CONTRIBUTING.md) before submitting pull requests.

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/improved-resilience`).
3. Commit your changes following Conventional Commits (`git commit -m 'feat: add idempotency key cache'`).
4. Ensure all tests and linters pass (`pytest tests/` and `python .github/scripts/lint_readme.py`).
5. Open a Pull Request.

---

## Security

Please report vulnerabilities confidentially according to our security policy in [SECURITY.md](./SECURITY.md). Do not open public issues for suspected security exploits.

---

## License

This project is licensed under the terms of the MIT License. See [LICENSE](./LICENSE) for the full text.
