import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const ROOT = path.resolve(process.cwd());
const SRC_HTML = path.join(ROOT, "index.html");
const SRC_CSS = path.join(ROOT, "styles.css");
const SRC_JS = path.join(ROOT, "app.js");
const OUT_DIR = path.join(ROOT, "dist");
const OUT_HTML = path.join(OUT_DIR, "index.html");

function fail(msg) {
  console.error(`[build-dist] ${msg}`);
  process.exit(1);
}

function replaceOnce(haystack, needle, replacement, label) {
  const idx = haystack.indexOf(needle);
  if (idx < 0) fail(`Could not find ${label} marker: ${needle}`);
  if (haystack.indexOf(needle, idx + needle.length) >= 0) fail(`Found ${label} marker more than once.`);
  return haystack.slice(0, idx) + replacement + haystack.slice(idx + needle.length);
}

function normalizeNewlines(s) {
  return s.replaceAll("\r\n", "\n");
}

async function main() {
  const [htmlRaw, cssRaw, jsRaw] = await Promise.all([
    readFile(SRC_HTML, "utf8"),
    readFile(SRC_CSS, "utf8"),
    readFile(SRC_JS, "utf8"),
  ]);

  const html = normalizeNewlines(htmlRaw);
  const css = normalizeNewlines(cssRaw);
  const js = normalizeNewlines(jsRaw);

  let out = html;

  out = replaceOnce(
    out,
    '<link rel="stylesheet" href="./styles.css" />',
    `<style>\n${css}\n</style>`,
    "CSS link tag",
  );

  out = replaceOnce(
    out,
    '<script type="module" src="./app.js"></script>',
    `<script type="module">\n/* This file is the single-file build output. Source of truth lives in the repo root (index.html/app.js/styles.css). */\n\n${js}\n</script>`,
    "JS script tag",
  );

  await mkdir(OUT_DIR, { recursive: true });
  await writeFile(OUT_HTML, out, "utf8");
  console.log(`[build-dist] Wrote ${path.relative(ROOT, OUT_HTML)}`);
}

main().catch((e) => {
  fail(e?.stack || String(e));
});
