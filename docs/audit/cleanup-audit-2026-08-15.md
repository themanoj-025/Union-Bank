# UNION-BANK- — Documentation Folder Cleanup & De-LLM-ification Audit (2026-08-15)

## 1. Executive Summary

Scope: full `docs/` tree — root docs, `community/`, `decisions/` (ADR-0001…
0006), `design/`, `product/`, `project/`, `reference/` (BASELINE_METRICS,
BASELINE_VERSIONS, CASE_STUDY, CURRENT_STATE, E2E_TEST_STRATEGY, INVENTORY,
RESUME_BULLETS, RUNBOOK, SELF_AUDIT, THREAT_MODEL, TS_MIGRATION, openapi.json,
Glossary), `technical/`, `migration/`, `audit/`. Docs are specific to the
actual system (real ADRs with dates, threat model, baseline metrics, runbook).
Reads as human-curated. Two items flagged for owner decision (ADR numbering
collision already tracked in-repo; personal RESUME_BULLETS doc); no
auto-changes.

## 2. Urgent: Leaked Secrets/Credentials Found

None. Example payloads use `ada@example.com` / `s3cret!` — obviously fake.

## 3. LLM/AI Fingerprints Removed

None. The `SELF_AUDIT.md` "## Conclusion" heading is a genuine technical
audit-conclusion section (with real scores 4.6/10 → …), not essay filler.

## 4. Structural Changes

None. `reference/openapi.json` is toolchain-generated API reference
(preserved).

## 5. Duplicate Content Consolidated

None identical. **ADR-0001 numbering collision** (two files, see §14) is
already flagged in the repo's own migration records as a backlog item.

## 6. Contradictions Found (manual review, not auto-resolved)

None substantive. The two ADR-0001 files cover different decisions
(codebase-tree consolidation vs service-layer consolidation) — content
compatible, numbering collides.

## 7. Boilerplate/Template Cruft Removed

None.

## 8. Dead Links Fixed/Removed

None. Link scanner clean.

## 9. README / CONTRIBUTING / CONSTITUTION Review

No `docs/README.md` index; top-level docs serve as entry points (acceptable).
`reference/RESUME_BULLETS.md` is personal-portfolio content (see §14).

## 10. Security/Privacy Findings

None. `reference/THREAT_MODEL.md` is a genuine threat model.

## 11. Consistency Fixes Applied

None required.

## 12. Files Modified

- `docs/audit/cleanup-audit-2026-08-15.md` — added (this report)

## 13. Files/Folders Deleted

None.

## 14. Remaining Manual Review Items

1. **ADR-0001 numbering collision (Tier 2/3)** —
   ~~`decisions/ADR-0001-consolidate-codebase.md` and
   `decisions/ADR-0001-consolidate-service-layer.md` share the number 0001.~~
   ✅ **Fixed** — service-layer renumbered to ADR-0002, all ADRs shifted +1, cross-references updated.
   Already listed as a backlog item in `migration/migration_summary.md` and
   `file_move_ledger.md` ("renumber one and update cross-references").
   Renumbering one ADR + updating cross-refs is docs-only and low-risk, but
   was deliberately deferred by prior audits; left for owner sign-off.
2. **`reference/RESUME_BULLETS.md` (Tier 2)** — personal-portfolio content
   ("Ready-to-use entries for your resume/LinkedIn") inside project docs.
   Factual (maps to verifiable deliverables) but not project documentation.
   Recommendation: keep (if the repo doubles as a portfolio artifact) or move
   to a personal location. Owner decision.
3. **No docs index (Tier 2 recommendation)** — optional `docs/README.md`.

## 15. "Does This Still Look AI-Scaffolded?" Score

**96 / 100** — 100 baseline; −3 for the ADR-0001 collision awaiting renumber,
−1 for the personal RESUME_BULLETS doc in project docs (owner decision).
Real ADRs with dates, real metrics, threat model, no contradictions.
