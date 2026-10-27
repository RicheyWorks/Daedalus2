"""List plugin C++ merges a batched rebuild must cover (engine-free, read-only git).

    python tools/unreal_preflight/rebuild_delta/rebuild_delta.py <last-rebuilt-sha> [target-ref]

Prints JSON: every first-parent commit on target-ref after the last rebuilt sha that touches
plugin build inputs (.h/.cpp/.cs/.uplugin under engines/unreal/). Refuses if the rebuilt sha is
not an ancestor of the target, so a rebuild never silently misses or double-counts work.
"""
import json
import re
import subprocess
import sys

BUILD_INPUTS = ("*.h", "*.cpp", "*.cs", "*.uplugin")
ROOT = "engines/unreal/"
_PR = re.compile(r"Merge pull request #(\d+)")


def _git(args, cwd):
    return subprocess.run(["git"] + args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def build_paths(root=ROOT):
    return [":(glob)%s**/%s" % (root, pat) for pat in BUILD_INPUTS]


def delta(rebuilt, target="origin/main", cwd=".", root=ROOT):
    ok = subprocess.run(["git", "merge-base", "--is-ancestor", rebuilt, target], cwd=cwd).returncode == 0
    if not ok:
        raise ValueError("%s is not an ancestor of %s" % (rebuilt, target))
    out = _git(["log", "--first-parent", "--format=%H%x09%cI%x09%s", "%s..%s" % (rebuilt, target), "--"]
               + build_paths(root), cwd)
    rows = []
    for line in out.splitlines():
        sha, when, subject = line.split("\t", 2)
        files = _git(["diff", "--name-only", sha + "^1", sha, "--"] + build_paths(root), cwd).split()
        match = _PR.search(subject)
        rows.append({"sha": sha, "short": sha[:8], "when": when, "pr": int(match.group(1)) if match else None,
                     "subject": subject, "files": len(files)})
    rows.reverse()
    return {"rebuilt": rebuilt, "target": _git(["rev-parse", target], cwd).strip(),
            "needs_rebuild": bool(rows), "commits": rows}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print(json.dumps(delta(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "origin/main"), indent=2))
