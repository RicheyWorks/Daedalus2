# SPDX-License-Identifier: MIT
"""Rigging Check (G541, disk-saver): survey the rigging of the CI workflows.

Python dev tooling only; nothing here runs inside Unreal and no workflow is executed.
Reads .github/workflows/*.yml (read-only, plain-text parse, no YAML library) and checks:

  errors (frayed):
    * unpinned:        a `uses:` action with no @ref, or a moving branch ref
                       (main, master, HEAD, latest, dev, develop);
  advisories (slack):
    * major_drift:     an action used on a different major version than the repo's
                       most common one for that action (ties go to the newest),
    * third_party_tag: an action outside actions/ and github/ pinned to a tag, not a
                       40-hex commit SHA,
    * python_drift:    a literal python-version different from the repo's most common,
    * no_permissions:  no top-level `permissions:` block (the token gets default scopes).

Local (./) and docker:// actions are skipped; ${{ }} expressions are skipped.
The repo-wide tallies (`actions`, `python_versions`) always cover every workflow;
`--under PREFIX` keeps findings for workflows whose steps use files under PREFIX.
Verdict taut / slack / frayed. Stdlib only, deterministic, no clock.

  python tools/streaming/rigging_check.py [--root DIR] [--under tools/streaming] [--json] [--fail-on slack|frayed]

Exit 0 = survey printed, 1 = --fail-on and the verdict is at least that bad, 2 = refusal.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FORMAT = "daedalus-rigging-check"
RANK = {"taut": 0, "slack": 1, "frayed": 2}
MOVING = {"main", "master", "head", "latest", "dev", "develop"}
FIRST_PARTY = {"actions", "github"}
USES = re.compile(r"^\s*-?\s*uses\s*:\s*(.+?)\s*$")
PYVER = re.compile(r"^\s*python-version\s*:\s*(.+?)\s*$")
SHA = re.compile(r"^[0-9a-f]{40}$")
ORDER = ("unpinned", "major_drift", "third_party_tag", "python_drift", "no_permissions")


class RiggingError(ValueError):
    pass


def _clean(v):
    v = v.split(" #")[0].strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    return v


def major(ref):
    m = re.match(r"^v?(\d+)", ref)
    return f"v{m.group(1)}" if m else ref


def _major_key(m):
    d = re.match(r"^v(\d+)$", m)
    return (1, int(d.group(1))) if d else (0, m)


def parse(text):
    """{uses: [(line, action, ref or None)], python: [(line, version)], permissions: bool, body: str}."""
    uses, py, perms = [], [], False
    for n, raw in enumerate(text.splitlines(), 1):
        if raw.lstrip().startswith("#"):
            continue
        if raw.startswith("permissions:"):
            perms = True
        m = USES.match(raw)
        if m:
            v = _clean(m.group(1))
            if v.startswith(("./", "docker://")) or "${{" in v:
                continue
            action, _, ref = v.partition("@")
            uses.append((n, action, ref or None))
            continue
        m = PYVER.match(raw)
        if m:
            v = _clean(m.group(1))
            if "${{" not in v and not v.startswith("["):
                py.append((n, v))
    return {"uses": uses, "python": py, "permissions": perms, "body": text}


def _dominant(counts, key=lambda x: x):
    return max(counts, key=lambda k: (counts[k], key(k))) if counts else None


def survey(root, under=None):
    wf_dir = os.path.join(root, ".github", "workflows")
    if not os.path.isdir(wf_dir):
        raise RiggingError(f"{wf_dir}: not a directory")
    parsed = {}
    for name in sorted(os.listdir(wf_dir)):
        if name.endswith((".yml", ".yaml")):
            with open(os.path.join(wf_dir, name), encoding="utf-8", errors="replace") as f:
                parsed[name] = parse(f.read())
    tallies, pycount = {}, {}
    for p in parsed.values():
        for _, action, ref in p["uses"]:
            if ref:
                tallies.setdefault(action, {})
                tallies[action][major(ref)] = tallies[action].get(major(ref), 0) + 1
        for _, v in p["python"]:
            pycount[v] = pycount.get(v, 0) + 1
    dominant = {a: _dominant(c, _major_key) for a, c in tallies.items()}
    py_dom = _dominant(pycount, lambda v: tuple(int(x) for x in re.findall(r"\d+", v)))
    findings, scoped = [], []
    prefix = under.rstrip("/") + "/" if under else None
    for name, p in parsed.items():
        if prefix and prefix not in p["body"]:
            continue
        scoped.append(name)
        for line, action, ref in p["uses"]:
            if ref is None or ref.lower() in MOVING:
                findings.append({"workflow": name, "kind": "unpinned", "action": action, "ref": ref, "line": line})
                continue
            if major(ref) != dominant[action]:
                findings.append({"workflow": name, "kind": "major_drift", "action": action, "ref": ref,
                                 "repo_major": dominant[action], "line": line})
            if action.split("/")[0] not in FIRST_PARTY and not SHA.match(ref):
                findings.append({"workflow": name, "kind": "third_party_tag", "action": action, "ref": ref, "line": line})
        for line, v in p["python"]:
            if v != py_dom:
                findings.append({"workflow": name, "kind": "python_drift", "version": v, "repo_version": py_dom, "line": line})
        if not p["permissions"]:
            findings.append({"workflow": name, "kind": "no_permissions"})
    order = {k: i for i, k in enumerate(ORDER)}
    findings.sort(key=lambda x: (order[x["kind"]], x["workflow"], x.get("line", 0), x.get("action", "")))
    counts = {k: sum(1 for x in findings if x["kind"] == k) for k in ORDER}
    verdict = "frayed" if counts["unpinned"] else "slack" if findings else "taut"
    return {"format": FORMAT, "version": 1, "under": under, "workflows": scoped,
            "actions": {a: {"majors": dict(sorted(c.items())), "repo_major": dominant[a]} for a, c in sorted(tallies.items())},
            "python_versions": dict(sorted(pycount.items())), "repo_python": py_dom,
            "findings": findings, "counts": counts, "verdict": verdict}


def text(r):
    c = r["counts"]
    out = [f"rigging check: {r['verdict']} ({len(r['workflows'])} workflows; " +
           ", ".join(f"{c[k]} {k}" for k in ORDER) + ")"]
    for a, t in r["actions"].items():
        if len(t["majors"]) > 1:
            out.append(f"  drift {a}: " + ", ".join(f"{m} x{n}" for m, n in t["majors"].items()) + f" (repo {t['repo_major']})")
    for x in r["findings"]:
        if x["kind"] == "no_permissions":
            out.append(f"  - no_permissions {x['workflow']}")
        else:
            what = x.get("action") or x.get("version")
            ref = f"@{x['ref']}" if x.get("ref") else ""
            out.append(f"  {'!' if x['kind'] == 'unpinned' else '-'} {x['kind']} {x['workflow']} line {x['line']}: {what}{ref}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Rigging Check: action pinning, version drift and permissions in CI workflows.")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--under", help="only workflows that use files under this prefix")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on", choices=("slack", "frayed"))
    a = ap.parse_args(argv)
    try:
        r = survey(a.root, a.under)
    except RiggingError as e:
        print(f"rigging_check: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 1 if a.fail_on and RANK[r["verdict"]] >= RANK[a.fail_on] else 0


if __name__ == "__main__":
    sys.exit(main())