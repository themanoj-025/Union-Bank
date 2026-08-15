# UNION-BANK- — Module Dependency Map

## Core package (src/unionbank) — clean-architecture dependency rule

Dependencies point **inward only**: `entrypoints` + `infrastructure` may use
`application`, `domain`, `utils`, `config`; `application` may use `domain`;
`domain` depends on nothing.

```
config.py            ← imported by every layer (settings, TESTING flag)
domain/*             ← imported by application (entities in use cases) and
                       infrastructure (repositories/mappers map to entities)
application/interfaces.py  ← ports; implemented by infrastructure.repositories
application/services.py / async_services.py
                     ← depend on application.interfaces + domain
application/notifications.py ← depends on config/logger
infrastructure/container.py / async_container.py
                     ← **composition root**: wires services + repositories
                       (imported by entrypoints/api/main.py)
infrastructure/database.py   ← depends on config
infrastructure/repositories.py, async_repositories.py
                     ← implement application.interfaces; depend on database,
                       mappers, domain
infrastructure/cache.py      ← Redis cache adapter (config)
infrastructure/metrics.py    ← Prometheus instrumentation (config)
infrastructure/backward_compat.py ← legacy flat-module shims (uses utils/domain)
utils/*              ← leaf helpers; imported by application, infrastructure,
                       entrypoints; some legacy code imports them directly
entrypoints/api/*    ← imports application services + infrastructure.container
                       + utils (auth, rate-limit) + config
entrypoints/cli/*    ← imports application.services + domain + utils
```

## Frontend → backend

```
frontend/src/api.js           → REST calls to backend /api/* (JWT bearer)
frontend/src/context/AuthContext.jsx → login/session state, calls api.js
frontend/src/pages/*.jsx      → components + api.js/AuthContext (no direct
                                backend imports)
frontend/src/components/*     → pure UI (except PrivateRoute which uses AuthContext)
```

## Cross-boundary rules (why)

- **No `infrastructure`/`entrypoints` imports inside `domain` or `application`** —
  the DI containers exist precisely to keep the inner layers framework-free
  and testable with `tests/fakes.py`.
- **Both entrypoints share `application` services** — the FastAPI layer and
  the CLI layer never re-implement business logic.
- **`utils/` is the pragmatic exception** — legacy modules (`analyzr_core`,
  `file_io`, `savings`) are consumed directly by entrypoints; documented in
  `infrastructure/backward_compat.py` and flagged as technical debt.
- **No circular imports** between package layers. The historical risk point
  (api ↔ services ↔ repositories) is resolved by the container: `api/main.py`
  imports the container, which imports repositories, which import interfaces.

## External dependencies

- **Backend**: FastAPI + uvicorn, SQLite (stdlib), Redis (cache/rate-limit),
  PyJWT, passlib/bcrypt (hashing), prometheus-client, alembic (migrations),
  hypothesis (property tests), pytest
- **Frontend**: React 18, Vite, react-router, Vitest + Testing Library
- **Infra**: Docker Compose, Kubernetes, Prometheus + Grafana, Locust (load tests)
