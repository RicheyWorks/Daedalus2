# SPDX-License-Identifier: MIT
"""PROPOSED (R22 job 1, hephaestus, for Boss review): read-only chunk reconciliation for the R22c -> R22d handoff.

Answers one question with no side effects: across a recovery, was any saved chunk lost, rewritten, or counted twice?

    python reconcile_chunks.py before --ledger <ledger.json> [--chunk 314 --next 3241 --per-kind 3240]
    python reconcile_chunks.py across --before <copy-of-pre-recovery-ledger.json> --after <ledger.json>
    python reconcile_chunks.py session --dir <old-session-folder>

`before`  : the pre-recovery ledger ends exactly at the expected chunk / next index / counts.
`across`  : the post-recovery ledger keeps the pre-recovery history byte-for-byte as data, continues at
            next_index with contiguous non-overlapping ranges, and its counts equal the union of ranges.
`session` : the old session folder does NOT contain clean-stop receipts that the failed run never wrote
            (normal-lease-release.json, released-producer-lock.json, r22-terminal.json) and still holds its
            failure evidence (failure.json, session.json).

It only reads the files named on the command line. It never writes, renames, locks, calls a broker or the
editor, and never edits pins. Exit 0 = consistent, 1 = refused (reasons printed), 2 = bad input.
"""
import argparse
import json
import sys
from pathlib import Path

KINDS = ("skull", "toter")
NEVER_WRITTEN_BY_FAILED_RUN = ("normal-lease-release.json", "released-producer-lock.json", "r22-terminal.json")
FAILURE_EVIDENCE = ("failure.json", "session.json")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _ranges(chunks):
    """Return (reasons, covered index set, last end). Both kinds share one range per chunk in R22."""
    reasons, seen, prev = [], {}, None
    for c in chunks:
        try:
            n, (lo, hi) = c["chunk"], c["range"]
        except (KeyError, TypeError, ValueError):
            return ["malformed chunk row"], set(), None
        if type(n) is not int or type(lo) is not int or type(hi) is not int or hi < lo:
            return ["malformed chunk row %r" % (n,)], set(), None
        if prev is not None:
            if n != prev[0] + 1:
                reasons.append("chunk numbering not contiguous at %s" % n)
            if lo <= prev[2]:
                reasons.append("chunk %s range overlaps an earlier chunk (double count)" % n)
            elif lo != prev[2] + 1:
                reasons.append("gap before chunk %s: %s..%s never saved (loss)" % (n, prev[2] + 1, lo - 1))
        for i in range(lo, hi + 1):
            if i in seen:
                reasons.append("index %s counted in chunks %s and %s" % (i, seen[i], n))
            seen.setdefault(i, n)
        prev = (n, lo, hi)
    numbers = [c["chunk"] for c in chunks]
    dup = sorted({x for x in numbers if numbers.count(x) > 1})
    if dup:
        reasons.append("chunk numbers repeated: %s" % dup)
    receipts = [str(Path(c.get("receipt", "")).name).lower() for c in chunks if c.get("receipt")]
    if len(set(receipts)) != len(receipts):
        reasons.append("a native receipt is referenced by more than one chunk")
    return reasons, set(seen), (prev[2] if prev else None)


def check_before(ledger, chunk=314, next_index=3241, per_kind=3240):
    reasons = []
    chunks = ledger.get("completed_chunks") or []
    if not chunks:
        return ["no completed chunks"]
    r, covered, end = _ranges(chunks)
    reasons += r
    last = chunks[-1]
    if last.get("chunk") != chunk:
        reasons.append("last chunk is %s, expected %s" % (last.get("chunk"), chunk))
    if ledger.get("next_index") != next_index or end is None or end + 1 != next_index:
        reasons.append("next_index %s is not %s / end + 1" % (ledger.get("next_index"), next_index))
    want = {k: per_kind for k in KINDS}
    if ledger.get("saved_counts") != want or ledger.get("source_counts") != want:
        reasons.append("saved/source counts are not %s per kind" % per_kind)
    if end is not None and end != per_kind:
        reasons.append("history ends at %s, counts say %s" % (end, per_kind))
    if len([c for c in chunks if c.get("chunk") == chunk]) != 1:
        reasons.append("chunk %s is not recorded exactly once" % chunk)
    if Path(ledger.get("last_native_receipt", "")).name != Path(last.get("receipt", "")).name:
        reasons.append("last_native_receipt is not the last chunk's receipt")
    return reasons


def check_across(before, after):
    reasons = []
    b, a = before.get("completed_chunks") or [], after.get("completed_chunks") or []
    if not b:
        return ["pre-recovery ledger has no chunks"]
    if a[:len(b)] != b:
        reasons.append("pre-recovery chunk history was changed or truncated (loss)")
        return reasons
    r, covered, end = _ranges(a)
    reasons += r
    new = a[len(b):]
    if new and new[0]["range"][0] != before.get("next_index"):
        reasons.append("first new chunk starts at %s, not pre-recovery next_index %s"
                       % (new[0]["range"][0], before.get("next_index")))
    expected = before["saved_counts"]["skull"] + sum(c["range"][1] - c["range"][0] + 1 for c in new)
    for key in ("saved_counts", "source_counts"):
        if after.get(key) != {k: expected for k in KINDS}:
            reasons.append("%s %s != pre-recovery + new ranges (%s per kind)" % (key, after.get(key), expected))
    if end is not None and after.get("next_index") != end + 1:
        reasons.append("post-recovery next_index is not end + 1")
    if after.get("campaign_deadline_utc") == before.get("campaign_deadline_utc") and new:
        reasons.append("new chunks recorded under the old campaign deadline (window reused)")
    return reasons


def check_session(listing):
    names = {str(n) for n in listing}
    reasons = ["old session contains %s, which the failed run never wrote" % n
               for n in NEVER_WRITTEN_BY_FAILED_RUN if n in names]
    reasons += ["old session lost evidence file %s" % n for n in FAILURE_EVIDENCE if n not in names]
    return reasons


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("before")
    p.add_argument("--ledger", required=True)
    p.add_argument("--chunk", type=int, default=314)
    p.add_argument("--next", type=int, default=3241)
    p.add_argument("--per-kind", type=int, default=3240)
    q = sub.add_parser("across")
    q.add_argument("--before", required=True)
    q.add_argument("--after", required=True)
    s = sub.add_parser("session")
    s.add_argument("--dir", required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "before":
            reasons = check_before(read(args.ledger), args.chunk, args.next, args.per_kind)
        elif args.cmd == "across":
            reasons = check_across(read(args.before), read(args.after))
        else:
            reasons = check_session([x.name for x in Path(args.dir).iterdir()])
    except (OSError, ValueError, KeyError, TypeError) as e:
        print("bad input: %s" % e)
        return 2
    for r in reasons:
        print("REFUSED: " + r)
    print("OK" if not reasons else "REFUSED")
    return 0 if not reasons else 1


if __name__ == "__main__":
    sys.exit(main())