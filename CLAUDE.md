# VS Queue Monitor — Claude guidance

## Shared baseline

Read `AGENTS.md` first, then `.agents/shared-instructions.md`.

- `AGENTS.md` is the root auto-load entry point.
- `.agents/shared-instructions.md` is the shared guidance source for all agents in this repo.

## Design doc is the contract

`docs/DESIGN.md` is the **source of truth** for product intent and UX decisions in this repo.

- **Consult `docs/DESIGN.md` first** and align changes to its intent, vocabulary, and interaction patterns.
- If a requested change conflicts with the design contract, **update the design doc first**, then implement.
- If a change affects **user-visible behavior** (labels, copy, flows, defaults, onboarding, alerts, graph behavior, settings affordances), update:
  - **`docs/DESIGN.md`** when the **intent / decision / UX contract** changes
  - **`README.md`** when the **how-to / troubleshooting / setup steps** change

Prefer established patterns: seamless flow, progressive disclosure, honest states, graph behavior semantics.

---

## Git: commit after changes

When you finish a coherent set of edits or complete a user-requested task:

1. **Bump the micro (patch) version** on every commit (unless the user says skip):
   - Increment the third semver number (`1.0.0` → `1.0.1`) in **`vs_queue_monitor/__init__.py`** — that is the single source of truth for the version.
   - `pyproject.toml` reads the version dynamically via `[tool.setuptools.dynamic] version = {attr = "vs_queue_monitor.VERSION"}` — no change needed there.
   - `monitor.py` no longer has its own `Version:` docstring line — do not add one back.

2. **Update `README.md` before commit** when the change affects user-visible behavior, CLI flags, configuration, saved settings/defaults, paths, requirements, or install/run steps. Skip only for purely internal refactors or comments-only edits.

3. **Check for errors before committing**:
   - Run `python -m py_compile` on every changed `.py` file. Fix failures before committing.
   - Use editor/linter diagnostics on edited files; fix new issues before committing.
   - Do not commit while compile or lint checks still fail, unless the user explicitly says to.

4. **Commit** — `git add` only intentional project files, then `git commit` with a message stating what changed and why.

5. **Do not run `git push`** unless the user explicitly asks.

6. Do not commit build artifacts, `__pycache__/`, editor junk, or secrets.

Do not end a coding task that modified tracked files without attempting a commit, unless the user asked not to.

---

## Monitor behavior

Apply when editing `monitor.py`, `README.md`, or related files.

### Single-file delivery and window icon

- **Primary artifact:** Users often ship **only** `monitor.py`. Do not add runtime dependencies on files next to the script unless the feature is optional and clearly degraded when missing.
- **Embedded icon:** Window icon is a GIF in `_APP_ICON_GIF_B64`, loaded with `tk.PhotoImage(data=...)`. Keep a strong reference on the app instance so Tcl does not GC the image. Catch `tk.TclError` if the display cannot use it.
- **Repo copy:** `assets/app_icon.gif` mirrors the embed. After replacing the icon, update `_APP_ICON_GIF_B64` in the same change set.

### Shell (Windows)

In PowerShell, chain commands with **`;`**, not `&&`.

### Queue position and "done" state

- **Position `0`** means past connect-queue wait (post-queue patterns after the last queue-position line). Map raw ≤1 + post-queue signal → `0` for KPI/graph.
- Completion sound/popup, Completed status, 100% progress, and celebration emoji align with past-queue detection / position `0`, not only hitting position `1`.
- `POST_QUEUE_PROGRESS_LINE_RES`: include connecting/loading lines, not only "fully connected." Only count matches **strictly after** the final queue line in the tail.

### Log resolution and paths

- `resolve_log_file`: Prefer strict client-log discovery — do not fall back to arbitrary `*.log` files.
- `expand_logs_folder_path`: Browse and Start require an existing directory; a client log file is optional at first. If none resolves, start in **Waiting for log file** and keep polling.

### Settings must match code

- **"Log every position change"**: When off, omit routine queue lines from History entirely. When on, log each transition.
- **Default `show_every_change`:** `true`.

### Interrupted mode

While Interrupted, **freeze** KPI Rate / Global Rate display. Recency-weighted speed uses wall time and would otherwise drift every tick.

### Status strings

- **Waiting for log file**: No resolved client log path yet (or unreadable).
- **Warning: no queue detected** (`danger=True`): Log file exists but tail has no connect-queue position line.
- Distinguish **At front** (still in queue at `1`) vs **Completed** (position `0` / past-queue).

### ETA

At position `1`, still show REMAINING using a one-step model (and fallback when speed unknown), not `—`.

### Defaults

Default warning thresholds: `15, 10, 5, 3, 2, 1` (`DEFAULT_ALERT_THRESHOLDS`).

