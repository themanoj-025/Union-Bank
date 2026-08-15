# UNION-BANK- — System Architecture

UNION-BANK- is a full-stack **banking management system**: a FastAPI REST
backend with clean-architecture layering, a React/Vite SPA frontend, Alembic
migrations, Redis-backed caching/rate-limiting, Prometheus metrics, and
Kubernetes + Docker deployment.

## High-level components

```
                     ┌──────────────────────────────────────┐
                     │        frontend/  (React SPA)        │
                     │  pages · components · AuthContext    │
                     └──────────────────┬───────────────────┘
                                        │ HTTPS /api/* (JWT)
                     ┌──────────────────▼───────────────────┐
                     │    src/unionbank/entrypoints/api     │
                     │     FastAPI app (main.py, v2.py)     │
                     └──────────────────┬───────────────────┘
                                        │
     ┌───────────────────┬──────────────┴───────────────┬───────────────────┐
     ▼                   ▼                              ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  ┌──────────────┐
│ application/ │  │ infrastructure│ │        utils/            │  │ entrypoints/ │
│  use cases   │  │ DB, repos,   │ │ auth, rate-limit, hashing │  │    cli/      │
│ (services)   │  │ DI, cache    │ │ validation, csv_export    │  │  (bank, …)   │
└──────┬───────┘  └──────┬───────┘  └──────────────────────────┘  └──────────────┘
       │                 │
       └─────────────────┴────────────────────────────┐
                                                      ▼
                                        ┌──────────────────────────┐
                                        │      domain/  (pure)     │
                                        │ entities · interest ·    │
                                        │ clock · value objects    │
                                        └──────────────────────────┘
```

## Component responsibilities

| Component | Responsibility |
|---|---|
| `src/unionbank/domain/` | Pure business entities (`entities`), interest/balance logic (`interest`), time abstraction (`clock`) — no I/O |
| `src/unionbank/application/` | Use cases: `services` (sync) and `async_services` (async), `interfaces` (ports), `notifications` |
| `src/unionbank/infrastructure/` | Adapters: `database` (SQLite init), `repositories`/`async_repositories`, `container`/`async_container` (DI), `cache` (Redis), `metrics` (Prometheus), `mappers`, `persistence`, `backward_compat` |
| `src/unionbank/entrypoints/api/` | FastAPI REST API (`main.py` app factory, `v2.py`, `common.py` deps, `models.py` DTOs) — JWT auth, rate limiting |
| `src/unionbank/entrypoints/cli/` | Terminal entry points (`bank`, `admin`, `account`) with shared `ui` helpers |
| `src/unionbank/utils/` | Cross-cutting: `cookie_auth`, `token_security`, `hashing`, `rate_limit`/`account_rate_limit`, `validation`, `formatting`, `csv_export`, `file_io`, `logger`, `savings`, `categories`, `analyzr_core` |
| `src/unionbank/config.py` | Single source of truth for settings (env-driven, TESTING flag) |
| `frontend/` | React SPA: `api.js` client, `AuthContext` (JWT session), 25+ pages, shared components |
| `tests/` | 15 pytest modules: unit, integration, API integration, property-based, security, migrations, smoke |
| `alembic/` | Migrations: initial schema + balance check constraint |
| `scripts/` | `docker-entrypoint.sh` (wait-for-redis → init_db → alembic → uvicorn), `migrate_json_to_sqlite.py`, `analyzr.py`, locust load tests |
| `k8s/` | deployment, hpa (autoscaling), ingress, service manifests |
| `monitoring/` | Prometheus scrape config + Grafana dashboard |
| `seed_data.py` | Seeds the database (Makefile `make seed`) |

## Key architectural decisions

- **Clean architecture (ports & adapters)** — `domain` depends on nothing;
  `application` defines interfaces; `infrastructure` and `entrypoints`
  implement adapters; DI containers (`container.py`) wire them together.
- **src-layout package** — `PYTHONPATH=src` (CI and `docker-entrypoint.sh`
  both set it); run via `uvicorn unionbank.entrypoints.api.main:app`.
- **Single API surface** — `entrypoints/api/main.py` is the canonical
  FastAPI app; `v2.py` layers additional endpoints; both reuse
  `application.*` services (no duplicated business logic).
- **Environment-driven config** — `config.py` + `.env.example`; `UNION_BANK_TESTING=1`
  switches test mode; secrets (`.env`) are gitignored.
- **Migration + seeding pipeline** — `docker-entrypoint.sh` runs
  `init_db()` then `alembic upgrade head`, then starts uvicorn with
  `--workers ${UVICORN_WORKERS:-4}`.
- **Observability** — Prometheus metrics (`infrastructure/metrics.py`),
  Grafana dashboard, structured logging (`utils/logger.py`), k8s HPA on
  resource signals.
