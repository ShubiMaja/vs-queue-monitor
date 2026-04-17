import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_HTML = ROOT / "index.html"
SRC_CSS = ROOT / "styles.css"
SRC_JS = ROOT / "app.js"
OUT_DIR = ROOT / "dist"
OUT_HTML = OUT_DIR / "index.html"
ASSETS_SRC = ROOT / "assets"
SW_SRC = ROOT / "sw.js"


def fail(msg: str) -> None:
    raise SystemExit(f"[build-dist] {msg}")


def normalize_newlines(s: str) -> str:
    return s.replace("\r\n", "\n")


def replace_once(haystack: str, needle: str, replacement: str, label: str) -> str:
    idx = haystack.find(needle)
    if idx < 0:
        fail(f"Could not find {label} marker: {needle}")
    if haystack.find(needle, idx + len(needle)) >= 0:
        fail(f"Found {label} marker more than once.")
    return haystack[:idx] + replacement + haystack[idx + len(needle) :]


def main() -> None:
    html = normalize_newlines(SRC_HTML.read_text(encoding="utf-8"))
    css = normalize_newlines(SRC_CSS.read_text(encoding="utf-8"))
    js = normalize_newlines(SRC_JS.read_text(encoding="utf-8"))

    out = html

    out = replace_once(
        out,
        '<link rel="stylesheet" href="./styles.css" />',
        f"<style>\n{css}\n</style>",
        "CSS link tag",
    )

    script_re = re.compile(r'<script type="module" src="\./app\.js(?:\?v=[^"]*)?"></script>')
    matches = list(script_re.finditer(out))
    if len(matches) == 0:
        fail('Could not find JS script tag (expected src="./app.js" with optional ?v= cache bust).')
    if len(matches) > 1:
        fail("Found JS script tag more than once.")

    m = matches[0]
    injected = (
        '<script type="module">\n'
        "/* This file is the single-file build output. Source of truth lives in the repo root (index.html/app.js/styles.css). */\n\n"
        + js
        + "\n</script>"
    )
    out = out[: m.start()] + injected + out[m.end() :]

    ver_m = re.search(r'const\s+APP_VERSION\s*=\s*"([^"]+)"', js)
    if not ver_m:
        fail("Could not parse APP_VERSION from app.js")
    version = ver_m.group(1)
    version_json = json.dumps({"version": version}, indent=2) + "\n"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(out, encoding="utf-8")
    print(f"[build-dist] Wrote {OUT_HTML.relative_to(ROOT)}")

    try:
        if ASSETS_SRC.exists():
            dst = OUT_DIR / "assets"
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(ASSETS_SRC, dst)
            print(f"[build-dist] Copied assets -> {dst.relative_to(ROOT)}")
    except Exception as e:
        print(f"[build-dist] assets copy skipped: {e}")

    try:
        if SW_SRC.exists():
            shutil.copy2(SW_SRC, OUT_DIR / "sw.js")
            print(f"[build-dist] Copied sw.js -> {(OUT_DIR / 'sw.js').relative_to(ROOT)}")
    except Exception as e:
        print(f"[build-dist] sw.js copy skipped: {e}")

    (OUT_DIR / "version.json").write_text(version_json, encoding="utf-8")
    print(f"[build-dist] Wrote {(OUT_DIR / 'version.json').relative_to(ROOT)}")

    (ROOT / "version.json").write_text(version_json, encoding="utf-8")
    print(f"[build-dist] Wrote {(ROOT / 'version.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()

