# SPDX-License-Identifier: MIT
"""Build receipt for the DaedalusLink plugin, written right after a successful UBT link.

    python build_receipt.py write --repo R --plugin LIVE_PLUGIN_DIR --dll DLL --ubt-log LOG
                                  [--repo-plugin engines/unreal/DaedalusLink] [--base SHA]
                                  [--backup-dll OLD_DLL] [--out build-receipt.json]
    python build_receipt.py verify --receipt build-receipt.json [--plugin DIR]
    python build_receipt.py pins-diff --receipt build-receipt.json --pins protected-files.json [--pins ...]

write      refuses (exit 2) unless the UBT log has a 'Result: Succeeded' line. It records git HEAD/branch,
           merged PRs since --base, every plugin Source file (+ .uplugin) with sha256, git blob sha and whether
           it is byte-equal to HEAD, the DLL sha256/size/mtime, the old DLL hash, the UBT log sha256 and its
           success line. A sidecar <receipt>.sha256 holds the receipt's own hash.
verify     re-hashes the live plugin and DLL. Exit 0 = no drift, 1 = drift, 3 = receipt/sidecar mismatch.
pins-diff  read-only comparison of protected-files style rows ({path, sha256}) to the receipt.
           Exit 0 = every pinned plugin row matches, 1 = mismatches listed.
Stdlib only. Nothing is modified except the receipt files that write creates.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

SCHEMA = "daedalus.plugin-build-receipt.v1"
SUCCESS_RE = re.compile(r"^\s*Result:\s*Succeeded\b")
MERGE_RE = re.compile(r"Merge pull request #(\d+)")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_blob(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, text=True).stdout


def plugin_files(plugin):
    """Relative posix paths of Source/** files and top-level *.uplugin, sorted."""
    out = []
    src = os.path.join(plugin, "Source")
    for root, dirs, names in os.walk(src):
        dirs.sort()
        for n in names:
            out.append(os.path.relpath(os.path.join(root, n), plugin).replace(os.sep, "/"))
    out += [n for n in os.listdir(plugin) if n.endswith(".uplugin") and os.path.isfile(os.path.join(plugin, n))]
    return sorted(out)


def head_blobs(repo, repo_plugin):
    blobs = {}
    prefix = repo_plugin.strip("/") + "/"
    for line in git(repo, "ls-tree", "-r", "HEAD", "--", repo_plugin).splitlines():
        meta, path = line.split("\t", 1)
        blobs[path[len(prefix):]] = meta.split()[2]
    return blobs


def merged_prs(repo, base):
    if not base:
        return None
    rows = []
    for line in git(repo, "log", "--first-parent", "--format=%H%x09%s", "%s..HEAD" % base).splitlines():
        sha, subject = line.split("\t", 1)
        m = MERGE_RE.search(subject)
        if m:
            rows.append({"pr": int(m.group(1)), "merge_commit": sha, "subject": subject})
    return rows


def read_log_lines(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = data.decode("utf-16")
    elif data.count(b"\x00") > len(data) // 4:
        text = data.decode("utf-16-le", errors="replace")
    else:
        text = data.decode("utf-8", errors="replace")
    return text.splitlines()


def success_line(path):
    found = None
    for number, line in enumerate(read_log_lines(path), 1):
        if SUCCESS_RE.match(line):
            found = {"line": number, "text": line.strip()}
    return found


def file_stat(path):
    st = os.stat(path)
    return {"path": os.path.abspath(path), "sha256": sha256_file(path), "bytes": st.st_size,
            "mtime_utc": datetime.datetime.fromtimestamp(st.st_mtime, datetime.timezone.utc).isoformat()}


def canonical(obj):
    return (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode("utf-8")


def write_receipt(args):
    ok = success_line(args.ubt_log)
    if not ok:
        print("REFUSED: no 'Result: Succeeded' line in %s" % args.ubt_log)
        return 2
    blobs = head_blobs(args.repo, args.repo_plugin)
    files = []
    for rel in plugin_files(args.plugin):
        with open(os.path.join(args.plugin, rel), "rb") as fh:
            data = fh.read()
        blob = git_blob(data)
        files.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "git_blob": blob,
                      "head_blob": blobs.get(rel), "equal_to_head": blobs.get(rel) == blob})
    receipt = {
        "schema": SCHEMA,
        "written_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repo": {"head": git(args.repo, "rev-parse", "HEAD").strip(),
                 "branch": git(args.repo, "rev-parse", "--abbrev-ref", "HEAD").strip(),
                 "repo_plugin": args.repo_plugin, "base": args.base, "merged_prs": merged_prs(args.repo, args.base)},
        "plugin": os.path.abspath(args.plugin),
        "files": files,
        "summary": {"files": len(files), "equal_to_head": sum(f["equal_to_head"] for f in files),
                    "not_in_head": [f["path"] for f in files if f["head_blob"] is None],
                    "differs_from_head": [f["path"] for f in files if f["head_blob"] and not f["equal_to_head"]]},
        "dll": file_stat(args.dll),
        "old_dll": file_stat(args.backup_dll) if args.backup_dll else None,
        "ubt_log": {"path": os.path.abspath(args.ubt_log), "sha256": sha256_file(args.ubt_log), "success": ok},
    }
    data = canonical(receipt)
    with open(args.out, "wb") as fh:
        fh.write(data)
    digest = hashlib.sha256(data).hexdigest()
    with open(args.out + ".sha256", "w", encoding="utf-8") as fh:
        fh.write("%s  %s\n" % (digest, os.path.basename(args.out)))
    print(json.dumps({"receipt": os.path.abspath(args.out), "sha256": digest, "summary": receipt["summary"]}, indent=1))
    return 0


def load_receipt(path):
    with open(path, "rb") as fh:
        data = fh.read()
    side = path + ".sha256"
    recorded = ""
    if os.path.exists(side):
        with open(side, encoding="utf-8") as fh:
            recorded = (fh.read().split() or [""])[0]
    if recorded != hashlib.sha256(data).hexdigest():
        raise ValueError("receipt does not match its .sha256 sidecar: %s" % path)
    receipt = json.loads(data)
    if receipt.get("schema") != SCHEMA:
        raise ValueError("not a %s receipt" % SCHEMA)
    return receipt


def drift(receipt, plugin=None):
    plugin = plugin or receipt["plugin"]
    want = {f["path"]: f["sha256"] for f in receipt["files"]}
    have = {rel: sha256_file(os.path.join(plugin, rel)) for rel in plugin_files(plugin)}
    out = {"changed": sorted(p for p in want if p in have and have[p] != want[p]),
           "added": sorted(p for p in have if p not in want),
           "missing": sorted(p for p in want if p not in have)}
    dll = receipt["dll"]["path"]
    out["dll"] = None if os.path.exists(dll) and sha256_file(dll) == receipt["dll"]["sha256"] else \
        {"receipt": receipt["dll"]["sha256"], "live": sha256_file(dll) if os.path.exists(dll) else None}
    return out


def norm(path):
    return os.path.normcase(os.path.normpath(path)).replace("\\", "/")


def pins_diff(receipt, rows):
    root = norm(receipt["plugin"]) + "/"
    by_path = {root + norm(f["path"]): f["sha256"] for f in receipt["files"]}
    by_path[norm(receipt["dll"]["path"])] = receipt["dll"]["sha256"]
    out = {"checked": 0, "mismatched": [], "not_in_receipt": [], "outside_plugin": 0}
    for row in rows:
        p = norm(row["path"])
        if p not in by_path:
            if p.startswith(root):
                out["not_in_receipt"].append(row["path"])
            else:
                out["outside_plugin"] += 1
            continue
        out["checked"] += 1
        if row.get("sha256") != by_path[p]:
            out["mismatched"].append({"path": row["path"], "pinned": row.get("sha256"), "receipt": by_path[p]})
    return out


def load_rows(path):
    """Rows from a protected-files list, or from a parity-pass style dict (files, source_manifest.files,
    binary, canonical_header)."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        rows = list(data.get("files") or []) + list((data.get("source_manifest") or {}).get("files") or [])
        rows += [data[k] for k in ("binary", "canonical_header") if isinstance(data.get(k), dict)]
        data = rows
    return [r for r in data if isinstance(r, dict) and "path" in r]


def main(argv=None):
    ap = argparse.ArgumentParser(description="DaedalusLink plugin build receipt")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("--repo", required=True)
    w.add_argument("--plugin", required=True)
    w.add_argument("--repo-plugin", default="engines/unreal/DaedalusLink")
    w.add_argument("--dll", required=True)
    w.add_argument("--ubt-log", required=True)
    w.add_argument("--backup-dll")
    w.add_argument("--base")
    w.add_argument("--out", default="build-receipt.json")
    v = sub.add_parser("verify")
    v.add_argument("--receipt", required=True)
    v.add_argument("--plugin")
    p = sub.add_parser("pins-diff")
    p.add_argument("--receipt", required=True)
    p.add_argument("--pins", action="append", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "write":
        return write_receipt(args)
    try:
        receipt = load_receipt(args.receipt)
    except ValueError as e:
        print("RECEIPT INVALID: %s" % e)
        return 3
    if args.cmd == "verify":
        d = drift(receipt, args.plugin)
        print(json.dumps(d, indent=1))
        return 1 if (d["changed"] or d["added"] or d["missing"] or d["dll"]) else 0
    rows = [r for path in args.pins for r in load_rows(path)]
    d = pins_diff(receipt, rows)
    print(json.dumps(d, indent=1))
    return 1 if d["mismatched"] else 0


if __name__ == "__main__":
    sys.exit(main())
