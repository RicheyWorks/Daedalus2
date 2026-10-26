#!/usr/bin/env python3
"""Minigame catalog: one source of truth for every desktop arcade game.

Reads the native registry header and the portable test CMakeLists, then writes
docs/minigames/catalog.json (machine-readable, for placing cabinets in Daedalus
realms) and docs/minigames/CATALOG.md (human index).

  python tools/minigames/minigame_catalog.py           # regenerate
  python tools/minigames/minigame_catalog.py --check   # CI: fail on drift or gaps

Checks: every Java cabinet enum value has metadata and registered tests,
every listed game has a factory and vice versa, every *_test.cpp in
desktop_games is registered in CMake, every game has a portable test, and the
generated files are current. Stdlib only. No Unreal, no build.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = ROOT / "engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DesktopGames/DaedalusDesktopGameRegistry.h"
TESTS = ROOT / "engines/unreal/core-test/desktop_games"
JAVA_HDR = ROOT / "engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusJavaArcade.h"
JAVA_PROTO = ROOT / "engines/unreal/DaedalusLink/Source/DaedalusLink/Public/JavaArcade/DaedalusJavaArcadeProtocol.h"
JAVA_TESTS = ROOT / "engines/unreal/core-test/java_arcade/CMakeLists.txt"
OUT_JSON = ROOT / "docs/minigames/catalog.json"
OUT_MD = ROOT / "docs/minigames/CATALOG.md"

# Test-file prefixes per game id (shared-family suites included).
TEST_PREFIX = {
    "dungeon": ["dungeon", "maze"], "pacman": ["pacman", "maze"],
    "asteroids": ["asteroids", "shooters"], "sega_shooter": ["sega", "shooter", "shooters"],
    "star_shooter": ["star", "shooters"], "shadow_ninja": ["ninja", "platformers"],
    "contra": ["contra", "platformers"], "zelda": ["zelda", "platformers"],
    "football": ["football", "sports"], "dodge_ball": ["dodge", "sports"],
}


# Java cabinets: rules stay in the owning Java service; the cabinet only talks to it.
JAVA_META = {
    "Sudoku": {"id": "sudoku", "title": "SudokuPro", "source_repo": "RicheyWorks/sudokupro",
               "summary": "Account-scoped Sudoku boards with pencil notes, hints and saved boards.",
               "tests": ["java_arcade_protocol", "sudoku_saved_games"]},
    "Blackjack": {"id": "blackjack", "title": "BlackJackPro", "source_repo": "RicheyWorks/BlackJackPro",
                  "summary": "Blackjack table with Java-approved actions, table options and recovery context.",
                  "tests": ["java_arcade_protocol"]},
}


def parse_java(errors):
    hdr = JAVA_HDR.read_text(encoding="utf-8")
    m = re.search(r"enum class EDaedalusJavaGame\s*:\s*uint8\s*\{([^}]*)\}", hdr)
    values = [v.strip().split("=")[0].strip() for v in m.group(1).split(",") if v.strip()] if m else []
    if not values:
        errors.append("EDaedalusJavaGame enum not found")
    tests = set(re.findall(r"add_executable\((\w+)", JAVA_TESTS.read_text(encoding="utf-8")))
    proto = JAVA_PROTO.read_text(encoding="utf-8")
    am = re.search(r'return A == "bet"(.*?);', proto, re.S)
    bj_actions = re.findall(r'"(\w+)"', 'A == "bet"' + am.group(1)) if am else []
    out = []
    for v in values:
        meta = JAVA_META.get(v)
        if not meta:
            errors.append(f"Java cabinet '{v}' has no catalog metadata in minigame_catalog.py")
            continue
        for t in meta["tests"]:
            if t not in tests:
                errors.append(f"Java cabinet '{v}' test '{t}' is not in java_arcade/CMakeLists.txt")
        entry = {"id": meta["id"], "title": meta["title"], "summary": meta["summary"],
                 "host": "ADaedalusJavaArcade", "game_enum": f"EDaedalusJavaGame::{v}",
                 "source_repo": meta["source_repo"], "requires": "local Java game service (rules stay in Java)",
                 "portable_tests": sorted(meta["tests"]),
                 "native_status": "source-only; native compile and play acceptance wait for the batched rebuild"}
        if v == "Blackjack":
            entry["actions"] = bj_actions
        out.append(entry)
    for v in sorted(set(JAVA_META) - set(values)):
        errors.append(f"catalog metadata '{v}' has no EDaedalusJavaGame value")
    return out


CORE_DIR = REG.parent
# Capability -> overrides that provide it. Realm builders and hosts read these.
CAPABILITIES = {
    "options": ("SetOption",),
    "title_screen": ("EnterTitle",),
    "fresh_pad_replay": ("SourceControllerButton",),
    "source_keys": ("SourceKeyDown",),
    "pointer": ("SourcePointerButton",),
    "core_pause": ("OwnPause",),
    "save_restore": ("SaveState", "RestoreState"),
}


def parse_capabilities():
    """Map game class name -> sorted capability list, from the native cores' overrides."""
    caps = {}
    for f in sorted(CORE_DIR.glob("*Core.h")):
        parts = re.split(r"\nclass (\w+Game)\b", f.read_text(encoding="utf-8"))
        for i in range(1, len(parts), 2):
            body = parts[i + 1]
            got = set(re.findall(r"(\w+)\([^)]*\)\s*(?:const\s*)?override", body))
            caps[parts[i]] = sorted(k for k, need in CAPABILITIES.items() if all(n in got for n in need))
    return caps


