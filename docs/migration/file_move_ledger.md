# UNION-BANK- — File Move Ledger

## This pass (2026-08-11)

| Old path | New path | Category | Reason | Risk | Verified |
|---|---|---|---|---|---|
| `docs/migration_summary.md` | `docs/migration/migration_summary.md` | Meta/docs | Consolidate migration records under `docs/migration/` per enterprise standard | Low (docs only) | ✅ no inbound refs; `git mv` preserved history |

## Prior pass (v5.0, already committed)

The v5.0 restructuring (commit `5f80f0f`) moved the application into the
current clean-architecture skeleton (`src/unionbank/` with domain/application/
infrastructure/entrypoints), the React app into `frontend/`, added `k8s/`,
`monitoring/`, `scripts/`, and consolidated the legacy flat modules. Its own
record is preserved at `docs/migration/migration_summary.md`.

## Non-moves (documented decisions)

| Path | Decision | Reason |
|---|---|---|
| `src/unionbank/**` | keep | Clean-architecture src-layout; launch contract depends on it (`PYTHONPATH=src`) |
| `frontend/**` | keep | Standard React/Vite tree; package.json build contract |
| `tests/**` | keep | Already canonical with conftest/fakes |
| `alembic/**`, `data/**`, `scripts/**`, `k8s/**`, `monitoring/**` | keep | Canonical locations already |
| `data/union_bank.db` | keep tracked | Test/seed database (intentional per repo convention) |
| `docs/decisions/ADR-0001-*` (×2) | keep + flag | Duplicate ADR number; renaming breaks cross-references — backlog item |
| `F:tempserver.log`, `nul`, `frontend/F:tempvite.log` | leave (untracked) | Windows redirect artifacts on disk only — flagged in backlog, never committed |
| `src/unionbank/data/*`, `src/unionbank/utils/data/*` | leave (untracked) | Runtime data inside source tree — gitignored; flagged for later cleanup |
| `.pytest_cache/`, `.ruff_cache/`, `frontend/dist/`, `src/unionbank.egg-info/` | leave (untracked) | Build/cache artifacts, correctly gitignored |
