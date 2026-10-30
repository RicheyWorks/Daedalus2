# SPDX-License-Identifier: MIT
"""Pier Register (G534, disk-saver): audit the DiskSaver Daedalus hook data files.

Python dev tooling over JSON data only; nothing here runs inside Unreal.
Every DiskSaver island ships a hook file `data/islands/disk-saver/<slug>-v1.json` with a
quest id and an NPC. This reads them all (read-only), with the rules docs in docs/islands
and the tools in tools/streaming, and writes one berth row per hook. Findings:

  errors (unregistered):
    * bad_json:        the file is not a JSON object,
    * no_quest:        no quest id of the form q_<name>,
    * duplicate_quest: two hook files share a quest id,
    * lines_mismatch:  a hook.values entry has no npc.lines line (extra lines are fine);
  advisories (queried):
    * no_doc:          no docs/islands/DISKSAVER-<SLUG or QUEST>.md,
    * no_tool:         no tools/streaming/*.py named after the slug or quest, or naming the file,
    * no_npc:          no npc.name,
    * name_reused:     the same NPC given name (last word) on more than one island.

Files without a quest that carry a report `format` (e.g. a committed G206 baseline) are
reports, not hooks, and are skipped. `--name "Title Given"` checks whether a new NPC's
given name is free. Verdict registered / queried / unregistered. Stdlib only, no clock.

  python tools/streaming/pier_register.py [--root DIR] [--name NAME] [--json] [--fail-on queried|unregistered]

Exit 0 = register printed, 1 = --fail-on (or --name taken) and the result is at least that bad, 2 = refusal.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FORMAT = "daedalus-pier-register"
ERRORS = ("bad_json", "no_quest", "duplicate_quest", "lines_mismatch")
ADVISORIES = ("no_doc", "no_tool", "no_npc", "name_reused")
RANK = {"registered": 0, "queried": 1, "unregistered": 2}
QUEST = re.compile(r"^q_[a-z0-9_]+$")
MAX_BYTES = 4 * 1024 * 1024


class RegisterError(ValueError):
    pass


def given(name):
    return name.split()[-1].lower() if isinstance(name, str) and name.split() else None


def _read(path):
    if os.path.getsize(path) > MAX_BYTES:
        return None
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def register(root):
    data = os.path.join(root, "data", "islands", "disk-saver")
    docs = os.path.join(root, "docs", "islands")
    tools = os.path.join(root, "tools", "streaming")
    if not os.path.isdir(data):
        raise RegisterError(f"{data}: not a directory")
    doc_names = set(os.listdir(docs)) if os.path.isdir(docs) else set()
    tool_src = {}
    if os.path.isdir(tools):
        for n in sorted(os.listdir(tools)):
            if n.endswith(".py") and not n.endswith("_test.py") and not n.startswith("test_"):
                with open(os.path.join(tools, n), encoding="utf-8", errors="replace") as f:
                    tool_src[n[:-3]] = f.read()
    berths, findings, quests, names = [], [], {}, {}
    for fn in sorted(os.listdir(data)):
        if not fn.endswith("-v1.json"):
            continue
        slug = fn[:-len("-v1.json")]
        doc = _read(os.path.join(data, fn))
        if not isinstance(doc, dict):
            findings.append({"file": fn, "kind": "bad_json"})
            continue
        quest = doc.get("quest")
        if quest is None and "format" in doc:
            continue
        npc = doc.get("npc") if isinstance(doc.get("npc"), dict) else {}
        name = npc.get("name") if isinstance(npc.get("name"), str) and npc.get("name").strip() else None
        row = {"file": fn, "slug": slug, "quest": quest if isinstance(quest, str) else None, "npc": name,
               "doc": None, "tool": None}
        if not isinstance(quest, str) or not QUEST.match(quest):
            findings.append({"file": fn, "kind": "no_quest"})
        else:
            quests.setdefault(quest, []).append(fn)
        stems = {slug.upper()}
        if row["quest"]:
            stems.add(row["quest"][2:].replace("_", "-").upper())
        for s in sorted(stems):
            if f"DISKSAVER-{s}.md" in doc_names:
                row["doc"] = f"docs/islands/DISKSAVER-{s}.md"
                break
        if row["doc"] is None:
            findings.append({"file": fn, "kind": "no_doc"})
        want = {slug.replace("-", "_")} | ({row["quest"][2:]} if row["quest"] else set())
        for t in sorted(tool_src):
            if t in want or any(t.startswith(w) for w in want) or fn in tool_src[t]:
                row["tool"] = f"tools/streaming/{t}.py"
                break
        if row["tool"] is None:
            findings.append({"file": fn, "kind": "no_tool"})
        if name is None:
            findings.append({"file": fn, "kind": "no_npc"})
        else:
            names.setdefault(given(name), []).append((fn, name))
        hook = doc.get("hook") if isinstance(doc.get("hook"), dict) else {}
        lines = npc.get("lines")
        if isinstance(hook.get("values"), list) and isinstance(lines, dict) and not set(map(str, hook["values"])) <= set(lines):
            findings.append({"file": fn, "kind": "lines_mismatch", "missing": sorted(set(map(str, hook["values"])) - set(lines)),
                             "values": sorted(map(str, hook["values"]))})
        berths.append(row)
    for q in sorted(quests):
        if len(quests[q]) > 1:
            findings.append({"file": None, "kind": "duplicate_quest", "quest": q, "files": quests[q]})
    for g in sorted(names):
        if len(names[g]) > 1:
            findings.append({"file": None, "kind": "name_reused", "given": g,
                             "npcs": [{"file": f, "name": n} for f, n in names[g]]})
    order = {k: i for i, k in enumerate(ERRORS + ADVISORIES)}
    findings.sort(key=lambda x: (order[x["kind"]], x["file"] or "", json.dumps(x, sort_keys=True)))
    counts = {k: sum(1 for x in findings if x["kind"] == k) for k in ERRORS + ADVISORIES}
    verdict = "unregistered" if any(counts[k] for k in ERRORS) else "queried" if findings else "registered"
    return {"format": FORMAT, "version": 1, "berths": berths, "findings": findings, "counts": counts,
            "given_names": sorted(names), "verdict": verdict}


def name_check(reg, name):
    g = given(name)
    if g is None:
        raise RegisterError("--name must be a nonempty name")
    taken = [b for b in reg["berths"] if b["npc"] and given(b["npc"]) == g]
    return {"name": name, "given": g, "free": not taken, "taken_by": [{"file": b["file"], "npc": b["npc"]} for b in taken]}


def text(r):
    out = [f"pier register: {r['verdict']} ({len(r['berths'])} hooks; "
           f"{sum(r['counts'][k] for k in ERRORS)} errors, {sum(r['counts'][k] for k in ADVISORIES)} advisories)"]
    for x in r["findings"]:
        bits = " ".join(f"{k}={json.dumps(v)}" for k, v in sorted(x.items()) if k not in ("kind", "file"))
        out.append(f"  {'!' if x['kind'] in ERRORS else '-'} {x['kind']} {x['file'] or '*'} {bits}".rstrip())
    if "name_check" in r:
        n = r["name_check"]
        out.append(f"  name {n['name']!r}: " + ("free" if n["free"] else
                   "taken by " + ", ".join(f"{t['npc']} ({t['file']})" for t in n["taken_by"])))
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pier Register: audit the DiskSaver hook data files.")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--name", help="check whether a new NPC given name is free")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on", choices=("queried", "unregistered"))
    a = ap.parse_args(argv)
    try:
        r = register(a.root)
        if a.name is not None:
            r["name_check"] = name_check(r, a.name)
    except RegisterError as e:
        print(f"pier_register: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    bad = a.fail_on and RANK[r["verdict"]] >= RANK[a.fail_on]
    return 1 if bad or ("name_check" in r and not r["name_check"]["free"]) else 0


if __name__ == "__main__":
    sys.exit(main())