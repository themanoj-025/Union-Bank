# UNION-BANK- — Folder Structure

```
UNION-BANK-/
├── src/unionbank/                # Core package (src-layout, clean architecture)
│   ├── config.py                 # Settings / env-driven config (single source)
│   ├── domain/                   # Entities, value logic, interest, clock
│   ├── application/              # Use cases: services, interfaces, notifications, async_services
│   ├── entrypoints/              # Adapters that drive the app
│   │   ├── api/                  #   FastAPI: main.py (app), v2.py, common.py, models.py
│   │   └── cli/                  #   CLI: account, admin, bank, main, ui
│   ├── infrastructure/           # DB, repositories, container (DI), cache, metrics, mappers, persistence
│   └── utils/                    # Cross-cutting helpers (auth, hashing, rate-limit, validation, …)
├── frontend/                     # React + Vite SPA
│   ├── src/
│   │   ├── main.jsx              # Vite entry
│   │   ├── App.jsx               # Root component + routing
│   │   ├── api.js                # Backend API client
│   │   ├── context/AuthContext.jsx
│   │   ├── components/           # Shared UI (Header, Footer, Dropdown, ErrorBoundary, …)
│   │   ├── pages/                # Route pages (Home, Dashboard, Auth, Admin/, Transactions/, …)
│   │   └── test/                 # Vitest tests
│   ├── public/                   # Static assets (images, favicon, icons)
│   ├── index.html
│   ├── package.json              # npm scripts + deps
│   └── vite.config.js / vitest.config.js
├── tests/                        # 15 pytest modules + conftest + fakes
├── alembic/                      # DB migrations (versions/, env.py)
├── data/                         # Runtime data (union_bank.db seed + working files)
├── scripts/                      # docker-entrypoint.sh, analyzr.py, migrate_json_to_sqlite.py, load-test/
├── k8s/                          # deployment, hpa, ingress, service manifests
├── monitoring/                   # Prometheus + Grafana dashboards/provisioning
├── docs/                         # Full documentation suite (community, decisions, design, …)
│   ├── migration/                # Migration records
│   └── ...
├── .github/                      # CODEOWNERS, workflows (ci, codeql, commitlint, gitleaks, …)
├── .husky/                       # Git hooks (commit-msg, pre-commit)
├── .pre-commit-config.yaml
├── alembic.ini
├── commitlint.config.js
├── docker-compose.yml / docker-compose.prod.yml
├── Dockerfile                    # Multi-stage; CMD → scripts/docker-entrypoint.sh
├── e2e_test.py                   # End-to-end test driver
├── Makefile                      # dev / test / lint / format / migrate / seed / docker-up
├── package.json                  # Root tooling (husky, commitlint)
├── pyproject.toml                # Packaging + pytest config
├── requirements.txt / requirements-lock.txt
├── seed_data.py                  # DB seeding entry
├── start.bat / test.bat          # Windows convenience scripts
└── .env.example                  # Env template (secrets never committed)
```

## Layout rules

- **Clean architecture enforced by structure**: `domain/` (pure logic) ←
  `application/` (use cases) ← `entrypoints/` + `infrastructure/` (adapters).
- **Frontend and backend are sibling top-level trees** (`frontend/` and
  `src/`); no cross-package imports.
- **Artifacts & runtime data never live in the source tree** — runtime files
  are gitignored (`data/`, `src/unionbank/utils/data/`, `*.db*`); only the
  test-seed `data/union_bank.db` is tracked.
- **Secrets never tracked** — `.env` and `frontend/.env` are gitignored; only
  `.env.example` is committed.
