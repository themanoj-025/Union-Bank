# UNION-BANK- — Documentation Index

Single home for all UNION-BANK- documentation. UNION-BANK- is a
concurrent-safe banking API & management system: atomic transfers, TOTP 2FA,
async PostgreSQL, layered architecture, and full observability.

**Start here:** [architecture.md](architecture.md) (system map) →
[folder_structure.md](folder_structure.md) (repo tree) →
[technical/TechSpec.md](technical/TechSpec.md) (build details).

## Structure

```
docs/
├── README.md                      ← this index
├── architecture.md                system architecture
├── folder_structure.md            repository + docs tree
├── module_dependency.md           dependency graph
├── package_overview.md            module inventory
├── startup_flow.md                boot + runtime flows
├── community/
│   ├── CHANGELOG.md               changelog
│   ├── CODE_OF_CONDUCT.md         code of conduct
│   ├── CONTRIBUTING.md            contribution guide
│   ├── SECURITY.md                security policy
│   └── SUPPORT.md                 support channels
├── decisions/
│   ├── ADR-0001-consolidate-codebase.md    ADR: single canonical tree
│   ├── ADR-0002-consolidate-service-layer.md  ADR: single service layer
│   ├── ADR-0003-security-hardening.md
│   ├── ADR-0004-totp-2fa.md
│   ├── ADR-0005-data-retention.md
│   ├── ADR-0006-database-migration.md
│   └── ADR-0007-git-strategy.md
├── design/
│   ├── AppFlow.md                 app screens / states / flows
│   └── Design.md                  design decisions
├── product/
│   └── PRD.md                     product requirements
├── project/
│   ├── analysis_report.md         repo inventory & classification
│   ├── ImplementationPlan.md      implementation plan
│   ├── RiskRegister.md            risks & mitigations
│   ├── Rules.md                   engineering rules
│   └── Tracker.md                 status tracker
├── reference/
│   ├── BASELINE_METRICS.md        baseline performance metrics
│   ├── BASELINE_VERSIONS.md       baseline version inventory
│   ├── CASE_STUDY.md              case study
│   ├── CURRENT_STATE.md           current-state summary
│   ├── E2E_TEST_STRATEGY.md       end-to-end test strategy
│   ├── Glossary.md                terminology
│   ├── INVENTORY.md               forensic inventory
│   ├── openapi.json               auto-generated OpenAPI spec
│   ├── RESUME_BULLETS.md          portfolio resume bullets
│   ├── RUNBOOK.md                 ops runbook
│   ├── SELF_AUDIT.md              self-audit findings
│   ├── THREAT_MODEL.md            threat model
│   └── TS_MIGRATION.md            TypeScript migration notes
├── technical/
│   ├── API.md                     endpoint reference
│   ├── Deployment.md              deployment guide
│   ├── Schema.md                  data model
│   ├── SecurityAndCompliance.md   security baseline
│   ├── TechSpec.md                technical spec
│   └── Testing.md                 test strategy
├── migration/
│   ├── migration_summary.md       modernization record
│   ├── old_tree_to_new_tree.md    restructure before/after
│   └── file_move_ledger.md        file-move ledger
└── audit/
    ├── cleanup-audit-2026-08-13.md  previous cleanup audit
    └── cleanup-audit-2026-08-15.md  docs de-LLM-ification audit
```

## Guidance

| You want... | Read |
|---|---|
| How the system works end-to-end | [architecture.md](architecture.md) |
| Architecture decisions | [decisions/ADR-0004-totp-2fa.md](decisions/ADR-0004-totp-2fa.md) |
| Threat model | [reference/THREAT_MODEL.md](reference/THREAT_MODEL.md) |
| Ops runbook | [reference/RUNBOOK.md](reference/RUNBOOK.md) |
| Baseline metrics | [reference/BASELINE_METRICS.md](reference/BASELINE_METRICS.md) |
| API surface | [technical/API.md](technical/API.md) |
| Deployment | [technical/Deployment.md](technical/Deployment.md) |
| What's shipped / next | [project/Tracker.md](project/Tracker.md) |
| Risks & follow-ups | [project/RiskRegister.md](project/RiskRegister.md) |
