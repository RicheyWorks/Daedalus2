# SPDX-License-Identifier: MIT
"""Leading Lights (G543, disk-saver): check that the repo's Markdown links lead somewhere.

Python dev tooling only; nothing here runs inside Unreal. Reads every *.md file under the
repo (read-only; .git, dot-dirs, node_modules, Unreal build dirs and __pycache__ skipped) and
follows each relative link and image `[text](target)`:

  errors (dark):
    * broken:         the target file or directory does not exist;
  advisories (dim):
    * missing_anchor: target exists but has no heading for its #anchor (GitHub slug rules),
    * local_path:     link to a machine path (C:\\..., file:, ~/), which only works on one PC,
    * outside_repo:   relative link that climbs out of the repo root,
    * stale_path:     an inline code span naming a repo path (has a /, a file extension,
                      no spaces, wildcards or placeholders) found neither from the repo root
                      nor from the Markdown file's own folder.

Web links (any scheme: http, https, mailto, ...) are not fetched. Links in fenced code blocks
and inline code spans are ignored. A leading / means the repo root, as on GitHub.
`--under PREFIX` keeps findings for files whose repo path starts with PREFIX.
Verdict lit / dim / dark. Stdlib only, deterministic, no network, no clock.

  python tools/streaming/leading_lights.py [--root DIR] [--under docs/islands] [--json] [--fail-on dim|dark]

Exit 0 = report printed, 1 = --fail-on and the verdict is at least that bad, 2 = refusal.
"""
import argparse
import json
import os
import re
import sys
from urllib.parse import unquote

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FORMAT = "daedalus-leading-lights"
RANK = {"lit": 0, "dim": 1, "dark": 2}
ORDER = ("broken", "missing_anchor", "local_path", "outside_repo", "stale_path")
SKIP_DIRS = {"node_modules", "__pycache__", "Intermediate", "Binaries", "Saved", "DerivedDataCache"}
LINK = re.compile(r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+[\"'][^\"']*[\"'])?\s*\)")
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
DRIVE = re.compile(r"^[a-zA-Z]:[\\/]")
FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
CODE_SPAN = re.compile(r"`+[^`]*`+")
PATHY = re.compile(r"^(?:\./)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\.(?:py|md|json|jsonl|yml|yaml|txt|cs|cpp|h|java|toml|ini|csv|ps1|sh)$")
ROOTS = ("tools/", "docs/", "data/", ".github/", "server/", "Source/", "Plugins/", "scripts/")
HTML_ANCHOR = re.compile(r"""<a\s+[^>]*(?:name|id)\s*=\s*["']([^"']+)["']""", re.I)


class LightsError(ValueError):
    pass


def _bare(v):
    return v[2:] if v.startswith("./") else v


def slug(text):
    """GitHub-style heading anchor."""
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    t = t.strip().lower().replace("`", "")
    t = re.sub(r"[^\w\- ]", "", t, flags=re.UNICODE)
    return t.replace(" ", "-")


def scan(text):
    """(links [(line, target)], anchors set) for one Markdown text."""
    links, anchors, seen, fence, spans = [], set(), {}, None, []
    for n, line in enumerate(text.splitlines(), 1):
        f = FENCE.match(line)
        if f:
            if fence is None:
                fence = f.group(1)
            elif f.group(1) == fence:
                fence = None
            continue
        if fence:
            continue
        for a in HTML_ANCHOR.findall(line):
            anchors.add(a.lower())
        h = HEADING.match(line)
        if h:
            s = slug(h.group(1))
            k = seen.get(s, 0)
            anchors.add(s if k == 0 else f"{s}-{k}")
            seen[s] = k + 1
        for m in LINK.finditer(CODE_SPAN.sub("", line)):
            links.append((n, m.group(1)))
        for s in CODE_SPAN.findall(line):
            v = s.strip("`").strip()
            if PATHY.match(v) and _bare(v).startswith(ROOTS):
                spans.append((n, v))
    return links, anchors, spans


def _md_files(root):
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if not x.startswith(".") and x not in SKIP_DIRS)
        for f in sorted(files):
            if f.lower().endswith(".md"):
                out.append(os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/"))
    return sorted(out)


def _read(path):
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def survey(root, under=None):
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        raise LightsError(f"{root}: not a directory")
    files = _md_files(root)
    if under:
        prefix = under.strip("/")
        files = [f for f in files if f == prefix or f.startswith(prefix + "/")]
    cache, findings, total = {}, [], 0

    def anchors_of(rel):
        if rel not in cache:
            cache[rel] = scan(_read(os.path.join(root, rel)))[1]
        return cache[rel]

    for rel in files:
        links, own, spans = scan(_read(os.path.join(root, rel)))
        cache[rel] = own
        for line, v in spans:
            here = os.path.dirname(os.path.join(root, rel))
            if not any(os.path.exists(os.path.join(b, _bare(v))) for b in (root, here)):
                findings.append({"file": rel, "line": line, "kind": "stale_path", "target": v})
        for line, target in links:
            if DRIVE.match(target) or target.lower().startswith("file:") or target.startswith("~"):
                total += 1
                findings.append({"file": rel, "line": line, "kind": "local_path", "target": target})
                continue
            if SCHEME.match(target):
                continue
            total += 1
            path, _, anchor = target.partition("#")
            path, anchor = unquote(path), unquote(anchor).lower()
            if not path:
                dest = rel
            else:
                base = root if path.startswith("/") else os.path.dirname(os.path.join(root, rel))
                full = os.path.normpath(os.path.join(base, path.lstrip("/")))
                if os.path.relpath(full, root).replace(os.sep, "/").startswith("../") or full == os.path.dirname(root):
                    findings.append({"file": rel, "line": line, "kind": "outside_repo", "target": target})
                    continue
                if not os.path.exists(full):
                    findings.append({"file": rel, "line": line, "kind": "broken", "target": target})
                    continue
                dest = os.path.relpath(full, root).replace(os.sep, "/")
            if anchor and dest.lower().endswith(".md") and os.path.isfile(os.path.join(root, dest)):
                if anchor not in anchors_of(dest):
                    findings.append({"file": rel, "line": line, "kind": "missing_anchor", "target": target})
    order = {k: i for i, k in enumerate(ORDER)}
    findings.sort(key=lambda x: (order[x["kind"]], x["file"], x["line"], x["target"]))
    counts = {k: sum(1 for x in findings if x["kind"] == k) for k in ORDER}
    verdict = "dark" if counts["broken"] else "dim" if findings else "lit"
    return {"format": FORMAT, "version": 1, "under": under, "files": len(files), "links": total,
            "findings": findings, "counts": counts, "verdict": verdict}


def text(r):
    c = r["counts"]
    out = [f"leading lights: {r['verdict']} ({r['files']} files, {r['links']} local links; " +
           ", ".join(f"{c[k]} {k}" for k in ORDER) + ")"]
    for x in r["findings"]:
        out.append(f"  {'!' if x['kind'] == 'broken' else '-'} {x['kind']} {x['file']}:{x['line']} -> {x['target']}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Leading Lights: relative Markdown links that lead nowhere.")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--under", help="only Markdown files whose repo path starts with this prefix")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on", choices=("dim", "dark"))
    a = ap.parse_args(argv)
    try:
        r = survey(a.root, a.under)
    except LightsError as e:
        print(f"leading_lights: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 1 if a.fail_on and RANK[r["verdict"]] >= RANK[a.fail_on] else 0


if __name__ == "__main__":
    sys.exit(main())
