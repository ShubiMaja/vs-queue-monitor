# VS Queue Monitor — web UI parity

The **only** user-facing surface is the **local web client** (`vs_queue_monitor/web/static/`) backed by **Starlette** + **`QueueMonitorEngine`**. There is no separate Tk or Textual app; behavior lives in the engine and these integration points:

| Concern | Where |
|--------|--------|
| REST + WebSocket state | `vs_queue_monitor/web/server.py` |
| Engine hooks (timers, history, alerts) | `vs_queue_monitor/web/hooks_web.py` |
| Graph (Tk `redraw_graph` parity: step series, ticks, interior-only grids, minor X ticks, hover) | `web/static/graph_canvas.js` + `GET /api/meta` → `graph_theme` (`vs_queue_monitor.core`) |
| Queue session graph scope (dropdown; KPIs stay live) | Snapshot `queue_sessions` + `core.queue_sessions_for_log_tail` · `app.js` `buildDisplayState` |
| Native **folder** / **log file** icons (header) | `POST /api/pick_path` · Tk dialog on the Python host (not in remote browsers) |
| **Stats** (Start/End Pos, Pos Delta, Duration, Avg Rate) + **Copy stats** | Same graph scope as Session / TSV · `computeGraphSessionStats` in `app.js` (parity with `feature/change-to-web-ui`) |
| **Copy history** button | Same text as history panel · keyboard **v** unchanged |
| Threshold ranges (`3-1`, …) | `parse_alert_thresholds` in `core.py` |
| Version / build fingerprint | Snapshot + `GET /api/meta` · env `VS_QUEUE_MONITOR_BUILD_FINGERPRINT` optional (legacy: `VSQM_BUILD_FINGERPRINT`) |
| Dashboard chrome (CSS variables) | `GET /api/meta` → `chrome_theme` (`theme.py`) |
| Threshold / completion toasts + optional **Notification** API | `app.js` (`applyState`) |
| New queue run while **Interrupted** | Modal + `POST /api/new_queue` |
| Settings persisted | `POST /api/config` (same keys as `config.json` elsewhere) |
| Keyboard (when focus is not in a text field) | **Space** start/stop · **F1** help · **o** settings · **c** copy graph TSV · **v** copy session history (buttons for stats/history too) |

Sounds and system fallbacks still run **in the Python process** (`engine.py`), not in the browser. The graph uses **Canvas 2D** with logic aligned to the former Tk implementation; constants come from Python so they stay in sync with `core.py`.

For product-level UX intent, see [`DESIGN.md`](DESIGN.md) and [`UI-UX-PARITY.md`](UI-UX-PARITY.md).
