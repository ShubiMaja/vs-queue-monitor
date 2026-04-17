// Run after editing app.js, styles.css, or index.html: npm run build
import { cp, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const ROOT = path.resolve(process.cwd());
const SRC_HTML = path.join(ROOT, "index.html");
const SRC_CSS = path.join(ROOT, "styles.css");
const SRC_JS = path.join(ROOT, "app.js");
const OUT_DIR = path.join(ROOT, "dist");
const OUT_HTML = path.join(OUT_DIR, "index.html");
const ASSETS_SRC = path.join(ROOT, "assets");

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

  const scriptRe =
    /<script type="module" src="\.\/app\.js(?:\?v=[^"]*)?"><\/script>/g;
  const scriptMatches = [...out.matchAll(scriptRe)];
  if (scriptMatches.length === 0) {
    fail('Could not find JS script tag (expected src="./app.js" with optional ?v= cache bust).');
  }
  if (scriptMatches.length > 1) fail("Found JS script tag more than once.");
  const scriptMatch = scriptMatches[0];
  out =
    out.slice(0, scriptMatch.index) +
    `<script type="module">\n/* This file is the single-file build output. Source of truth lives in the repo root (index.html/app.js/styles.css). */\n\n${js}\n</script>` +
    out.slice(scriptMatch.index + scriptMatch[0].length);

  const verMatch = /const\s+APP_VERSION\s*=\s*"([^"]+)"/.exec(js);
  if (!verMatch) fail("Could not parse APP_VERSION from app.js");
  const version = verMatch[1];
  const versionJson = `${JSON.stringify({ version }, null, 2)}\n`;

  await mkdir(OUT_DIR, { recursive: true });
  await writeFile(OUT_HTML, out, "utf8");
  console.log(`[build-dist] Wrote ${path.relative(ROOT, OUT_HTML)}`);

  try {
    await cp(ASSETS_SRC, path.join(OUT_DIR, "assets"), { recursive: true });
    console.log(`[build-dist] Copied assets → ${path.relative(ROOT, path.join(OUT_DIR, "assets"))}`);
  } catch (e) {
    console.warn(`[build-dist] assets copy skipped: ${e?.message || e}`);
  }

  await writeFile(path.join(OUT_DIR, "version.json"), versionJson, "utf8");
  console.log(`[build-dist] Wrote ${path.relative(ROOT, path.join(OUT_DIR, "version.json"))}`);

  await writeFile(path.join(ROOT, "version.json"), versionJson, "utf8");
  console.log(`[build-dist] Wrote ${path.relative(ROOT, path.join(ROOT, "version.json"))}`);
}

main().catch((e) => {
  fail(e?.stack || String(e));
});
