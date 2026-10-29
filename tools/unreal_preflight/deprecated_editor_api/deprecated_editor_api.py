# SPDX-License-Identifier: MIT
"""Read-only scan for deprecated Unreal editor Python APIs (UE 5.0+).

Reports every call to the deprecated ``unreal.EditorLevelLibrary`` (and
friends) with the subsystem replacement. It never edits a file.

    python tools/unreal_preflight/deprecated_editor_api/deprecated_editor_api.py [--root .] [--out report.md] [--json]
Exit code is always 0 (report only); use --fail-on-hits to make it a gate.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict

# deprecated class -> replacement subsystem (UE 5.0 deprecation notes)
REPLACEMENTS = {
    "EditorLevelLibrary": "UnrealEditorSubsystem / EditorActorSubsystem / LevelEditorSubsystem",
    "EditorFilterLibrary": "EditorActorSubsystem filtering or plain Python",
    "EditorStaticMeshLibrary": "StaticMeshEditorSubsystem",
    "EditorSkeletalMeshLibrary": "SkeletalMeshEditorSubsystem",
}
METHOD_HINTS = {
    "get_editor_world": "unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()",
    "get_game_world": "unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()",
    "get_all_level_actors": "unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()",
    "save_current_level": "unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()",
    "save_all_dirty_levels": "unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_all_dirty_levels()",
    "pilot_level_actor": "unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).pilot_level_actor(a)",
    "eject_pilot_level_actor": "unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).eject_pilot_level_actor()",
}
SAVES = {"save_current_level", "save_all_dirty_levels"}
PATTERN = re.compile(r"\bunreal\.(" + "|".join(REPLACEMENTS) + r")\.(\w+)")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "Intermediate", "Binaries", "Saved"}


@dataclass(frozen=True)
class Hit:
    path: str
    line: int
    api: str
    method: str
    replacement: str
    saves_level: bool
    in_string: bool


def scan_text(path: str, text: str) -> list[Hit]:
    hits = []
    for no, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        for m in PATTERN.finditer(line):
            api, method = m.group(1), m.group(2)
            before = line[: m.start()]
            in_string = (before.count('"') % 2 == 1) or (before.count("'") % 2 == 1)
            hits.append(Hit(path, no, api, method,
                            METHOD_HINTS.get(method, REPLACEMENTS[api]),
                            method in SAVES, in_string))
    return hits


def scan_tree(root: str) -> list[Hit]:
    out: list[Hit] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            full = os.path.join(dirpath, name)
            if os.path.abspath(full) == os.path.abspath(__file__):
                continue
            try:
                with open(full, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out.extend(scan_text(rel, text))
    return out


def owner_of(path: str) -> str:
    parts = path.split("/")
    if parts[:2] == ["tools", "islands"] and len(parts) > 2:
        return "islands/" + parts[2]
    return "/".join(parts[:2]) if len(parts) > 2 else parts[0]


def render_markdown(hits: list[Hit]) -> str:
    files = sorted({h.path for h in hits})
    lines = ["# Deprecated Unreal editor Python API report", "",
             f"{len(hits)} call(s) in {len(files)} file(s). Read-only report; no script was edited.",
             "Rows marked SAVE call a level save; review that they cannot save the persistent world.", "",
             "| Owner area | File:line | Call | Replacement | Notes |", "|---|---|---|---|---|"]
    for h in sorted(hits, key=lambda h: (owner_of(h.path), h.path, h.line)):
        notes = ", ".join(n for n, on in (("SAVE", h.saves_level), ("inside string", h.in_string)) if on)
        lines.append(f"| {owner_of(h.path)} | `{h.path}:{h.line}` | `{h.api}.{h.method}` | `{h.replacement}` | {notes} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=".")
    p.add_argument("--out")
    p.add_argument("--json", action="store_true")
    p.add_argument("--fail-on-hits", action="store_true")
    a = p.parse_args(argv)
    hits = scan_tree(a.root)
    body = json.dumps([asdict(h) for h in hits], indent=2) if a.json else render_markdown(hits)
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        print(f"{len(hits)} hit(s) -> {a.out}")
    else:
        sys.stdout.write(body)
    return 1 if (a.fail_on_hits and hits) else 0


if __name__ == "__main__":
    raise SystemExit(main())
