# VS Queue Monitor - Shared Agent Instructions

This file is the shared instruction baseline for coding agents working in this repository.

## Source Of Truth

`docs/README.md` is the documentation map. `docs/DESIGN.md` is the source of truth for product intent, UX decisions, vocabulary, and interaction patterns.

- Consult `docs/README.md` first when deciding where documentation changes belong.
- Consult `docs/DESIGN.md` before changing user-visible behavior.
- If a requested change conflicts with the design contract, update the design doc first, then implement.
- If a change affects user-visible behavior, update:
  - `docs/DESIGN.md` when the UX contract or intent changes
  - `README.md` when setup, troubleshooting, behavior, or usage guidance changes

Prefer the established patterns in this repo: seamless flow, progressive disclosure, honest states, and consistent graph/history semantics.

## Shared Behavior Expectations

- Keep the happy path fast and low-friction.
- Show less by default, but do not hide important information.
- Put detail in Help, tooltips, settings, and tours instead of crowding the main UI.
- Keep error states actionable and recoverable.
- Do not fake certainty in ETA, rate, or queue-state messaging.

## Git And Verification

When you finish a coherent change set:

1. Bump the patch version in `monitor.py` unless the user explicitly says to skip it.
2. Update `README.md` when the change affects users.
3. Run `python -m py_compile` on changed Python files before committing.
4. Commit intentional changes with a clear message.
5. When a commit represents a release checkpoint, RC, stable milestone, or other user-designated snapshot, create an annotated git tag for it after the commit.
6. Do not run `git push` unless the user explicitly asks.

Do not commit generated junk, caches, secrets, or unrelated files.

### Browser Test Discipline

- Playwright and browser-smoke tests must never reuse or mutate the real user config under `%APPDATA%` / `XDG_CONFIG_HOME`.
- Keep browser-test config/state isolated in a test-specific sandbox path.
- For browser-visible bugs, do not declare success from code inspection alone when a real browser check is possible.
- Prefer this order for UI/browser bug verification:
  1. reproduce in Playwright or the real browser
  2. confirm the relevant API/state is correct
  3. confirm the rendered UI matches that state
  4. only then declare the fix complete
- When a bug is only reproduced against a real user log, verify against that real log path instead of relying only on synthetic fixtures.

## Project-Specific Product Rules

- Users often ship only `monitor.py`, so avoid adding hard runtime dependencies on neighboring files unless the behavior degrades gracefully.
- In PowerShell, use `;` rather than `&&`.
- Queue position `0` means past queue wait, not merely position `1`.
- Distinguish `At front` from `Completed`.
- `Waiting for log file` and `Warning: no queue detected` are different states and should stay distinct.
- Default warning thresholds are `10, 5, 1`.
- `show_every_change` defaults to `true`.
- When `Log every position change` is off, omit routine queue lines from History.
- While interrupted, freeze live rate displays rather than letting time-based calculations drift.

## Dependency Guidance

- Prefer the Python standard library first.
- Otherwise prefer mature, permissively licensed open-source dependencies.
- For non-trivial web UI libraries, vendor stable OSS bundles under `vs_queue_monitor/web/static/vendor/` and document them in `vendor/README.md`.
- Avoid proprietary SDKs or closed toolchains unless there is an explicit product decision.

## Desktop Web UI Guidance

The shipping UI is the local web client under `vs_queue_monitor/web/static/` backed by `vs_queue_monitor/engine.py`.

- Favor seamless, local-first flows.
- Keep layout scannable and calm.
- Use visual structure, spacing, and hierarchy to reduce copy.
- Back up compact UI choices with accessible names, hints, Help, and the guided tour.
- Do not rely on color alone to communicate status.
