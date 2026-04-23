# Documentation Map

This folder is the documentation hub for the repository.

Use these files by role:

- [DESIGN.md](DESIGN.md)
  - Product and UX source of truth
  - Vocabulary, behavior contracts, release gate, browser verification discipline
- [WEB_UI_REGRESSIONS.md](WEB_UI_REGRESSIONS.md)
  - Web-specific guardrails and regression notes
  - UI startup, notifications, graph/UI pitfalls, manual web checklist
- [TODO.md](TODO.md)
  - Active bug list, deferred items, and fixed-item history with commentary

## Rules

- Put product intent and user-visible behavior contracts in `DESIGN.md`.
- Put web-client regression guardrails in `WEB_UI_REGRESSIONS.md`.
- Put bug tracking and fix history in `TODO.md`.
- Avoid copying the same guidance across multiple files. Prefer linking back here and to the source file.

## Practical workflow

When behavior changes:

1. Update `DESIGN.md` if the product/UX contract changed.
2. Update `README.md` if users need new setup, usage, or troubleshooting guidance.
3. Update `WEB_UI_REGRESSIONS.md` if the change closes or introduces a web-specific regression pattern.
4. Update `TODO.md` to record the bug/tweak history when relevant.
