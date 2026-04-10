"""One-shot: strip QueueMonitorApp methods duplicated in QueueMonitorEngine (run from repo root)."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / "vs_queue_monitor" / "gui.py"
ENGINE = ROOT / "vs_queue_monitor" / "engine.py"

et = ast.parse(ENGINE.read_text(encoding="utf-8"))
ENGINE_METHODS: set[str] = set()
for n in et.body:
    if isinstance(n, ast.ClassDef) and n.name == "QueueMonitorEngine":
        ENGINE_METHODS = {x.name for x in n.body if isinstance(x, ast.FunctionDef)}
        break

tree = ast.parse(GUI.read_text(encoding="utf-8"))
out_body: list[ast.stmt] = []
for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "QueueMonitorApp":
        kept: list[ast.stmt] = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name in ENGINE_METHODS and item.name != "__init__":
                    continue
            kept.append(item)
        node.body = kept
        node.bases = [
            ast.Name(id="QueueMonitorEngine", ctx=ast.Load()),
            ast.Attribute(value=ast.Name(id="tk", ctx=ast.Load()), attr="Tk", ctx=ast.Load()),
        ]
        out_body.append(node)
    else:
        out_body.append(node)

tree.body = out_body
ast.fix_missing_locations(tree)
GUI.write_text(ast.unparse(tree) + "\n", encoding="utf-8")
print("Stripped", GUI, "engine methods:", sorted(ENGINE_METHODS))
