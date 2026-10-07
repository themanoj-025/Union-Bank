# AGENTS.md — UNION-BANK-

> Canonical project instructions. Pointers like `CLAUDE.md` or
> `.github/copilot-instructions.md` should say "See AGENTS.md".

---

## Project overview

**UNION-BANK-** — a banking core services platform. Core components:

- **API** — FastAPI / Spring service for banking operations.
- **Web / App** — frontend for account management and transactions.
- **Services** — backend microservice suite.
- **Model** — risk / fraud detection models.

Stack: Python 3.11+ · FastAPI · PostgreSQL · React.

---

## Exact commands

```bash
# Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Lint / typecheck / test
make lint
pre-commit run --all-files
python -m mypy . --ignore-missing-imports
python -m pytest tests/ -v --cov=. --cov-fail-under=70

# Run
uvicorn api.main:app --reload
```

---

## Folder map

| Path | Purpose |
|------|---------|
| `api/` | FastAPI application (routes, services) |
| `services/` | Backend microservice suite |
| `dashboard/` | Reporting UI |
| `model/` | Risk / fraud detection |
| `tests/` | pytest suite |
| `.github/workflows/` | CI (ruff, mypy, pytest, gitleaks, trivy) |

## Do / don't

- **Do** treat all financial transactions as critical-path and idempotent.
- **Do not** commit `.env` files.
- **Do not** commit PII, account numbers, or transaction amounts.

## Security rules

- **No secrets in the repository**; `gitleaks` CI gate gates on hits.
- **PII and money movement data must be masked/encrypted** before any file
  leaves the sandbox.
- Transaction integrity must be audited on every change.

## AI-assistance convention

Commits authored by AI must carry the trailer:

```text
AI-Assisted: yes | no | partial
```

See `.gitmessage` for the template. Do not rewrite historic commits
retroactively.
