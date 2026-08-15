# UNION-BANK- — Startup Flow

The system runs as a Dockerized backend + frontend. `scripts/docker-entrypoint.sh`
is the canonical backend boot path (`ENTRYPOINT_TARGET=api`).

## Backend startup (`scripts/docker-entrypoint.sh` → uvicorn)

1. **PYTHONPATH bootstrap** — `export PYTHONPATH=${PYTHONPATH:-}:/app/src` so
   the src-layout package `unionbank` resolves.
2. **Redis wait (optional)** — if `REDIS_URL` is set, poll the host:port
   (30 × 1s) before proceeding; continue without cache if unreachable.
3. **Database init** — `python -c "from unionbank.infrastructure.database import init_db; init_db()"`
   creates the SQLite schema if missing (paths from `config.py`).
4. **Alembic migrations** — if `alembic/versions/*.py` exist, run
   `alembic upgrade head` (initial migration + balance constraint).
5. **App server** — `exec uvicorn unionbank.entrypoints.api.main:app
   --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-4} --proxy-headers`.

   Importing `api.main` triggers:
   a. `unionbank.config` — env loading (incl. `UNION_BANK_TESTING` flag).
   b. Composition root: `infrastructure.container` builds the service
      graph (services → repositories → database/mappers).
   c. FastAPI app creation: auth middleware (JWT), rate-limit middleware
      (Redis-backed), Prometheus instrumentation, CORS.
   d. Router registration incl. `v2.py` endpoints; Pydantic DTOs from
      `entrypoints/api/models.py`.
   e. Ready to serve: `/docs` (OpenAPI), `/api/health`, authenticated
      banking endpoints.

## Frontend startup (dev)

1. `npm install` in `frontend/` → `npm run dev` (Vite dev server).
2. `src/main.jsx` mounts `App.jsx`; router renders pages; `AuthContext`
   restores session from stored JWT and calls `api.js` for data.
3. Vite proxies `/api/*` to the backend (per `vite.config.js`).

## Operational entry points

| Entry | Command |
|---|---|
| API | `uvicorn unionbank.entrypoints.api.main:app` (Makefile `make dev`) |
| CLI | `python -m unionbank.entrypoints.cli.main` (bank/admin/account) |
| Seed | `python seed_data.py` (Makefile `make seed`) |
| Migrate | `alembic upgrade head` (Makefile `make migrate`) |
| Tests | `make test` (`pytest tests/`) |
| E2E | `python e2e_test.py` |
| Load test | `scripts/load-test/locustfile.py` |

## What must exist at startup

- Env keys from `.env.example` (DB path, JWT secret, REDIS_URL optional,
  `UNION_BANK_TESTING` for test mode)
- `alembic/versions/` migrations; `data/union_bank.db` seed for tests
- Redis (optional — app degrades to in-memory rate limiting)
