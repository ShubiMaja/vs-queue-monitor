"""One-time script to retroactively deduplicate session_history.jsonl.

Collapses records that are the same session but stored under different path
formats (token-masked vs raw, case variants on Windows).
Keeps the highest-ranked record per (norm_log_file, session_id).
Also normalizes log_file fields to portable %APPDATA% / $HOME tokens.
"""

import json
import os
import sys
import shutil
from pathlib import Path

# Allow running from project root or scripts/ dir
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vs_queue_monitor.core import normalize_log_path_for_dedup, normalize_log_path_for_storage, get_history_path


def session_merge_rank(rec: dict) -> tuple:
    """Prefer completed > unknown > interrupted > abandoned > crashed, then more points."""
    outcome_rank = {"completed": 4, "unknown": 3, "interrupted": 2, "abandoned": 1, "crashed": 0}
    pts = rec.get("points") or []
    return (
        outcome_rank.get(rec.get("outcome", ""), -1),
        len(pts),
        1 if rec.get("server") else 0,
    )


def dedup_jsonl(path: Path) -> None:
    if not path.exists():
        print(f"File not found: {path}")
        return

    raw_lines = path.read_text(encoding="utf-8").splitlines()
    records = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except Exception as e:
            print(f"  Skipping unparseable line: {e}")

    print(f"Input: {len(records)} records")

    # Dedup by (norm_log_file, session_id), keeping best-ranked record.
    primary: dict[tuple[str, int], dict] = {}
    no_id: list[dict] = []
    for rec in records:
        sid = rec.get("session_id")
        lf = normalize_log_path_for_dedup(str(rec.get("log_file") or ""))
        if sid is not None:
            pk = (lf, int(sid))
            prev = primary.get(pk)
            if prev is None or session_merge_rank(rec) > session_merge_rank(prev):
                primary[pk] = rec
        else:
            no_id.append(rec)

    deduped = list(primary.values()) + no_id
    deduped.sort(key=lambda r: float(r.get("start_epoch") or 0))

    print(f"Output: {len(deduped)} records")

    # Show what collapsed
    by_norm: dict[str, list] = {}
    for (norm_lf, _sid), rec in primary.items():
        by_norm.setdefault(norm_lf, []).append(rec)
    for norm_lf, recs in sorted(by_norm.items()):
        print(f"  {norm_lf}")
        for r in sorted(recs, key=lambda x: x.get("session_id", 0)):
            print(f"    sid={r.get('session_id')} outcome={r.get('outcome')} lf={r.get('log_file', '')[:60]}")

    # Backup original
    backup = path.with_suffix(".jsonl.bak")
    shutil.copy2(path, backup)
    print(f"\nBackup written to: {backup}")

    # Normalize log_file paths to portable tokens
    normalized: list[dict] = []
    norm_changes = 0
    for rec in deduped:
        raw_lf = str(rec.get("log_file") or "")
        normed = normalize_log_path_for_storage(raw_lf)
        if normed != raw_lf:
            rec = dict(rec)
            rec["log_file"] = normed
            norm_changes += 1
        normalized.append(rec)
    if norm_changes:
        print(f"Normalized {norm_changes} log_file path(s) to portable tokens")

    # Write cleaned file
    with open(path, "w", encoding="utf-8") as fh:
        for rec in normalized:
            fh.write(json.dumps(rec) + "\n")
    print(f"Cleaned file written to: {path}")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else get_history_path()
    dedup_jsonl(target)
