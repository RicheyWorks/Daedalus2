#!/usr/bin/env python3
"""plugin_drift: compare an installed Unreal plugin folder against the repo copy.

Read-only. Walks both trees, hashes every file with SHA-256 and sorts each
relative path into one of: identical, eol_only (same bytes once CRLF/LF are
normalised), differing, live_only, main_only. Writes a JSON manifest
(schema plugin-drift/v1) and a Markdown summary. Exit codes: 0 no drift,
1 drift found, 2 usage or IO error.

Standard library only, so it runs anywhere Python 3.8+ runs.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
from typing import Dict, Iterable, List, Optional

SCHEMA = "plugin-drift/v1"
# Build products and caches, never source. Compared trees skip them.
DEFAULT_EXCLUDE_DIRS = ("Binaries", "Intermediate", "Saved", "DerivedDataCache", ".git", "__pycache__")
CATEGORIES = ("identical", "eol_only", "differing", "live_only", "main_only")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scan_tree(root: str, exclude_dirs: Iterable[str] = DEFAULT_EXCLUDE_DIRS) -> Dict[str, dict]:
    """Return {relative/posix/path: {"sha256", "sha256_lf", "size", "mtime"}} for every file under root."""
    if not os.path.isdir(root):
        raise FileNotFoundError(f"not a directory: {root}")
    skip = set(exclude_dirs)
    out: Dict[str, dict] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skip)
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            with open(full, "rb") as fh:  # read-only
                data = fh.read()
            st = os.stat(full)
            out[rel] = {
                "sha256": _sha256(data),
                "sha256_lf": _sha256(data.replace(b"\r\n", b"\n")),
                "size": st.st_size,
                "mtime": _dt.datetime.fromtimestamp(st.st_mtime, _dt.timezone.utc).isoformat(timespec="seconds"),
            }
    return out


def compare(live: Dict[str, dict], repo: Dict[str, dict]) -> Dict[str, List[dict]]:
    result: Dict[str, List[dict]] = {c: [] for c in CATEGORIES}
    for rel in sorted(set(live) | set(repo)):
        a, b = live.get(rel), repo.get(rel)
        if a and not b:
            result["live_only"].append({"path": rel, "live": a})
        elif b and not a:
            result["main_only"].append({"path": rel, "repo": b})
        elif a["sha256"] == b["sha256"]:
            result["identical"].append({"path": rel, "sha256": a["sha256"]})
        elif a["sha256_lf"] == b["sha256_lf"]:
            result["eol_only"].append({"path": rel, "live": a, "repo": b})
        else:
            result["differing"].append({"path": rel, "live": a, "repo": b})
    return result


def build_manifest(live_root: str, repo_root: str, label: str = "", repo_ref: str = "",
                   exclude_dirs: Iterable[str] = DEFAULT_EXCLUDE_DIRS) -> dict:
    live = scan_tree(live_root, exclude_dirs)
    repo = scan_tree(repo_root, exclude_dirs)
    res = compare(live, repo)
    counts = {c: len(res[c]) for c in CATEGORIES}
    return {
        "schema": SCHEMA,
        "label": label,
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "live_root": live_root,
        "repo_root": repo_root,
        "repo_ref": repo_ref,
        "excluded_dirs": sorted(exclude_dirs),
        "counts": counts,
        "drift": any(counts[c] for c in ("differing", "live_only", "main_only")),
        "files": res,
    }


def render_markdown(m: dict) -> str:
    c = m["counts"]
    lines = [
        f"# Plugin drift: {m.get('label') or 'plugin'}",
        "",
        f"- Generated (UTC): {m['generated_utc']}",
        f"- Live: `{m['live_root']}`",
        f"- Repo: `{m['repo_root']}`" + (f" at `{m['repo_ref']}`" if m.get("repo_ref") else ""),
        f"- Drift: **{'YES' if m['drift'] else 'no'}**",
        "",
        "| identical | eol_only | differing | live_only | main_only |",
        "|---:|---:|---:|---:|---:|",
        f"| {c['identical']} | {c['eol_only']} | {c['differing']} | {c['live_only']} | {c['main_only']} |",
        "",
    ]
    for cat in ("live_only", "main_only", "differing", "eol_only"):
        rows = m["files"][cat]
        if not rows:
            continue
        lines += [f"## {cat} ({len(rows)})", ""]
        for r in rows:
            side = r.get("live") or r.get("repo")
            lines.append(f"- `{r['path']}` ({side['size']} B, mtime {side['mtime']})")
        lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--live", required=True, help="installed plugin dir (read only)")
    p.add_argument("--repo", required=True, help="repo plugin dir")
    p.add_argument("--json", dest="out_json", help="write JSON manifest here")
    p.add_argument("--md", dest="out_md", help="write Markdown summary here")
    p.add_argument("--label", default="")
    p.add_argument("--repo-ref", default="", help="commit the repo dir is at, recorded in the manifest")
    p.add_argument("--exclude-dir", action="append", default=None,
                   help="dir names to skip (repeatable); default: " + ",".join(DEFAULT_EXCLUDE_DIRS))
    a = p.parse_args(argv)
    try:
        m = build_manifest(a.live, a.repo, a.label, a.repo_ref,
                           a.exclude_dir if a.exclude_dir else DEFAULT_EXCLUDE_DIRS)
    except OSError as e:
        print(f"plugin_drift: {e}", file=sys.stderr)
        return 2
    if a.out_json:
        with open(a.out_json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(m, fh, indent=2, sort_keys=False)
            fh.write("\n")
    if a.out_md:
        with open(a.out_md, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(render_markdown(m))
    c = m["counts"]
    print("plugin_drift: " + " ".join(f"{k}={v}" for k, v in c.items()) + f" drift={m['drift']}")
    return 1 if m["drift"] else 0


if __name__ == "__main__":
    sys.exit(main())
