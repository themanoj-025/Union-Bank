# UNION-BANK- — Package & Module Inventory

## Backend package: `unionbank` (src/unionbank)

| Module | Responsibility |
|---|---|
| `__init__.py` | Package marker |
| `config.py` | Environment-driven settings (DB path, JWT secret, Redis URL, TESTING flag) — single source of truth |
| `domain/` | Pure business logic |
| `domain/entities.py` | Core entities (Account, User, Transaction, …) |
| `domain/interest.py` | Interest & balance computation rules |
| `domain/clock.py` | Time abstraction (testable clock) |
| `application/` | Use-case layer |
| `application/services.py` | Synchronous business services |
| `application/async_services.py` | Asynchronous variants |
| `application/interfaces.py` | Ports/repository contracts |
| `application/notifications.py` | Notification use cases |
| `entrypoints/api/` | FastAPI REST API |
| `entrypoints/api/main.py` | Canonical app factory (`uvicorn unionbank.entrypoints.api.main:app`) |
| `entrypoints/api/v2.py` | Additional endpoint group |
| `entrypoints/api/common.py` | Shared FastAPI dependencies (auth, rate-limit) |
| `entrypoints/api/models.py` | Pydantic request/response DTOs |
| `entrypoints/cli/` | Terminal interface |
| `entrypoints/cli/bank.py` | Bank CLI commands |
| `entrypoints/cli/admin.py` | Admin CLI commands |
| `entrypoints/cli/account.py` | Account CLI commands |
| `entrypoints/cli/main.py` | CLI dispatcher |
| `entrypoints/cli/ui.py` | CLI rendering helpers |
| `infrastructure/` | Adapters |
| `infrastructure/database.py` | SQLite init/connection |
| `infrastructure/repositories.py` | Repository implementations (sync) |
| `infrastructure/async_repositories.py` | Repository implementations (async) |
| `infrastructure/container.py` | DI composition root (sync) |
| `infrastructure/async_container.py` | DI composition root (async) |
| `infrastructure/cache.py` | Redis cache adapter |
| `infrastructure/metrics.py` | Prometheus metrics instrumentation |
| `infrastructure/mappers.py` | ORM/entity ↔ domain mapping |
| `infrastructure/persistence.py` | Persistence helpers |
| `infrastructure/backward_compat.py` | Legacy flat-module shims |
| `utils/` | Cross-cutting helpers |
| `utils/cookie_auth.py`, `utils/token_security.py` | Session/JWT security |
| `utils/hashing.py` | Password hashing |
| `utils/rate_limit.py`, `utils/account_rate_limit.py` | Rate limiting |
| `utils/validation.py` | Input validation |
| `utils/formatting.py` | Display formatting |
| `utils/csv_export.py` | CSV export helpers |
| `utils/file_io.py` | File IO helpers |
| `utils/logger.py` | Logging setup |
| `utils/savings.py` | Savings-plan logic |
| `utils/categories.py` | Transaction categories |
| `utils/analyzr_core.py` | Analyzer engine (legacy, used by scripts/analyzr.py) |

## Frontend (frontend/)

| Path | Responsibility |
|---|---|
| `src/main.jsx` | Vite entry |
| `src/App.jsx` | Root component + route tree |
| `src/api.js` | Backend API client (fetch + JWT) |
| `src/context/AuthContext.jsx` | Auth session state provider |
| `src/components/` | Header, Footer, Dropdown, CurrencyDropdown, ErrorBoundary, Skeleton, `Auth/PrivateRoute` |
| `src/pages/` | 25+ route pages (Home, Dashboard, Personal, Business, Loans, Security, Admin/*, Auth/*, Transactions/*, …) |
| `src/test/` | Vitest tests (ErrorBoundary, Header, PrivateRoute) + setup |

## Tests (tests/)

15 pytest modules — `test_api_integration`, `test_integration`, `test_services`,
`test_utils`, `test_features`, `test_security`, `test_edge_cases`,
`test_property_based`, `test_migrations`, `test_smoke`, `test_coverage_gaps`,
`test_password_leak`, `test_analyzr` + `conftest.py`, `fakes.py`.

## Non-package trees

| Path | Purpose |
|---|---|
| `alembic/` | Migrations (initial schema + balance check constraint) |
| `scripts/` | `docker-entrypoint.sh`, `analyzr.py`, `migrate_json_to_sqlite.py`, `load-test/locustfile.py` |
| `data/` | Runtime data (seed DB tracked; working files gitignored) |
| `k8s/` | Deployment, HPA, ingress, service manifests |
| `monitoring/` | Prometheus config + Grafana dashboard/provisioning |
| `docs/` | Community, decisions (ADR), design, product, project, reference, technical, migration |
