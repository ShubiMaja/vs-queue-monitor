# VS Queue Monitor — TUI limitations / forced differences

This document lists **intentional** and/or **unavoidable** differences between the GUI and TUI due to terminal constraints, SSH constraints, and Textual behavior. The goal is not to justify gaps, but to make sure users and contributors understand what is **different by necessity** vs what is just **unfinished**.

For the target UX parity spec, see `docs/UI-UX-PARITY.md`.

## 1) Folder picker (“Browse…”)

- **GUI**: native folder picker dialog.
- **TUI**: no reliable, cross-platform native folder picker in SSH/headless mode.
  - **TUI behavior**: “Browse” focuses the path input and prints instructions to paste a folder path and press Enter.

## 2) Mouse hover tooltips

- **GUI**: true mouse hover over a canvas; shows a tooltip and a vertical cursor line.
- **TUI**: terminals do not reliably support rich mouse hover + arbitrary tooltips.
  - **TUI behavior**: keyboard cursor mode (Left/Right) shows a vertical cursor line and prints cursor info in the status area.

## 3) Pixel-precision layout

- **GUI**: pixel-based canvas; can deduplicate tick labels by pixel spacing.
- **TUI**: character-cell layout; braille plotting is higher resolution than ASCII but still constrained by terminal width/height.
  - **TUI behavior**: “approximate” label spacing/dedup in character columns.

## 4) Sound and notifications

- **GUI**: can play sounds and show `Toplevel` popups consistently.
- **TUI**:
  - Sound may not work in all SSH environments (no audio device).
  - “Popups” are implemented as toasts (`notify()`) rather than windows.

## 5) Pane resizing via drag

- **GUI**: draggable sashes and auto-collapse thresholds.
- **TUI**: no direct equivalent to drag-resizing panes (depends on terminal size).
  - **TUI behavior**: panel toggles (keys) + terminal resize.

## 6) Button look-and-feel

- **GUI**: real buttons and themed widgets.
- **TUI**: Textual `Button` widgets can be visually tall and may wrap; terminals vary widely.
  - **TUI behavior**: “compact chips” (clickable `Static`) used for topbar controls to avoid wrapping/hiding controls.

## 7) Input focus vs global keybinds

- **GUI**: key events can be bound globally or per-widget.
- **TUI**: focused inputs tend to capture keys.
  - **TUI behavior**: app bindings are `priority=True` and focus is cleared on mount so global keys work by default.

## 8) “Exact visual match” is not required

The TUI must match **meaning** and **outcomes** (what users can do and learn), not pixels:

- Graph must convey step shape, progress, and key points.
- Alerts must be obvious and logged.
- Settings must persist and map to the same engine config.

