# UNION-BANK- Modernization State

pre_task_head: 3fb4bc37ee0c659216a744b818fba1da5fdcd5dd
backup_ref: backup/pre-audit-20261009154952 (existing)
work_branch: chore/repo-cleanup-audit-20261009
ref_snapshot: baseline/for-each-ref.txt (captured 2026-10-10)

parameters:
  mode: execute-staged
  autonomy: 1
  rest: as per ULTRA MASTER REPOSITORY MODERNIZATION PROMPT v7.0

phase_progress:
  0: done (baseline captured)
  1: done (analysis + classification recorded)
  2: done (file classification + movability map)
  3: partial (deletions applied; dedup held pending review)
  4: done (path-coupling catalog captured; G10 = none)
  5: done (target architecture decided; move batches planned)
  GateA: NOT requested (mode=execute-staged auto-applies low-risk deletions)
  6: in-progress
  7: pending
  8: pending

decisions:
  D-001  Delete orphaned tracked MODERNIZATION_AUDIT.md
         Reason: zero references (git grep -nF -> 0), duplicates docs/audit/cleanup-audit-*.md
  D-002  Remove untracked runtime data/union_bank.db[.db-wal|.db-shm]
         Reason: documented untracked runtime artifacts (prior audit); gitignored by data/*.db*
  D-003  .bak snapshots NOT deleted
         Reason: intentional runtime self-backup feature (file_io.py + SECURITY.md); git grep shows 0 references but deleting would remove documented behavior artifacts
  D-004  Duplicate requirements manifests CONSOLIDATION HELD
         Reason: DUPLICATE LOGIC equivalence proof (protocol 8.5) required before merge;
         manifest pinning may differ by release cadence -> report & request sign-off

batch_list:
  B1-low  [applied]  delete orphaned audit md + runtime db artifacts  risk=low

open_questions:
  Q1  Consolidate root requirements.txt vs requirements.lock? recommend: keep both canonical,
      one authoritative (requirements.txt) + lockfile; NOT auto-resolved (release-cadence intent unknown)
