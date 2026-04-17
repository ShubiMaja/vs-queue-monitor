# VS Queue Monitor — regressions & lessons learned

This document is intentionally **operational**: it captures regressions, root causes, fixes, and quick verification recipes.

Keep **`docs/DESIGN.md`** focused on product/UX design intent. Put postmortems and debugging notes here.

---

## Entry template (copy/paste)

- **Title**: <short name>
- **Symptom**: <what the user sees>
- **Trigger**: <when it happens / conditions>
- **Root cause**: <the actual bug>
- **Fix**: <what changed and why>
- **Verify**:
  - **Steps**: <repro steps>
  - **Expected**: <correct outcome>
- **Notes**: <gotchas, follow-ups, links to commits/PRs>

---

## What to prioritize logging

- **Startup failures / dead UI** (one exception prevents event listeners from wiring)
- **Session boundaries** (graph spans multiple sessions, “new run” not detected, stale values after reconnect)
- **Seeding/replay** (initial load shows wrong start/current, missing timestamps causing insane rates, duplicate points)
- **Live view / time axis** (empty runaway, frozen axis, jumpy scaling)
- **Interrupted/stale detection** (false interruptions, stuck status, recovery behavior)
- **History verbosity/perf** (too many points/lines, UI stalls, `logEveryChange` behavior)

