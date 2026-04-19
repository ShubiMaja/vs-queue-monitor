# Web platform — local server + static client

The shipping app is **`python monitor.py`** → **Starlette** on **`127.0.0.1`** + the static UI under **`vs_queue_monitor/web/static/`**. The **`feature/change-to-web-ui`** branch in git history is a **standalone static** prototype (browser-only log parsing); capabilities that made sense for the Python-backed product are **ported here** (session dropdown, threshold ranges, build fingerprint, footer version).

## Parity points integrated from `feature/change-to-web-ui`

| Area | Implementation |
|------|----------------|
| Queue **session** graph scope | `queue_sessions` in WebSocket/API snapshot (`core.queue_sessions_for_log_tail`), session `<select>` + `buildDisplayState` in `app.js` |
| **Stats** + **Copy stats** / **Copy history** | Per-session graph summary + clipboard (ported from static branch) |
| Warning **threshold ranges** (`3-1`, `8-10`) | `parse_alert_thresholds` in `core.py` + `mergeAlertThresholdsString` in `app.js` |
| **Build fingerprint** / version line | `build_fingerprint` in snapshot + `GET /api/meta`; git short SHA via `git rev-parse`, or env `VSQM_BUILD_FINGERPRINT` |
| Dashboard **theme** from Python | `GET /api/meta` → `graph_theme`, `chrome_theme` (`vs_queue_monitor/web/theme.py`) |

## Not ported (different architecture)

- **GitHub Pages** / `npm run build` / **service worker** PWA — optional follow-up; the default product is the local Python server.
- **In-browser** file parsing (no Python) — replaced by server-side tailing. **Native** folder/file pick is available via **`POST /api/pick_path`** (Tk on the host running `monitor.py`), not `input type=file` in the page.

## Release fingerprint

Set **`VSQM_BUILD_FINGERPRINT`** in CI or the environment when git metadata is unavailable.
