---
name: ui-ux-expert-analysis
description: >-
  Performs structured UI/UX expert reviews of local web clients and similar
  frontends: information architecture, friction, accessibility, visual cohesion,
  and actionable recommendations. Optionally uses Playwright screenshot artifacts
  for layout and responsive review. Use when the user asks for a UX audit, UI/UX
  analysis, expert review, design critique, usability assessment, or
  screenshot-based visual review of the app UI or static client in this repository.
---

# UI/UX expert analysis

## When to read this skill

Apply when analyzing **user-facing UI** (this repo: `vs_queue_monitor/web/static/`, tests under `tests/` that assert layout/IA). Do **not** substitute for product requirements—ground claims in **code and behavior**.

## Before analyzing

1. If present, read **`.cursor/rules/ux-seamless-flow.mdc`** and align recommendations with seamless-flow principles (minimize steps, in-context help, recoverable errors, no dead ends).
2. Skim **`README.md`** sections that describe **dashboard behavior** so analysis does not contradict documented intent.
3. Prefer **evidence from implementation** over assumptions: markup structure, CSS layout/tokens, JS event flows, Playwright/visual tests.

## Investigation order

Work top-down so the review matches user scan order:

1. **Shell** — `index.html` (or equivalent): landmark order (header → main regions → footer), modals/overlays, `aria-*` and labels on icon-only controls.
2. **Visual system** — `styles.css` (or theme): tokens (`:root`), spacing rhythm, breakpoints, overflow strategy.
3. **Interaction** — `app.js`: navigation between states, modals vs popovers, keyboard shortcuts, toasts/errors, `prompt`/`alert` vs custom UI.
4. **Encoded intent** — `tests/test_ui_visual.py` (or similar): viewports, overflow checks, required visible regions.

### Optional: screenshot evidence (this repo)

Use when a **visual or responsive** pass should complement code review (e.g. after CSS/layout changes, or to compare breakpoints).

- **Run:** `VS_QUEUE_MONITOR_PLAYWRIGHT_SCREENSHOTS=1` and execute  
  `pytest tests/test_ui_visual.py::test_optional_full_page_screenshots`  
  (requires Playwright; see `README.md` / test module docstring.)
- **Artifacts:** PNGs under `test-results/ui-shots/` (full dashboard plus cropped top bar, KPI, graph per viewport). Usually **gitignored**—treat as local review output unless the project tracks baselines on purpose.
- **Use for UX analysis:** spacing, alignment, density, empty states, breakpoint behavior—not a substitute for **structure** in HTML/CSS/JS; pair screenshots with the investigation steps above.

## Analysis dimensions

Cover each area briefly; skip if not applicable. Tie observations to **files or patterns**.

| Dimension | Questions |
|-----------|-----------|
| **Information architecture** | Does hierarchy match task order? Is primary action obvious? Scope (e.g. live vs historical) clear? |
| **Friction & flow** | Extra steps? Context switches? Modal detours on the happy path? Recovery from bad path / empty data? |
| **Feedback** | Loading, success, failure, live status—clear and adjacent to the control? |
| **Visual cohesion** | Typography, spacing, button hierarchy, density vs clutter. |
| **Accessibility** | Focus, keyboard, screen reader names, modal focus trap, native anti-patterns (`prompt`, etc.). |
| **Responsive** | Narrow/wide behavior; horizontal overflow; touch targets. |
| **Trust & copy** | Honest about uncertainty (ETAs, estimates)—especially for monitoring tools. |

## Output format

Use clear headings and **complete sentences**. Prefer **strengths → risks → medium polish → accessibility** → optional **prioritized table** of next steps.

### Template

```markdown
### What works well
- [Concrete pattern + why it helps users]

### Friction and risks (highest impact first)
- [Issue + where it shows up in UI/code]

### Visual / interaction polish (medium)
- ...

### Accessibility
- ...

### Suggested direction (optional table)
| Area | Direction |
|------|------------|
| ... | ... |
```

## Quality bar for the review

- **Specific**: Name regions (e.g. top bar, KPI strip, graph toolbar), not only “the UI”.
- **Actionable**: Recommendations should be implementable (e.g. “Escape closes modals” not “improve UX”).
- **Proportionate**: Match depth to scope—small change gets a short review.
- **No filler**: Avoid generic praise (“modern”, “clean”) without a tied observation.

## Optional: follow-up

If the user wants implementation, **narrow** to one or two items and change only what the task requires; match existing patterns in `styles.css` / `app.js`.