---

## Dependencies: open source first

1. **Python:** Prefer the standard library when clear, tested, and maintainable.
2. **PyPI:** Choose mature, permissively licensed OSS; record in `requirements.txt` with sensible minimum versions.
3. **Document user-facing deps:** If a new dependency affects install size, platform support, or how users run the app, update `README.md` in the same change set.
4. **Web UI:** Static HTML/CSS/JS served by Starlette. Prefer mature MIT/BSD OSS for non-trivial behavior; add vendored minified bundles under `vs_queue_monitor/web/static/vendor/`, document in `vendor/README.md`, load from `index.html` before `app.js`.
5. **Avoid** proprietary SDKs, undocumented closed components, or large algorithm blocks from random sources when a maintained OSS library covers the same need.

---

## UX philosophy: seamless flow first

The shipping UI is the local web client (`vs_queue_monitor/web/static/`) with `vs_queue_monitor/engine.py`.

**Principles:**
- **Minimize steps**: fewer clicks, fewer context switches, fewer places to look.
- **Guide in-context**: show help or next action where the user already is (status line, inline hint, dialog).
- **Make actions actionable**: messages should point to a direct next step (browse folder, Start, Settings).
- **Keep the happy path fast**: no modal detours for normal usage.
- **Handle expected failures gracefully**: missing files, wrong paths, empty folders should be clear and recoverable.
- **Don't dead-end**: every error state should offer an obvious way forward.

**Guardrails:**
- No network backend for core monitoring: local log read and local config only.
- Don't fake certainty: ETAs and rates are estimates from logs; copy must stay honest.

---

## Visual language and simplicity

When designing or changing the web client (`vs_queue_monitor/web/static/`):

- **Show less, imply more**: Prefer scannable structure (alignment, grouping, emphasis) over explanatory sentences in the default view.
- **Do not hide accountability**: Anything removed from inline copy must still be reachable via tooltips, Help, or tour.

**Pair lean chrome with disclosure:**
1. `title` attributes and short hints on controls where icon/abbreviation is not self-explanatory.
2. `aria-label` / accessible names on icon-only controls (required for screen readers).
3. **Help** (`?`) for paths, shortcuts, and operational detail.
4. **Guided tour** for the first-run story.

**Guardrails:**
- **No information removal**: Simplify presentation, not availability. Critical constraints stay where policy requires them.
- **Not color-only**: Status and warnings need text, icon, or pattern — not hue alone.
- **Progressive disclosure**: Put depth in Help, settings, tooltips, and tour — not in permanent banner text.

---

## UI/UX expert analysis skill

When asked for a UX audit, UI/UX analysis, expert review, design critique, usability assessment, or screenshot-based visual review:

**Before analyzing:**
1. Read this file's UX sections (seamless flow + visual language) and align recommendations with them.
2. Skim `README.md` sections that describe dashboard behavior so analysis does not contradict documented intent.
3. Prefer evidence from implementation (markup, CSS, JS) over assumptions.

**Investigation order** (matches user scan order):
1. **Shell** — `index.html`: landmark order, modals/overlays, `aria-*` and labels on icon-only controls.
2. **Visual system** — `styles.css`: tokens (`:root`), spacing rhythm, breakpoints, overflow strategy.
3. **Interaction** — `app.js`: navigation, modals vs popovers, keyboard shortcuts, toasts/errors.
4. **Encoded intent** — `tests/test_ui_visual.py`: viewports, overflow checks, required visible regions.

**Optional screenshots:** Run `VS_QUEUE_MONITOR_PLAYWRIGHT_SCREENSHOTS=1` + `pytest tests/test_ui_visual.py::test_optional_full_page_screenshots`. Artifacts land in `test-results/ui-shots/`.

**Analysis dimensions:**

| Dimension | Questions |
|-----------|-----------|
| Information architecture | Hierarchy match task order? Primary action obvious? Scope clear? |
| Friction & flow | Extra steps? Context switches? Modal detours? Recovery from bad path? |
| Feedback | Loading, success, failure, live status — clear and adjacent to control? |
| Visual cohesion | Typography, spacing, button hierarchy, density vs clutter. |
| Visual language | Layout/color/iconography reduce needless words? Omitted copy available via tooltips, Help, tour? |
| Accessibility | Focus, keyboard, screen reader names, modal focus trap, native anti-patterns. |
| Responsive | Narrow/wide behavior, horizontal overflow, touch targets. |
| Trust & copy | Honest about uncertainty (ETAs, estimates)? |

**Output format:** Strengths → friction/risks → polish → accessibility → optional prioritized table. Be specific (name regions), actionable, and proportionate to scope.