def parse_verified(cmake):
    """Capabilities proven by registered portable tests.

    A test file may declare `// catalog-capability: <cap>: <id> <id> ...` for
    behavior a game provides inside Step instead of through an override.
    """
    verified, errors = {}, []
    for src in sorted(cmake):
        text = (TESTS / src).read_text(encoding="utf-8")
        for cap, ids in re.findall(r"//\s*catalog-capability:\s*(\w+):\s*([\w ]+)", text):
            if cap not in CAPABILITIES:
                errors.append(f"{src} declares unknown capability '{cap}'")
                continue
            for gid in ids.split():
                verified.setdefault(gid, set()).add(cap)
    return verified, errors


def parse_registry(text):
    entries = re.findall(r'\{"([a-z_]+)","([^"]+)","([^"]*)"\}', text)
    factories = dict(re.findall(r'if\(Id=="([a-z_]+)"\) return std::make_unique<(\w+)>', text))
    return entries, factories


def parse_cmake(text):
    return {src: name for name, src in re.findall(r'desktop_test\((\w+) (\w+\.cpp)', text)}


def tests_for(gid, cmake):
    prefixes = TEST_PREFIX.get(gid, [gid])
    out = []
    for src, name in cmake.items():
        stem = src[: -len("_test.cpp")] if src.endswith("_test.cpp") else src
        if stem in prefixes or any(stem.startswith(p + "_") for p in prefixes):
            out.append(name)
    return sorted(out)


def build():
    entries, factory_map = parse_registry(REG.read_text(encoding="utf-8"))
    factories = set(factory_map)
    capmap = parse_capabilities()
    cmake = parse_cmake((TESTS / "CMakeLists.txt").read_text(encoding="utf-8"))
    verified, errors = parse_verified(cmake)
    ids = [e[0] for e in entries]
    for gid in sorted(set(verified) - set(ids)):
        errors.append(f"catalog-capability names unknown game '{gid}'")
    for gid in sorted(set(ids) - factories):
        errors.append(f"listed game '{gid}' has no factory")
    for gid, cls in sorted(factory_map.items()):
        if cls not in capmap:
            errors.append(f"factory class '{cls}' for '{gid}' not found in DesktopGames cores")
    for gid in sorted(factories - set(ids)):
        errors.append(f"factory '{gid}' is not listed")
    for f in sorted(p.name for p in TESTS.glob("*_test.cpp")):
        if f not in cmake:
            errors.append(f"{f} is not registered in desktop_games/CMakeLists.txt")
    games = []
    for gid, title, blurb in entries:
        tests = tests_for(gid, cmake)
        if not tests:
            errors.append(f"game '{gid}' has no portable test")
        games.append({
            "id": gid,
            "title": title,
            "summary": blurb,
            "host": "ADaedalusDesktopArcade",
            "start": f'StartGame("{gid}", Seed)',
            "portable_tests": tests,
            "capabilities": sorted(set(capmap.get(factory_map.get(gid, ""), [])) | verified.get(gid, set())),
            "native_status": "source-only; native compile and play acceptance wait for the batched rebuild",
        })
    java = parse_java(errors)
    data = {
        "schema": "daedalus.minigames.catalog/v1",
        "generated_by": "tools/minigames/minigame_catalog.py",
        "realm_placement": ("Spawn one ADaedalusDesktopArcade cabinet per entry, or one cabinet with a picker; "
                            "call StartGame(id, seed) on use. Derive the seed from realm id + player for repeatable runs."),
        "games": games,
        "java_cabinets": java,
    }
    md = [
        "# Minigame catalog", "",
        "Generated by `tools/minigames/minigame_catalog.py`. Do not edit by hand; rerun the script.", "",
        "Each game runs in an `ADaedalusDesktopArcade` cabinet via `StartGame(id, seed)`. Realm builders can read",
        "`catalog.json` to place cabinets in any Daedalus realm. Native status for all: source only until the",
        "batched rebuild under the editor custodian.", "",
        "| id | title | portable tests |", "|---|---|---|",
    ]
    for g in games:
        md.append(f"| `{g['id']}` | {g['title']} | {len(g['portable_tests'])} |")
    md += ["", "## Capabilities", "",
           "Read from each core's overrides, plus behavior proven by a portable test that declares",
           "`// catalog-capability: <cap>: <ids>` (for games that handle it inside `Step`). A blank cell is a gap.", "",
           "| id | " + " | ".join(CAPABILITIES) + " |", "|---|" + "---|" * len(CAPABILITIES)]
    for g in games:
        md.append(f"| `{g['id']}` | " + " | ".join("yes" if c in g["capabilities"] else "" for c in CAPABILITIES) + " |")
    md += ["", "## Java cabinets", "",
           "Hosted by `ADaedalusJavaArcade`; rules stay in the owning Java service. See `docs/java-arcade/README.md`.", "",
           "| id | title | enum | source | portable tests |", "|---|---|---|---|---|"]
    for j in java:
        md.append(f"| `{j['id']}` | {j['title']} | `{j['game_enum']}` | {j['source_repo']} | {len(j['portable_tests'])} |")
    md.append("")
    return json.dumps(data, indent=2) + "\n", "\n".join(md), errors


def read(p):
    return p.read_text(encoding="utf-8").replace("\r\n", "\n") if p.exists() else ""


def main():
    js, md, errors = build()
    if "--check" in sys.argv:
        if read(OUT_JSON) != js or read(OUT_MD) != md:
            errors.append("docs/minigames catalog is stale; run python tools/minigames/minigame_catalog.py")
        for e in errors:
            print("FAIL:", e)
        print("catalog ok" if not errors else f"{len(errors)} problem(s)")
        return 1 if errors else 0
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(js, encoding="utf-8", newline="\n")
    OUT_MD.write_text(md, encoding="utf-8", newline="\n")
    for e in errors:
        print("WARN:", e)
    d = json.loads(js)
    print(f"wrote {len(d['games'])} games, {len(d['java_cabinets'])} java cabinets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
