# VS Queue Monitor — web UI parity

The **only** user-facing surface is the **local web client** (`vs_queue_monitor/web/static/`) backed by **Starlette** + **`QueueMonitorEngine`**. Legacy Tk and Textual front ends were removed; behavior lives in the shared engine and these integration points:

| Concern | Where |
|--------|--------|
| REST + WebSocket state | `vs_queue_monitor/web/server.py` |
| Engine hooks (timers, history, alerts) | `vs_queue_monitor/web/hooks_web.py` |
| Graph (Tk `redraw_graph` parity: step series, ticks, interior-only grids, minor X ticks, hover) | `web/static/graph_canvas.js` + `GET /api/meta` → `graph_theme` (`vs_queue_monitor.core`) |
| Dashboard chrome (CSS variables) | `GET /api/meta` → `chrome_theme` (`theme.py`) |
| Threshold / completion toasts + optional **Notification** API | `app.js` (`applyState`) |
| New queue run while **Interrupted** | Modal + `POST /api/new_queue` |
| Settings persisted | `POST /api/config` (same keys as `config.json` elsewhere) |
| Keyboard (when focus is not in a text field) | **Space** start/stop · **F1** help · **o** settings · **c** copy graph TSV · **v** copy session history |

Sounds and system fallbacks still run **in the Python process** (`engine.py`), not in the browser. The graph uses **Canvas 2D** with logic aligned to the former Tk implementation; constants come from Python so they stay in sync with `core.py`.

For product-level UX intent, see [`DESIGN.md`](DESIGN.md) and [`UI-UX-PARITY.md`](UI-UX-PARITY.md).
