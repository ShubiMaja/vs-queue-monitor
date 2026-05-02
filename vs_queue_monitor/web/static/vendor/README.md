# Vendored web dependencies (open source)

Files in this directory are **minified third-party bundles** shipped with the local web UI (no npm install required at runtime). Pin updates here when replacing a file.

| File | Package | Version | License | Source |
|------|---------|---------|---------|--------|
| `dayjs.min.js` | [dayjs](https://github.com/iamkun/dayjs) | 1.11.13 | MIT | [jsDelivr](https://cdn.jsdelivr.net/npm/dayjs@1.11.13/dayjs.min.js) | SHA-256: `9cfdb93f38afcf2d076abecd66d32bfd3383cdf1967654ebc26a26605daf4173` |

Used for consistent date/time formatting in `app.js` (session labels) and `graph_canvas.js` (graph hover tooltip), with a small inline fallback if the script fails to load.
