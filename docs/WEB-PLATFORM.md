# Web platform — engineering & release reference

The repository ships a **browser-hosted** queue monitor (static build) alongside the Python desktop and TUI apps. This note is for **release**, **engineering**, and **product** readers who need hosting facts, repo policy, and behavioral context without spelunking chat logs.

---

## Release engineering — hosting & deployment

### Canonical site URL

GitHub Pages URLs follow the **account or organization** that owns the repository, not an individual contributor’s username.

| Item | Value |
|------|--------|
| Example remote | `git@github.com:ShubiMaja/vs-queue-monitor.git` |
| **Project Pages URL** | `https://shubimaja.github.io/vs-queue-monitor/` |

A URL that uses the wrong owner (e.g. `https://yosefrow.github.io/vs-queue-monitor/`) returns **404** if that user/org does not host the project.

### When the site returns 404

1. **Wrong owner** in the URL — match the GitHub owner of the repo.
2. **Pages not enabled** — Repository **Settings → Pages → Build and deployment**: set **Source** to **GitHub Actions** when using the Actions-based deploy workflow (`actions/deploy-pages`).
3. **No successful deploy** — A workflow run must complete after Pages is enabled.
4. **Branch filters** — Deploy workflows typically run only on pushes to branches listed under `on.push.branches` in the workflow file (e.g. `main` / `master`). Manual runs may still be available via **`workflow_dispatch`**.

### Pipeline behavior (intended)

Configuration lives under **`.github/workflows/`** (e.g. a Pages workflow YAML). The job should:

- Install Node dependencies and run the production build (`npm install` / `npm ci` + `npm run build`).
- Publish the **`dist/`** artifact, including **`dist/.nojekyll`** so Jekyll does not drop required assets.
- Deploy with **`actions/deploy-pages@v4`** (or current supported major).

To add deploys from an additional branch (e.g. a long-lived feature branch), add that branch name under `on.push.branches` in the workflow file.

### Release checklist (maintainers)

1. Merge or push the branch that contains the workflow to the configured default branch so triggers apply.
2. **Settings → Pages:** GitHub **Actions** as source (if using that workflow).
3. **Actions:** confirm the Pages deploy workflow completes successfully.
4. Open the canonical Project Pages URL (or the URL shown on the successful run / environment).

---

## Software engineering — build & repository policy

### Source layout

| Path | Role |
|------|------|
| `app.js`, `index.html`, `styles.css` | Web UI sources |
| `dist/` | Production bundle (e.g. `dist/index.html` after `npm run build`) |

### Local build

```bash
npm install
npm run build
```

### Git policy

| Path / topic | Policy |
|--------------|--------|
| `node_modules/` | **Ignored** — do not commit. After clone, run `npm install`. Verify ignore: `git check-ignore -v node_modules`. |
| `dist/` | **Ignored** — CI builds for Pages; avoid committing unless there is an explicit reason. To record a build in git, use `git add -f …` only deliberately. |

### Desktop app version (Python entrypoint)

Release discipline for the **Python** app: bump the patch version in **`monitor.py`** — both the `VERSION` constant and the `Version:` line in the module docstring — when making commits that change tracked product files, unless maintainers agree to skip for a trivial-only change.

---

## Product & UX — web client (reference)

These items describe **current or recent** web surface behavior for triage and parity discussions; they are not an end-user manual.

- **Queue sessions:** Session selection (dropdown), graph boundary markers, and KPIs/stats scoped to the selected session; History/logging aligned with session apply.
- **Updates:** `BUILD_FINGERPRINT` (and related logic) reduces spurious “interrupted” / false update noise when reloading.
- **Settings:** Settings modal vs inline controls were deduplicated where redundant; guided tour work was deprioritized in favor of other UX.
- **Alerts & copy:** Alert threshold parsing (including range-style inputs where applicable), stats presentation, and footer/notification copy were iterated for clarity.

**Useful code entry points for search:** `applySessionSelectionToGraph`, `BUILD_FINGERPRINT`, and symbols tied to “session” in the web sources.
