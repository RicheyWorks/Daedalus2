#!/usr/bin/env python3
"""Every native C++ minigame core has a parity fixture and a core test CI builds and runs.

A native core is Public/Daedalus{Name}Core.h for a game in docs/minigames/catalog.json
(desktop games and python games). Desktop host headers under DesktopGames/ are cabinets,
not this set. Disk, stable, and realm cores are not catalog minigames, so they are skipped.

For each core the check requires:
  * engines/unreal/core-test/{id}_parity.txt with at least one line,
  * engines/unreal/core-test/{id}_core_test.cpp that includes that header,
  * one workflow run script that compiles that cpp and runs it with the fixture.

No game rules are read or changed.

  python tools/minigames/minigame_core_parity.py --check
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CATALOG = ROOT / "docs/minigames/catalog.json"
PUBLIC = ROOT / "engines/unreal/DaedalusLink/Source/DaedalusLink/Public"
CORE_TEST = ROOT / "engines/unreal/core-test"
WORKFLOWS = ROOT / ".github/workflows"

_RUN = re.compile(r"(?m)^([ \t]*)run:[ \t]*(.*)$")


def pascal(game_id):
    return "".join(part.capitalize() for part in game_id.split("_") if part)


def run_scripts(text):
    """Bodies of workflow `run:` steps. Names and comments outside a run do not count."""
    scripts = []
    for match in _RUN.finditer(text):
        indent = len(match.group(1).replace("\t", "    "))
        first = match.group(2).strip()
        if first in ("|", ">", "|-", ">-", "|+", ">+"):
            lines = []
            for line in text[match.end():].splitlines():
                if line.strip() == "":
                    lines.append(line)
                    continue
                lead = len(line) - len(line.lstrip(" \t"))
                if lead > indent:
                    lines.append(line)
                else:
                    break
            scripts.append("\n".join(lines))
        else:
            scripts.append(first)
    return scripts


def workflow_runs(root):
    folder = root / ".github/workflows"
    if not folder.is_dir():
        return []
    scripts = []
    for path in sorted(folder.glob("*.yml")):
        scripts.extend(run_scripts(path.read_text(encoding="utf-8")))
    return scripts


def minigame_ids(catalog):
    ids = []
    for section in ("games", "python_games"):
        for game in catalog.get(section, []):
            gid = game.get("id")
            if isinstance(gid, str) and gid:
                ids.append(gid)
    return ids


def gaps(root, catalog, runs):
    """Missing fixture, core test, or CI run for each catalog minigame that has a native core."""
    public = root / "engines/unreal/DaedalusLink/Source/DaedalusLink/Public"
    tests = root / "engines/unreal/core-test"
    found = []
    for gid in minigame_ids(catalog):
        name = pascal(gid)
        header = public / f"Daedalus{name}Core.h"
        if not header.is_file():
            continue
        found.append(gid)
        rel_header = f"Daedalus{name}Core.h"
        fixture = tests / f"{gid}_parity.txt"
        source = tests / f"{gid}_core_test.cpp"
        if not fixture.is_file():
            yield f"{gid}: missing parity fixture engines/unreal/core-test/{gid}_parity.txt"
        elif not fixture.read_text(encoding="utf-8").strip():
            yield f"{gid}: parity fixture engines/unreal/core-test/{gid}_parity.txt is empty"
        if not source.is_file():
            yield f"{gid}: missing core test engines/unreal/core-test/{gid}_core_test.cpp"
        elif rel_header not in source.read_text(encoding="utf-8"):
            yield f"{gid}: {gid}_core_test.cpp does not include {rel_header}"
        cpp = f"{gid}_core_test.cpp"
        fixture_name = f"{gid}_parity.txt"
        if not any(cpp in script and fixture_name in script for script in runs):
            yield (
                f"{gid}: no workflow run script compiles {cpp} and runs it with {fixture_name}"
            )
    if not found:
        yield "no native minigame cores found under Public/Daedalus*Core.h"


def check(root=ROOT):
    catalog_path = root / "docs/minigames/catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    return list(gaps(root, catalog, workflow_runs(root)))


def main():
    problems = check()
    for problem in problems:
        print("FAIL:", problem)
    if problems:
        print(f"{len(problems)} gap(s)")
        return 1
    print(f"minigame cores ok: {len(_covered())}")
    return 0


def _covered():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    covered = []
    for gid in minigame_ids(catalog):
        if (PUBLIC / f"Daedalus{pascal(gid)}Core.h").is_file():
            covered.append(gid)
    return covered


if __name__ == "__main__":
    sys.exit(main())
