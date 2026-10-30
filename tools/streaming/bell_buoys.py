# SPDX-License-Identifier: MIT
"""Bell Buoys (G538, disk-saver): do the CI path filters ring for the files CI actually uses?

Python dev tooling only; nothing here runs inside Unreal and no workflow is executed.
A workflow with an `on: pull_request: paths:` filter runs only when a changed file matches
one of its patterns. If a run step uses a file the filter does not cover, a change to that
file merges without the check ever ringing. This reads .github/workflows/*.yml and the repo
tree (read-only, plain-text parse, no YAML library) and reports per filtered workflow:

  errors (silent):
    * unguarded:     a repo file (or module directory) a step uses that no paths pattern matches (step\n                     names are ignored; a directory counts if any file in it matches),
    * missing_file:  a step names a repo path that does not exist;
  advisories (muffled):
    * stale_pattern: a paths pattern that matches no file in the repo.

Workflows with no pull_request paths filter (or with paths-ignore) run on every change
and are listed as unfiltered. Patterns use GitHub glob rules (`*` within a segment, `**`
across segments). `--under PREFIX` keeps only workflows whose steps use files under PREFIX.
Verdict ringing / muffled / silent. Stdlib only, deterministic, no clock.

  python tools/streaming/bell_buoys.py [--root DIR] [--under tools/streaming/] [--json] [--fail-on muffled|silent]

Exit 0 = report printed, 1 = --fail-on and the verdict is at least that bad, 2 = refusal.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FORMAT = "daedalus-bell-buoys"
RANK = {"ringing": 0, "muffled": 1, "silent": 2}
TOP = ("tools", "data", "docs", "schemas", "scripts", "assets", "examples")
REF = re.compile(r"(?<![\w$/.-])((?:%s)/[A-Za-z0-9_./*-]*[A-Za-z0-9_*-])" % "|".join(TOP))
MOD = re.compile(r"-m\s+((?:%s)(?:\.[A-Za-z_][A-Za-z0-9_]*)+)" % "|".join(TOP))
SKIP_DIRS = {".git", "node_modules", "target", "__pycache__", ".venv", "build", "Binaries", "Intermediate", "Saved"}


class BuoyError(ValueError):
    pass


def glob_re(pattern):
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
            if pattern.startswith("/", i):
                out[-1] = "(?:.*/)?"
                i += 1
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _strip(v):
    v = v.split(" #")[0].strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    return v


def parse_workflow(text):
    """(paths list or None, paths_ignore flag, [(line_no, step text)] after 'jobs:')."""
    lines = text.splitlines()
    paths, ignore, in_pr, pr_indent, in_paths, paths_indent = None, False, False, -1, False, -1
    jobs_at = None
    for n, raw in enumerate(lines):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        ind = len(raw) - len(raw.lstrip())
        s = raw.strip()
        if ind == 0 and s.startswith("jobs:"):
            jobs_at = n
            break
        if in_paths and ind > paths_indent and s.startswith("-"):
            paths.append(_strip(s[1:]))
            continue
        in_paths = False
        if in_pr and ind <= pr_indent:
            in_pr = False
        if re.match(r"^(pull_request|pull_request_target)\s*:", s):
            in_pr, pr_indent = True, ind
            continue
        if in_pr and s.startswith("paths-ignore:"):
            ignore = True
        elif in_pr and re.match(r"^paths\s*:", s):
            rest = s.split(":", 1)[1].strip()
            paths = [] if paths is None else paths
            if rest.startswith("["):
                paths += [_strip(x) for x in rest.strip("[]").split(",") if x.strip()]
            else:
                in_paths, paths_indent = True, ind
    body = [(n + 1, l) for n, l in enumerate(lines) if jobs_at is not None and n > jobs_at and not l.lstrip().startswith("#")]
    return paths, ignore, body


def repo_files(root):
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not (x.startswith(".") and x != ".github"))
        rel = os.path.relpath(d, root).replace(os.sep, "/")
        for f in sorted(files):
            out.append(f if rel == "." else f"{rel}/{f}")
    return out


def refs(body):
    found = {}
    for n, line in body:
        if re.match(r"^\s*-?\s*name\s*:", line):
            continue
        for m in REF.finditer(line):
            found.setdefault(m.group(1).rstrip("/."), n)
        for m in MOD.finditer(line):
            found.setdefault(m.group(1).replace(".", "/"), n)
    return found


def audit(root, under=None):
    wf_dir = os.path.join(root, ".github", "workflows")
    if not os.path.isdir(wf_dir):
        raise BuoyError(f"{wf_dir}: not a directory")
    files = repo_files(root)
    fileset = set(files)
    rows, findings, unfiltered = [], [], []
    for name in sorted(os.listdir(wf_dir)):
        if not name.endswith((".yml", ".yaml")):
            continue
        with open(os.path.join(wf_dir, name), encoding="utf-8", errors="replace") as f:
            paths, ignore, body = parse_workflow(f.read())
        used = refs(body)
        if under and not any(r.startswith(under.rstrip("/") + "/") or r == under.rstrip("/") for r in used):
            continue
        if paths is None or ignore:
            unfiltered.append(name)
            continue
        pats = [(p, glob_re(p)) for p in paths if p and not p.startswith("!")]
        hit = {p: False for p, _ in pats}
        for fpath in files:
            for p, rx in pats:
                if not hit[p] and rx.match(fpath):
                    hit[p] = True
        checked = 0
        for r, line in sorted(used.items()):
            if "*" in r:
                continue
            if r in fileset:
                targets = [r]
            else:
                targets = [x for x in files if x.startswith(r + "/")]
                if not targets:
                    alt = [x for x in files if x.startswith(r + ".")]
                    if not alt:
                        findings.append({"workflow": name, "kind": "missing_file", "path": r, "line": line})
                        continue
                    targets = alt
            checked += 1
            if not any(rx.match(t) for t in targets for _, rx in pats):
                findings.append({"workflow": name, "kind": "unguarded", "path": r, "line": line})
        for p, _ in pats:
            if not hit[p]:
                findings.append({"workflow": name, "kind": "stale_pattern", "pattern": p})
        rows.append({"workflow": name, "patterns": len(pats), "inputs_checked": checked})
    order = {"unguarded": 0, "missing_file": 1, "stale_pattern": 2}
    findings.sort(key=lambda x: (order[x["kind"]], x["workflow"], x.get("path") or x.get("pattern")))
    counts = {k: sum(1 for x in findings if x["kind"] == k) for k in order}
    verdict = "silent" if counts["unguarded"] or counts["missing_file"] else "muffled" if counts["stale_pattern"] else "ringing"
    return {"format": FORMAT, "version": 1, "under": under, "workflows": rows, "unfiltered": unfiltered,
            "findings": findings, "counts": counts, "verdict": verdict}


def text(r):
    out = [f"bell buoys: {r['verdict']} ({len(r['workflows'])} filtered workflows, {len(r['unfiltered'])} unfiltered; "
           f"{r['counts']['unguarded']} unguarded, {r['counts']['missing_file']} missing, {r['counts']['stale_pattern']} stale)"]
    for x in r["findings"]:
        what = x.get("path") or x.get("pattern")
        where = f" (line {x['line']})" if "line" in x else ""
        out.append(f"  {'-' if x['kind'] == 'stale_pattern' else '!'} {x['kind']} {x['workflow']}: {what}{where}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Bell Buoys: CI paths filters vs the files CI uses.")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--under", help="only workflows whose steps use files under this prefix")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on", choices=("muffled", "silent"))
    a = ap.parse_args(argv)
    try:
        r = audit(a.root, a.under)
    except BuoyError as e:
        print(f"bell_buoys: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 1 if a.fail_on and RANK[r["verdict"]] >= RANK[a.fail_on] else 0


if __name__ == "__main__":
    sys.exit(main())
