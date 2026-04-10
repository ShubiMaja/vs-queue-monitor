# VS Queue Monitor — UI/UX Parity Spec (GUI + TUI)

This is the **product-level UI/UX spec** for VS Queue Monitor. It defines what the user should see and how it should behave in:

- **GUI**: Tk desktop app
- **TUI**: Textual terminal app (SSH-safe)

For implementation-focused notes, see `docs/GUI-TUI-PARITY.md`. For unavoidable differences and constraints, see `docs/TUI-LIMITATIONS.md`.

## Goals

- **Same mental model** across GUI/TUI: same state names, same KPI meanings, same graph semantics, same alerts.
- **Parity of outcomes**: what the user can do and what they learn should match, even if the widgets differ.

## Shared concepts (definitions)

- **Logs folder**: directory containing client logs; engine resolves a specific log file within it.
- **Position**: connect queue position; `0` means “past queue wait” (post-queue detection).
- **Info pane**: details block (Last change, Last threshold alert, Resolved log path, Global rate).
- **History pane**: chronological log of events and (optionally) every position change.
- **Graph**: step chart over time of queue position; supports linear/log Y scale.

## Information architecture (same in both)

### Top bar

Contains the “session controls” and current source path.

- **Play/Stop** (start/stop monitoring)
- **Run indicator** (Idle vs Monitoring)
- **Logs folder** path field
- **Browse** (GUI folder picker; TUI focus/help)
- **Settings** (opens settings UI)

### Status + graph (single composite area)

- **Status indicators**: KPIs at the top (Position/Status/Rate/Warnings/Elapsed/Est remaining/Progress)
- **Divider line**
- **Queue graph**

### Collapsible panes below

- **Info** (collapsible)
- **History** (collapsible; default collapsed in TUI)

## Mockups (reference wireframes)

### GUI (high-level)

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ [Play/Stop]  Logs folder: [C:\...\Logs]                 [Browse...] [Settings] │
├───────────────────────────────────────────────────────────────────────────────┤
│ POSITION  STATUS  RATE(Rolling N)  WARNINGS     ELAPSED  EST.REMAINING  PROGR │
│  101      Monitoring  1.12 min/pos 15 10 7 6…   2:16     2:00:04        [=== ]│
├───────────────────────────────────────────────────────────────────────────────┤
│ Queue graph                                                     [Y → log]      │
│  min 101  max 103                                                            │
│  (step chart, axis ticks, grid lines, marker, hover cursor + tooltip)        │
├───────────────────────────────────────────────────────────────────────────────┤
│ ▼ Info                                                                       │
│   Last change: ...    Last threshold alert: ...                              │
│   Resolved log path: ...                                                     │
│   Global rate: ...                                                           │
├───────────────────────────────────────────────────────────────────────────────┤
│ ▼ History                                                                     │
│   [timestamp] message...                                                      │
│   ...                                                                         │
└───────────────────────────────────────────────────────────────────────────────┘
```

### TUI (target layout)

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ [Play]  ○ Idle  Logs folder: [..........................................] [Br] [Set] │
└───────────────────────────────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────────────────────────────┐
│ Status / graph                                                                │
│ POSITION  STATUS  RATE(Rolling N)                                             │
│ WARNINGS 15 · 10 · 7 · 6 · 5 · ...                                            │
│ ELAPSED  0:12:34   EST. REMAINING 1:23:45   PROGRESS 42%                      │
│ ───────────────────────────────────────────────────────────────────────────── │
│ (braille step chart; GUI-aligned ticks/grid; cursor line if active)           │
└───────────────────────────────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────────────────────────────┐
│ ▼ Info  (i)                                                                   │
│ Last change: ...                                                              │
│ Last threshold alert: ...                                                     │
│ Resolved log path: ...                                                        │
│ Global rate: ...                                                              │
└───────────────────────────────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────────────────────────────┐
│ ▶ History (h/l)                                                               │
│ (when expanded: RichLog lines)                                                │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Interaction spec

### Monitoring (Play/Stop)

- **GUI**
  - Clicking Play starts monitoring; Stop stops.
  - Indicator/state updates immediately.
- **TUI**
  - Topbar “Play/Stop chip” toggles monitoring.
  - `Space` toggles monitoring.
  - Run indicator shows “○ Idle” or “● Monitoring”.

### Logs folder

- **GUI**
  - Browse opens a folder picker; choosing a folder updates config and (optionally) restarts monitoring.
- **TUI**
  - Path field accepts text; pressing Enter applies and persists.
  - Browse focuses the path field and prints guidance (no native picker over SSH).

### Settings

- **GUI**
  - Full settings window with sections and reset defaults.
- **TUI**
  - Settings modal with editable fields that persist to `config.json`.

### Collapsible panes

- **GUI**
  - “Info” and “History” chevrons toggle visibility.
  - Paned sashes allow resize.
- **TUI**
  - `i` toggles Info; `h/l` toggles History.
  - Headers remain visible when collapsed.

### Graph (semantics)

- **Both**
  - Step chart by time.
  - Log/linear Y scale mapping matches (`GRAPH_LOG_GAMMA`).
  - Grid/ticks follow GUI behavior (including interior-only horizontal grid).

### Graph cursor / hover

- **GUI**
  - Mouse hover shows a vertical cursor and tooltip with timestamp + position.
- **TUI**
  - When focused on Status/graph area, Left/Right arrow keys step through points.
  - Cursor draws a bright vertical line and shows `Cursor: HH:MM:SS pos N` in the status block.

## Copy / wording (must match)

- **Pane title**: “Info” and “History”
- **Graph title**: “Queue graph”
- **Completion state**: “Past queue wait” semantics (position `0` aligns with post-queue detection)

## Acceptance checklist

- Top bar contains Play/Stop, indicator, path, Browse, Settings in both UIs.
- Status + graph are combined, separated by a divider line.
- Info/History are collapsible in both, with the same labels.
- Graph semantics and alerts match engine behavior; completion uses position `0` / post-queue detection.

