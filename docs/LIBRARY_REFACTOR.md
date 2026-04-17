# Library refactor recommendations (MIT-friendly)

This project is intentionally **vanilla HTML/CSS/JS** with a simple build that copies files into `dist/`.
We can keep that model while offloading “UI infrastructure” work (tour, popover positioning, toasts) to small, well-maintained, **free** libraries with permissive licenses.

## Goals

- Reduce custom UI logic (less code to maintain, fewer edge-case bugs).
- Keep UX consistent (positioning, focus management, layering).
- Avoid license traps (prefer **MIT**).
- Avoid over-complicating the build (CDN or small npm deps are both acceptable).

## Recommended libraries

### 1) Guided tour / onboarding: **Driver.js** (MIT)

- **Use for**: anchored steps, next/prev navigation, highlighting target elements, scrolling into view, keyboard escape.
- **Why**:
  - MIT licensed (safe for personal + commercial).
  - Purpose-built for tours; fewer “DIY overlay conflicts”.
  - Good defaults; minimal API surface.
- **Link**: `https://driverjs.com/`

**Notes**
- Avoid Shepherd.js unless the project is AGPL-compatible or you buy a commercial license. Shepherd is **AGPL/commercial dual-licensed**, not MIT.

### 2) Popover/tooltip positioning engine: **Floating UI** (MIT)

- **Use for**: any “anchor this bubble to that element” UI (tour bubbles, popovers, tooltips, contextual menus).
- **Why**:
  - Best-in-class collision/flip/shift logic.
  - Framework-agnostic (works with vanilla DOM).
  - MIT licensed.
- **Link**: `https://floating-ui.com/`

### 3) Toasts: **Notyf** (MIT) or **ToastifyJS** (MIT)

Both are small and easy. Pick one:

- **Notyf**:
  - Minimalist API and styling.
  - Link: `https://github.com/caroso1222/notyf`
- **ToastifyJS**:
  - Extremely lightweight; lots of small options.
  - Link: `https://apvarun.github.io/toastify-js/`

## Suggested refactor plan (incremental, low-risk)

### Phase A: introduce a library “adapter layer”

Create thin wrappers so the rest of the app doesn’t depend on a specific library API.

- **`ui/toast.ts|js` adapter**
  - `toast.info(title, msg)`
  - `toast.warn(title, msg)`
  - `toast.error(title, msg)`
  - `toast.success(title, msg)`

- **`ui/tour.ts|js` adapter**
  - `tour.start()`
  - `tour.stop()`
  - `tour.isActive()`
  - `tour.setSteps(steps)`

This lets us swap implementations without a repo-wide rewrite.

### Phase B: replace tour first (highest complexity / most edge cases)

Current pain points addressed:
- Dimming overlay makes instructions harder to follow.
- Bubble overlay stacking with Settings/Help makes UI unusable.
- Maintaining accurate anchoring/scrolling/highlighting is tricky in custom code.

Driver.js solves these directly:
- It handles highlight/overlay, scrolling, and step navigation.
- It already has patterns for “don’t break clicks” and avoids hand-rolled `z-index` wars.

Migration strategy:
- Keep the existing `TOUR_STEPS` list shape, but map to Driver.js steps.
- On `tour.start()`, close Settings/Help and pause monitoring (we already do the pause).
- Remove custom `.tourOverlay`/`.tourBubble` HTML once the Driver.js tour is in place.

### Phase C: unify popover positioning with Floating UI

Targets:
- Status refresh popover
- Rate window popover
- Warnings thresholds popover

Benefits:
- One positioning algorithm everywhere (consistent).
- Better viewport handling (flip/shift) than our manual `getBoundingClientRect` math.

### Phase D: optionally swap our custom toasts

We currently have working toasts (with close button). This is optional.

Reasons to adopt a library anyway:
- Consistent stacking + animations with minimal code.
- Less DOM/state management code in `app.js`.

## Integration approach (keep build simple)

Two supported approaches:

### Option 1: npm dependency + copy into `dist/`

- Add deps to `package.json`.
- Update `scripts/build-dist.mjs` to copy the needed JS/CSS from `node_modules/…` into `dist/vendor/…`.
- Reference `./vendor/...` from `index.html`.

Pros: deterministic, offline-friendly.
Cons: slightly more build logic.

### Option 2: CDN (no build changes)

- Add `<script src="…">` and/or `<link rel="stylesheet" href="…">`.

Pros: simplest.
Cons: external network dependency; version pinning required.

## Decision summary

- **Tour**: Driver.js (MIT) is the best fit and directly addresses current tour issues.
- **Positioning**: Floating UI (MIT) gives “battle-tested” anchoring for all popovers.
- **Toasts**: keep current implementation or switch to Notyf/ToastifyJS (both MIT) if we want less custom UI code.

