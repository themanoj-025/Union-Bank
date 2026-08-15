# UNION-BANK- — Old Tree → New Tree

UNION-BANK- reached the enterprise skeleton in the earlier v5.0 restructuring
pass (commit `5f80f0f`). This migration pass consolidates the migration record
and completes the Phase-6 documentation suite.

## Tree changes in this pass

```
Before                                After
──────                                ─────
docs/migration_summary.md      →      docs/migration/migration_summary.md
docs/architecture.md (3-line stub)    docs/architecture.md (full architecture doc)
docs/folder_structure.md (stub,       docs/folder_structure.md (annotated tree;
  listed non-existent backend/)         corrected — backend is src/unionbank)
—                                     docs/module_dependency.md        (new)
—                                     docs/startup_flow.md             (new)
—                                     docs/package_overview.md         (new)
—                                     docs/migration/old_tree_to_new_tree.md (new)
—                                     docs/migration/file_move_ledger.md     (new)
```

## No-code-move rationale

The application code already conforms to the target skeleton:

- `src/unionbank/` — src-layout package with clean-architecture layers
  (`domain` / `application` / `infrastructure` / `entrypoints` / `utils`)
- `frontend/` — standard React/Vite tree (components, pages, context, test)
- `tests/` — 15 pytest modules incl. property-based and security suites
- `alembic/`, `data/`, `scripts/`, `k8s/`, `monitoring/`, `docs/` — canonical dirs
- Root holds only canonical metadata (Dockerfile, compose, Makefile,
  pyproject, requirements, package.json, seed_data.py, e2e_test.py, .env.example)

Moving any of it would break the documented launch contract
(`uvicorn unionbank.entrypoints.api.main:app`, `scripts/docker-entrypoint.sh`,
`PYTHONPATH=src`) with zero benefit — same precedent as AegisAI, Emotion-Lens
and Tamasha.

## Flagged, not changed (see backlog)

- `docs/decisions/ADR-0001-consolidate-codebase.md` + `ADR-0001-consolidate-service-layer.md`
  — duplicate ADR number; renaming would break cross-references.
- Untracked Windows artifacts on disk: `F:tempserver.log`, `nul`,
  `frontend/F:tempvite.log` — junk from botched redirects; not committed.
- Runtime data duplicated in `src/unionbank/utils/data/` and `src/unionbank/data/`
  — untracked leftovers; tracked seed is only `data/union_bank.db`.
