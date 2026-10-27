# SPDX-License-Identifier: MIT
"""Post-rebuild pin transition proposal: read-only, built on build_receipt.

    python pin_transition.py propose --receipt build-receipt.json --pins protected-files.json [--pins ...]
                                     --out <your scratch>/pin-transition.json
    python pin_transition.py check --proposal <your scratch>/pin-transition.json

propose  loads a sealed build receipt (build_receipt.load_receipt, sidecar must match), compares every pins file
         with build_receipt.pins_diff and writes one hash-sealed proposal: for each pins file its path and sha256,
         and for each pinned plugin row whose sha256 differs from the receipt the old -> new transition. Rows under
         the plugin that the receipt does not contain are listed as unresolved, never guessed. The output may not be
         a pins file, the receipt, or sit inside the plugin folder.
check    re-reads the proposal's sidecar, re-hashes the receipt and every pins file and re-runs the comparison.
         Any flipped byte, moved pin or changed receipt refuses: the proposal is stale.

It never edits, renames or deletes a pins file, never touches locks or leases and runs nothing. A proposal is
evidence for each pin owner's reviewed adoption, not permission to change pins.
Exit 0 = proposal written / still valid, 1 = refused or stale, 2 = bad input, 3 = receipt invalid.
Stdlib only.
"""
import argparse
import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build_receipt"))
import build_receipt as br  # noqa: E402

SCHEMA = "daedalus.pin-transition-proposal.v1"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def same_or_inside(path, folder):
    p = br.norm(os.path.abspath(path))
    f = br.norm(os.path.abspath(folder)).rstrip("/")
    return p == f or p.startswith(f + "/")


def build(receipt_path, pins_paths):
    receipt = br.load_receipt(receipt_path)
    with open(receipt_path, "rb") as fh:
        receipt_sha = sha256_bytes(fh.read())
    files = []
    for path in pins_paths:
        with open(path, "rb") as fh:
            data = fh.read()
        d = br.pins_diff(receipt, br.load_rows(path))
        files.append({"path": os.path.abspath(path), "sha256": sha256_bytes(data), "checked": d["checked"],
                      "outside_plugin": d["outside_plugin"], "unresolved": sorted(d["not_in_receipt"]),
                      "transitions": sorted(({"path": m["path"], "from_sha256": m["pinned"],
                                              "to_sha256": m["receipt"]} for m in d["mismatched"]),
                                            key=lambda r: r["path"])})
    return {"schema": SCHEMA,
            "receipt": {"path": os.path.abspath(receipt_path), "sha256": receipt_sha,
                        "repo_head": receipt["repo"]["head"], "plugin": receipt["plugin"],
                        "dll_sha256": receipt["dll"]["sha256"]},
            "pins_files": files,
            "summary": {"pins_files": len(files), "transitions": sum(len(f["transitions"]) for f in files),
                        "unresolved": sum(len(f["unresolved"]) for f in files)},
            "note": "proposal only; pins unchanged; adoption stays with each pin owner's reviewed procedure"}


def body(proposal):
    """The comparable part of a proposal (everything but its write time)."""
    return {k: v for k, v in proposal.items() if k != "written_utc"}


def propose(args):
    out = os.path.abspath(args.out)
    for p in args.pins + [args.receipt]:
        if br.norm(out) == br.norm(os.path.abspath(p)):
            print("REFUSED: output would overwrite an input: %s" % p)
            return 1
    try:
        receipt = br.load_receipt(args.receipt)
    except (ValueError, OSError) as e:
        print("RECEIPT INVALID: %s" % e)
        return 3
    if same_or_inside(out, receipt["plugin"]):
        print("REFUSED: output inside the plugin folder")
        return 1
    if os.path.exists(out):
        print("REFUSED: output exists; write a new file: %s" % out)
        return 1
    try:
        proposal = build(args.receipt, args.pins)
    except (ValueError, OSError, KeyError) as e:
        print("BAD INPUT: %s" % e)
        return 2
    proposal["written_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    data = br.canonical(proposal)
    with open(out, "xb") as fh:
        fh.write(data)
    with open(out + ".sha256", "x", encoding="utf-8") as fh:
        fh.write("%s  %s\n" % (sha256_bytes(data), os.path.basename(out)))
    print(json.dumps({"proposal": out, "sha256": sha256_bytes(data), "summary": proposal["summary"]}, indent=1))
    return 0


def check(args):
    try:
        with open(args.proposal, "rb") as fh:
            data = fh.read()
        with open(args.proposal + ".sha256", encoding="utf-8") as fh:
            recorded = (fh.read().split() or [""])[0]
    except OSError as e:
        print("BAD INPUT: %s" % e)
        return 2
    if recorded != sha256_bytes(data):
        print("STALE: proposal does not match its sidecar")
        return 1
    proposal = json.loads(data)
    if proposal.get("schema") != SCHEMA:
        print("BAD INPUT: not a %s proposal" % SCHEMA)
        return 2
    try:
        fresh = build(proposal["receipt"]["path"], [f["path"] for f in proposal["pins_files"]])
    except (ValueError, OSError, KeyError) as e:
        print("STALE: %s" % e)
        return 1
    if body(fresh) != body(proposal):
        print("STALE: receipt or pins changed since the proposal was written")
        return 1
    print(json.dumps({"valid": True, "summary": proposal["summary"]}, indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Post-rebuild pin transition proposal (read-only)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("propose")
    p.add_argument("--receipt", required=True)
    p.add_argument("--pins", action="append", required=True)
    p.add_argument("--out", required=True)
    c = sub.add_parser("check")
    c.add_argument("--proposal", required=True)
    args = ap.parse_args(argv)
    return propose(args) if args.cmd == "propose" else check(args)


if __name__ == "__main__":
    sys.exit(main())