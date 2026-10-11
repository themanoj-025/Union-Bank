# DEAD-WEIGHT PURGE v2.0 AUDIT REPORT

**Repository**: `UNION-BANK-`  
**Mode**: `AUDIT_ONLY` (Zero repository modifications performed)  
**Baseline Commit SHA**: `385dc447da8708a2f145b740fb36e1cecf9e9ee8`  
**Audit Date**: 2026-10-11  
**Verdict**: **YELLOW** (Dead weight detected; review recommended)

---

## 1. Executive Summary

- **Tracked Files in Git**: 354
- **Untracked Local Files**: 1
- **Total LOC**: 60,079
- **Analyzed Size**: 12.27 MB
- **Total Dead-Weight Candidates Identified**: 183
  - **Tier 0 (Provable Junk/Empty)**: 95
  - **Tier 1 (High Confidence)**: 0
  - **Tier 2 (Medium / Needs Verification)**: 88
  - **Tier 3 (Protected / Hard Vetoed)**: 0

## 2. Findings by Category

| Category | Description | Count |
|---|---|---|
| **A** | Empty & Near-Empty Files | 10 |
| **C** | Junk / Caches / Build Artifacts | 85 |
| **D** | Potential Orphan Modules | 88 |
| **H** | Exact Hash Duplicates | 0 |

### Top Tier-0 Items (Provable Deletion Candidates if EXECUTE_SAFE were used):
- [`A`] `py.typed`: 0-byte file with no content
- [`A`] `src/__init__.py`: 0-byte file with no content
- [`A`] `src/logging_utils/__init__.py`: 0-byte file with no content
- [`A`] `src/py.typed`: 0-byte file with no content
- [`A`] `src/unionbank/__init__.py`: 0-byte file with no content
- [`A`] `src/unionbank/data/__init__.py`: 0-byte file with no content
- [`A`] `src/unionbank/entrypoints/__init__.py`: 0-byte file with no content
- [`A`] `src/unionbank/entrypoints/api/__init__.py`: 0-byte file with no content
- [`A`] `src/unionbank/entrypoints/cli/__init__.py`: 0-byte file with no content
- [`A`] `src/unionbank/utils/data/__init__.py`: 0-byte file with no content
- [`C`] `.cleanup-audit/`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.cleanup-audit/.claude/`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.coverage`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.env`: Untracked build/dependency/cache artifact directory in workspace
- [`C`] `.github/copilot-instructions.md`: Untracked build/dependency/cache artifact directory in workspace
_...and 80 more listed in `manifest.csv`._

## 3. Next Steps & Recommended Actions

1. Review `.purge-reports/manifest.csv` and `.purge-reports/FLAGGED.md`.
2. If safe cleanup is desired, configure `MODE: EXECUTE_SAFE` or generate an approval `PLAN.yaml`.
3. Verify that all untracked artifacts (`__pycache__`, `.venv`, `.pytest_cache`) are properly covered in `.gitignore`.
