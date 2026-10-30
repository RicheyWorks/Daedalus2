# SPDX-License-Identifier: MIT
"""Caulking Check (G544, disk-saver): find the seams where text files let water in.

Python dev tooling only; nothing here runs inside Unreal. Reads text files under one or more
folders (read-only; .git, dot-dirs, node_modules, __pycache__ and Unreal build dirs skipped)
and checks the bytes, not the meaning:

  errors (leaking):
    * bad_utf8:        the file is not valid UTF-8,
    * bad_json:        a .json file (or a .jsonl line) does not parse,
    * duplicate_key:   a JSON object repeats a key (json.load silently keeps only the last);
  advisories (weeping):
    * bom:             starts with a UTF-8 byte-order mark,
    * crlf:            has CRLF line endings (counted; `mixed` when LF lines are present too),
    * no_final_newline: non-empty file that does not end with a newline,
    * trailing_space:  lines ending in spaces or tabs (counted; Markdown excluded, where two
                       trailing spaces are a line break),
    * tab_indent:      .py/.yml/.yaml lines indented with a tab (counted).

Extensions checked: .py .md .json .jsonl .yml .yaml .txt .toml .csv .ini .ps1 .sh .cfg.
Verdict sound / weeping / leaking. Stdlib only, deterministic, no clock.

  python tools/streaming/caulking_check.py [--root DIR] [--under tools/streaming ...] [--json] [--fail-on weeping|leaking]

`--under` may repeat; default is the DiskSaver lane (tools/streaming, data/islands/disk-saver,
docs/islands). Exit 0 = report printed, 1 = --fail-on and the verdict is at least that bad,
2 = refusal.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FORMAT = "daedalus-caulking-check"
RANK = {"sound": 0, "weeping": 1, "leaking": 2}
ERRORS = ("bad_utf8", "bad_json", "duplicate_key")
ADVISORIES = ("bom", "crlf", "no_final_newline", "trailing_space", "tab_indent")
ORDER = ERRORS + ADVISORIES
TEXT_EXT = {".py", ".md", ".json", ".jsonl", ".yml", ".yaml", ".txt", ".toml", ".csv", ".ini", ".ps1", ".sh", ".cfg"}
TAB_EXT = {".py", ".yml", ".yaml"}
SKIP_DIRS = {"node_modules", "__pycache__", "Intermediate", "Binaries", "Saved", "DerivedDataCache"}
DEFAULT_UNDER = ("tools/streaming", "data/islands/disk-saver", "docs/islands")
BOM = b"\xef\xbb\xbf"


class CaulkingError(ValueError):
    pass


class _Dup(ValueError):
    pass


def _pairs(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise _Dup(k)
        seen[k] = v
    return seen


def _json_problem(s):
    """None, ("duplicate_key", key) or ("bad_json", message)."""
    try:
        json.loads(s, object_pairs_hook=_pairs)
    except _Dup as e:
        return ("duplicate_key", str(e))
    except ValueError as e:
        return ("bad_json", str(e).split(":")[0])
    return None


def check_bytes(rel, raw):
    """Findings for one file's bytes."""
    ext = os.path.splitext(rel)[1].lower()
    out = []

    def add(kind, **kw):
        out.append(dict({"file": rel, "kind": kind}, **kw))

    if raw.startswith(BOM):
        add("bom")
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        add("bad_utf8", offset=e.start)
        return out
    crlf = text.count("\r\n")
    if crlf:
        lf = text.count("\n") - crlf
        add("crlf", lines=crlf, mixed=lf > 0)
    if text and not text.endswith("\n"):
        add("no_final_newline")
    lines = text.replace("\r\n", "\n").split("\n")
    if ext != ".md":
        ts = [i for i, l in enumerate(lines, 1) if l != l.rstrip(" \t")]
        if ts:
            add("trailing_space", lines=len(ts), first=ts[0])
    if ext in TAB_EXT:
        tabs = [i for i, l in enumerate(lines, 1) if l.startswith("\t") or (l[:len(l) - len(l.lstrip(" \t"))].find("\t") >= 0)]
        if tabs:
            add("tab_indent", lines=len(tabs), first=tabs[0])
    if ext == ".json":
        p = _json_problem(text)
        if p:
            add(p[0], detail=p[1])
    elif ext == ".jsonl":
        for i, l in enumerate(lines, 1):
            if l.strip():
                p = _json_problem(l)
                if p:
                    add(p[0], detail=p[1], line=i)
                    break
    return out


def _files(root, under):
    seen = set()
    for u in under:
        base = os.path.join(root, *u.strip("/").split("/"))
        if os.path.isfile(base):
            cands = [base]
        elif os.path.isdir(base):
            cands = []
            for d, dirs, files in os.walk(base):
                dirs[:] = sorted(x for x in dirs if not x.startswith(".") and x not in SKIP_DIRS)
                cands += [os.path.join(d, f) for f in files]
        else:
            raise CaulkingError(f"{u}: no such file or folder under {root}")
        for c in cands:
            if os.path.splitext(c)[1].lower() in TEXT_EXT:
                seen.add(os.path.relpath(c, root).replace(os.sep, "/"))
    return sorted(seen)


def survey(root, under=DEFAULT_UNDER):
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        raise CaulkingError(f"{root}: not a directory")
    files = _files(root, under)
    findings = []
    for rel in files:
        with open(os.path.join(root, rel), "rb") as f:
            findings += check_bytes(rel, f.read())
    order = {k: i for i, k in enumerate(ORDER)}
    findings.sort(key=lambda x: (order[x["kind"]], x["file"]))
    counts = {k: sum(1 for x in findings if x["kind"] == k) for k in ORDER}
    verdict = "leaking" if any(counts[k] for k in ERRORS) else "weeping" if findings else "sound"
    return {"format": FORMAT, "version": 1, "under": list(under), "files": len(files),
            "findings": findings, "counts": counts, "verdict": verdict}


def text(r):
    c = r["counts"]
    out = [f"caulking check: {r['verdict']} ({r['files']} files; " + ", ".join(f"{c[k]} {k}" for k in ORDER if c[k]) + ")"]
    for x in r["findings"]:
        extra = ", ".join(f"{k}={x[k]}" for k in ("lines", "first", "mixed", "line", "offset", "detail") if k in x)
        out.append(f"  {'!' if x['kind'] in ERRORS else '-'} {x['kind']} {x['file']}" + (f" ({extra})" if extra else ""))
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Caulking Check: encoding, line-ending and JSON-key seams in text files.")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--under", action="append", help="folder or file to check (repeatable)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on", choices=("weeping", "leaking"))
    a = ap.parse_args(argv)
    try:
        r = survey(a.root, tuple(a.under) if a.under else DEFAULT_UNDER)
    except CaulkingError as e:
        print(f"caulking_check: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 1 if a.fail_on and RANK[r["verdict"]] >= RANK[a.fail_on] else 0


if __name__ == "__main__":
    sys.exit(main())
