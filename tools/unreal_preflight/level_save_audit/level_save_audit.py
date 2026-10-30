#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only audit: which editor Python scripts can save the persistent DaedalusWorld map?

Scans *.py files (tests skipped) for level/package saves and grades each file:

  HIGH    a blanket save (save_all_dirty_levels, save_dirty_packages, save_dirty_packages_with_dialog) with no
          world guard, or any save right after loading DaedalusWorld itself, or save_current_level with neither a
          load of another map nor a guard. Whatever world is open when it runs (often DaedalusWorld) is written.
  MEDIUM  save_current_level after the script loads/creates its own map, but nothing checks the open world first.
  LOW     a guard refuses when the open world is DaedalusWorld, or only explicit packages/maps that are not
          DaedalusWorld are saved.

A guard is a line naming DaedalusWorld together with get_editor_world/get_path_name/get_name/world/level and a
refusal (raise, return, sys.exit, abort) within the next 3 lines. Calls inside string literals (code sent to a
bridge) are counted and marked. Nothing is edited; output is a JSON and a Markdown report.

  python level_save_audit.py [--root .] [--json out.json] [--md out.md]   exit 0 none HIGH, 1 any HIGH
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

BLANKET = ("save_all_dirty_levels", "save_dirty_packages", "save_dirty_packages_with_dialog")
CURRENT = ("save_current_level",)
EXPLICIT = ("save_map", "save_packages", "save_level")
SAVE_RE = re.compile(r"\b(" + "|".join(BLANKET + CURRENT + EXPLICIT) + r")\s*\(")
LOAD_RE = re.compile(r"\b(load_level|load_map|new_level|new_map|new_level_from_template)\s*\(([^)]*)\)")
WORLD = "DaedalusWorld"
GUARD_CTX = re.compile(r"get_editor_world|get_path_name|get_name|world|level", re.I)
REFUSE = re.compile(r"\braise\b|\breturn\b|sys\.exit|\babort\b|\bexit\(")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "tests", "fixtures"}


def string_lines(src: str) -> set[int]:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and getattr(n, "end_lineno", None):
            if n.end_lineno > n.lineno:
                out.update(range(n.lineno + 1, n.end_lineno + 1))
            elif "(" in n.value and SAVE_RE.search(n.value):
                out.add(n.lineno)
    return out


def has_guard(lines: list[str], upto: int) -> int | None:
    for i in range(min(upto, len(lines))):
        if WORLD in lines[i] and GUARD_CTX.search(lines[i]):
            window = "\n".join(lines[i:i + 4])
            if REFUSE.search(window):
                return i + 1
    return None


def audit_file(path: Path, rel: str) -> dict | None:
    try:
        src = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None
    if not SAVE_RE.search(src):
        return None
    lines = src.splitlines()
    in_str = string_lines(src)
    calls, loads = [], []
    for i, line in enumerate(lines, 1):
        code = line
        if line.lstrip().startswith("#"):
            continue
        for m in LOAD_RE.finditer(code):
            loads.append({"line": i, "call": m.group(1), "arg": m.group(2).strip()[:120], "world": WORLD in m.group(2)})
        for m in SAVE_RE.finditer(code):
            arg = code[m.end():].split(")", 1)[0]
            calls.append({"line": i, "call": m.group(1), "in_string": i in in_str, "arg": arg.strip()[:120]})
    if not calls:
        return None
    grades, reasons = [], []
    for c in calls:
        guard = has_guard(lines, c["line"] - 1)
        prior = [l for l in loads if l["line"] < c["line"]]
        if guard:
            g, why = "LOW", f"guard at line {guard}"
        elif prior and prior[-1]["world"]:
            g, why = "HIGH", f"loads {WORLD} (line {prior[-1]['line']}) then saves"
        elif c["call"] in BLANKET:
            g, why = "HIGH", "blanket save of every dirty level/package, no world guard"
        elif c["call"] in CURRENT:
            g, why = ("MEDIUM", f"saves current level after {prior[-1]['call']} line {prior[-1]['line']}, no world guard") if prior \
                else ("HIGH", "saves whatever level is open, no load and no world guard")
        else:
            g, why = ("HIGH", f"explicit save names {WORLD}") if WORLD in c["arg"] else ("LOW", "explicit package/map save")
        c.update(grade=g, reason=why)
        grades.append(g)
        reasons.append(why)
    order = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}
    return {"file": rel, "grade": max(grades, key=order.get), "calls": calls, "loads": loads,
            "mentions_world": WORLD in src}


def scan(root: Path) -> list[dict]:
    rows = []
    for p in sorted(root.rglob("*.py")):
        rel = p.relative_to(root).as_posix()
        if any(part in SKIP_DIRS for part in p.parts) or p.name.startswith("test_") or "/fixtures/" in f"/{rel}":
            continue
        if rel.startswith("tools/unreal_preflight/"):  # the audit/lint tools name these calls as patterns
            continue
        r = audit_file(p, rel)
        if r:
            rows.append(r)
    return rows


def owner_area(rel: str) -> str:
    parts = rel.split("/")
    return "/".join(parts[:3]) if len(parts) > 3 else "/".join(parts[:-1])


def to_md(rows: list[dict]) -> str:
    n = {g: sum(r["grade"] == g for r in rows) for g in ("HIGH", "MEDIUM", "LOW")}
    out = ["# Level-save audit (persistent DaedalusWorld risk)", "",
           f"{len(rows)} file(s) save levels or packages: {n['HIGH']} HIGH, {n['MEDIUM']} MEDIUM, {n['LOW']} LOW. "
           "Read-only report; no script was edited.", "",
           "| Grade | Owner area | File:line | Call | Why |", "|---|---|---|---|---|"]
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    for r in sorted(rows, key=lambda r: (order[r["grade"]], r["file"])):
        for c in r["calls"]:
            out.append(f"| {c['grade']} | {owner_area(r['file'])} | `{r['file']}:{c['line']}` | `{c['call']}`"
                       f"{' (in string)' if c['in_string'] else ''} | {c['reason']} |")
    out += ["", "Safer pattern: before any save, read `unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()`",
            "and refuse when its path is the persistent DaedalusWorld; save only your own map/packages explicitly."]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--md", type=Path)
    a = ap.parse_args(argv)
    rows = scan(a.root)
    md = to_md(rows)
    if a.json:
        a.json.write_text(json.dumps({"schema": "daedalus.level-save-audit.v1", "files": rows}, indent=2), encoding="utf-8")
    if a.md:
        a.md.write_text(md, encoding="utf-8")
    print(md if not a.md else md.splitlines()[2])
    return 1 if any(r["grade"] == "HIGH" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
