# SPDX-License-Identifier: MIT
"""Harbour Seals (G525, disk-saver): is a committed G206 report still true to its census?

Committed census_budget.py reports (the G505 Beacon Watch baseline, examples, hand-offs)
go stale when the World Census changes or the budget config moves, and nobody notices.
This reads a census.json and a G206 report (both read-only) plus the current G206 config
and seals the report:

  * unsealed: the report names no census_sources, so it cannot be traced;
  * stale:    its census_sources or snapshot_date differ from the census, or its budget
              differs from the current config (priced under an old budget);
  * tampered: same census and budget, but re-pricing the census with G206 does not
              reproduce the report (a field was edited by hand or by an old model);
  * sealed:   re-pricing reproduces the report exactly.

Every difference is listed by path (worlds keyed by id, islands by slot). Stdlib only,
read-only, no clock.

  python tools/streaming/harbour_seals.py CENSUS.json REPORT.json [--config CFG] [--json] [--fail-on-broken]

Exit 0 = seal printed, 1 = --fail-on-broken and the verdict is not sealed, 2 = refusal.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-harbour-seals"
MAX_BYTES = 16 * 1024 * 1024
MAX_DIFFS = 200


class SealError(ValueError):
    pass


def _load_json(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            raise SealError(f"{path}: too large")
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except OSError as e:
        raise SealError(f"{path}: {e.strerror}")
    except ValueError:
        raise SealError(f"{path}: not JSON")


def _key(item):
    if isinstance(item, dict):
        if isinstance(item.get("id"), str):
            return item["id"]
        if isinstance(item.get("slot"), int) and not isinstance(item.get("slot"), bool):
            return f"slot {item['slot']}"
    return None


def flatten(v, path="", out=None):
    """{path: leaf}; lists of worlds/islands are keyed by id / slot so reordering is not a diff."""
    out = {} if out is None else out
    if isinstance(v, dict):
        if not v:
            out[path] = {}
        for k in sorted(v):
            flatten(v[k], f"{path}.{k}" if path else k, out)
    elif isinstance(v, list):
        keys = [_key(x) for x in v]
        if v and all(keys) and len(set(keys)) == len(keys):
            for k, x in sorted(zip(keys, v)):
                flatten(x, f"{path}[{k}]", out)
        elif not v:
            out[path] = []
        else:
            for i, x in enumerate(v):
                flatten(x, f"{path}[{i}]", out)
    else:
        out[path] = v
    return out


def diff(want, got):
    a, b = flatten(want), flatten(got)
    rows = []
    for p in sorted(set(a) | set(b)):
        if p not in b:
            rows.append({"path": p, "kind": "missing", "expected": a[p]})
        elif p not in a:
            rows.append({"path": p, "kind": "extra", "found": b[p]})
        elif a[p] != b[p] or type(a[p]) is not type(b[p]):
            rows.append({"path": p, "kind": "changed", "expected": a[p], "found": b[p]})
    return rows


def seal(census, report, cfg):
    if not isinstance(report, dict) or report.get("format") != cb.FORMAT or report.get("version") != 1:
        raise SealError("report must be a daedalus-census-budget v1 report")
    try:
        fresh = cb.plan(census, cfg)
    except cb.CensusBudgetError as e:
        raise SealError(str(e))
    reasons = []
    src = report.get("census_sources")
    if not isinstance(src, list) or not src:
        verdict = "unsealed"
        reasons.append("report names no census_sources")
    else:
        if sorted(map(str, src)) != fresh["census_sources"]:
            reasons.append("census_sources differ from the census")
        if report.get("snapshot_date") != fresh["snapshot_date"]:
            reasons.append(f"snapshot_date {report.get('snapshot_date')} != census {fresh['snapshot_date']}")
        if report.get("budget") != fresh["budget"]:
            reasons.append("budget differs from the current config")
        verdict = "stale" if reasons else None
    diffs = diff(fresh, report)
    if verdict is None:
        verdict = "tampered" if diffs else "sealed"
        if diffs:
            reasons.append(f"{len(diffs)} field(s) differ from a fresh G206 re-price")
    return {"format": FORMAT, "version": 1, "verdict": verdict, "reasons": reasons,
            "census_sources": fresh["census_sources"], "snapshot_date": fresh["snapshot_date"],
            "diff_count": len(diffs), "diffs": diffs[:MAX_DIFFS]}


def text(r):
    out = [f"harbour seal: {r['verdict']} ({r['diff_count']} differences)"]
    out += [f"  - {x}" for x in r["reasons"]]
    for d in r["diffs"][:20]:
        if d["kind"] == "changed":
            out.append(f"    {d['path']}: expected {json.dumps(d['expected'])}, found {json.dumps(d['found'])}")
        else:
            out.append(f"    {d['path']}: {d['kind']}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Harbour Seals: check a G206 report against its census.")
    ap.add_argument("census")
    ap.add_argument("report")
    ap.add_argument("--config", default=cb.DEFAULT_CONFIG)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on-broken", action="store_true", help="exit 1 unless sealed")
    a = ap.parse_args(argv)
    try:
        r = seal(_load_json(a.census), _load_json(a.report), _load_json(a.config))
    except SealError as e:
        print(f"harbour_seals: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 1 if a.fail_on_broken and r["verdict"] != "sealed" else 0


if __name__ == "__main__":
    sys.exit(main())