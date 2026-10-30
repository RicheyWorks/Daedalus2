# SPDX-License-Identifier: MIT
"""Budget Trend Ledger (G517, disk-saver): run-over-run drift of the streaming budget.

Each World Census run is priced by G206 census_budget.py (40000 KiB RAM / 32768 KiB
disk, amber at 900 permille) and appended as ONE record to a JSON-lines ledger.
The ledger then reports drift between runs:

  * per-world RAM and disk deltas,
  * island beacon colour changes (green < amber < red),
  * worlds newly over budget (a red island, or no longer fitting all-resident),
  * worlds that appeared or dropped out,
  * a growing / shrinking / flat RAM trend per world over the last N runs.

Read-only over census.json and the G206 report; stdlib only, integers only,
deterministic bytes. No clock: a record's time is whatever --at passes in.

  python tools/streaming/budget_ledger.py record INPUT.json --ledger L.jsonl --run ID [--at WHEN]
  python tools/streaming/budget_ledger.py diff  --ledger L.jsonl [--from ID] [--to ID] [--json] [--fail-on-worse]
  python tools/streaming/budget_ledger.py trend --ledger L.jsonl [--last N] [--json] [--fail-on-worse]

INPUT is a census.json or an already-made G206 report (format daedalus-census-budget).
Exit 0 = ok, 1 = --fail-on-worse and the budget got worse, 2 = refusal.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-budget-ledger"
RANK = {"green": 0, "amber": 1, "red": 2}
WORSE = ("beacon_worse", "newly_over", "appeared_hot")
MAX_BYTES = 16 * 1024 * 1024


class LedgerError(ValueError):
    pass


def _int(v, what):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise LedgerError(f"{what}: expected a nonnegative integer")
    return v


def to_report(doc, cfg):
    """census.json -> G206 report; a G206 report passes through."""
    if isinstance(doc, dict) and doc.get("format") == cb.FORMAT:
        return doc
    try:
        return cb.plan(doc, cfg)
    except cb.CensusBudgetError as e:
        raise LedgerError(f"census: {e}")


def make_record(report, run, at=None):
    if not isinstance(run, str) or not run.strip():
        raise LedgerError("run id must be a nonempty string")
    if at is not None and not isinstance(at, str):
        raise LedgerError("at must be a string")
    if not isinstance(report, dict) or report.get("format") != cb.FORMAT or report.get("version") != 1:
        raise LedgerError("input must be a census.json or a daedalus-census-budget v1 report")
    budget = report.get("budget") or {}
    worlds = {}
    for w in report.get("worlds") or []:
        wid = w.get("id") if isinstance(w, dict) else None
        if not isinstance(wid, str) or not wid.strip() or wid in worlds:
            raise LedgerError("bad or duplicate world id")
        beacons = {}
        for i in w.get("islands") or []:
            s = _int(i.get("slot"), f"world {wid} slot")
            if i.get("beacon") not in RANK or str(s) in beacons:
                raise LedgerError(f"world {wid} slot {s}: bad beacon or duplicate slot")
            beacons[str(s)] = i["beacon"]
        fits = w.get("fits_all_resident")
        if not isinstance(fits, bool):
            raise LedgerError(f"world {wid} fits_all_resident must be true/false")
        worlds[wid] = {"ram_kib": _int(w.get("total_ram_kib"), f"world {wid} ram"),
                       "disk_kib": _int(w.get("total_disk_kib"), f"world {wid} disk"),
                       "fits_all_resident": fits, "beacons": beacons,
                       "over": (not fits) or "red" in beacons.values()}
    return {"format": FORMAT, "version": 1, "run": run, "at": at,
            "budget": {k: budget.get(k) for k in ("ram_budget_kib", "disk_budget_kib", "warn_permille")},
            "worlds": worlds}


def dumps_line(rec):
    return json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n"


def read_ledger(path):
    if not os.path.exists(path):
        return []
    if os.path.getsize(path) > MAX_BYTES:
        raise LedgerError(f"{path}: ledger too large")
    out, seen = [], set()
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                raise LedgerError(f"{path}:{n}: not JSON")
            if not isinstance(rec, dict) or rec.get("format") != FORMAT or not isinstance(rec.get("worlds"), dict):
                raise LedgerError(f"{path}:{n}: not a {FORMAT} record")
            if rec.get("run") in seen:
                raise LedgerError(f"{path}:{n}: duplicate run {rec.get('run')}")
            seen.add(rec.get("run"))
            out.append(rec)
    return out


def append(path, rec):
    recs = read_ledger(path)
    if any(r["run"] == rec["run"] for r in recs):
        raise LedgerError(f"run {rec['run']} already in ledger")
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(dumps_line(rec))
    return len(recs) + 1


def diff(a, b):
    """Drift from record a to record b; findings sorted, deterministic."""
    wa, wb = a["worlds"], b["worlds"]
    worlds, findings = [], []
    for wid in sorted(set(wa) | set(wb)):
        if wid not in wa:
            w = wb[wid]
            kind = "appeared_hot" if w["over"] or "amber" in w["beacons"].values() else "appeared"
            findings.append({"world": wid, "kind": kind})
            continue
        if wid not in wb:
            findings.append({"world": wid, "kind": "dropped"})
            continue
        x, y = wa[wid], wb[wid]
        worlds.append({"world": wid, "ram_delta_kib": y["ram_kib"] - x["ram_kib"],
                       "disk_delta_kib": y["disk_kib"] - x["disk_kib"]})
        if y["over"] and not x["over"]:
            findings.append({"world": wid, "kind": "newly_over"})
        if x["over"] and not y["over"]:
            findings.append({"world": wid, "kind": "back_under"})
        for s in sorted(set(x["beacons"]) | set(y["beacons"]), key=int):
            p, q = x["beacons"].get(s), y["beacons"].get(s)
            if p and q and p != q:
                findings.append({"world": wid, "slot": int(s), "before": p, "after": q,
                                 "kind": "beacon_worse" if RANK[q] > RANK[p] else "beacon_better"})
    worse = any(f["kind"] in WORSE for f in findings)
    return {"format": FORMAT + "-diff", "version": 1, "from": a["run"], "to": b["run"],
            "worlds": worlds, "findings": findings, "verdict": "worse" if worse else "steady"}


def trend(recs, last=5):
    if last < 2:
        raise LedgerError("--last must be at least 2")
    if not recs:
        raise LedgerError("ledger is empty")
    window = recs[-last:]
    out = []
    for wid in sorted({w for r in window for w in r["worlds"]}):
        ram = [r["worlds"][wid]["ram_kib"] for r in window if wid in r["worlds"]]
        d = ram[-1] - ram[0]
        out.append({"world": wid, "runs": len(ram), "ram_kib": ram, "net_kib": d,
                    "trend": "growing" if d > 0 else "shrinking" if d < 0 else "flat"})
    kinds = {w["trend"] for w in out}
    tally = "rising" if "growing" in kinds else "ebbing" if "shrinking" in kinds else "steady"
    return {"format": FORMAT + "-trend", "version": 1, "runs": [r["run"] for r in window],
            "worlds": out, "tally": tally}


def _pick(recs, run, default):
    if not recs:
        raise LedgerError("ledger is empty")
    if run is None:
        return recs[default]
    for r in recs:
        if r["run"] == run:
            return r
    raise LedgerError(f"run {run} not in ledger")


def text_diff(d):
    lines = [f"ledger diff {d['from']} -> {d['to']}: {d['verdict']}"]
    for w in d["worlds"]:
        lines.append(f"  {w['world']}: ram {w['ram_delta_kib']:+d} KiB, disk {w['disk_delta_kib']:+d} KiB")
    for f in d["findings"]:
        extra = f" slot {f['slot']} {f['before']} -> {f['after']}" if "slot" in f else ""
        lines.append(f"  ! {f['world']}: {f['kind']}{extra}")
    return "\n".join(lines) + "\n"


def text_trend(t):
    lines = [f"ledger trend over {len(t['runs'])} runs: {t['tally']}"]
    for w in t["worlds"]:
        lines.append(f"  {w['world']}: {w['trend']} ({w['net_kib']:+d} KiB over {w['runs']} runs)")
    return "\n".join(lines) + "\n"


def _load_json(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            raise LedgerError(f"{path}: too large")
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise LedgerError(f"{path}: {e.strerror}")
    except ValueError:
        raise LedgerError(f"{path}: not JSON")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Budget Trend Ledger: run-over-run streaming budget drift.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("input")
    r.add_argument("--ledger", required=True)
    r.add_argument("--run", required=True)
    r.add_argument("--at")
    r.add_argument("--config", default=cb.DEFAULT_CONFIG)
    for name in ("diff", "trend"):
        p = sub.add_parser(name)
        p.add_argument("--ledger", required=True)
        p.add_argument("--json", action="store_true")
        p.add_argument("--fail-on-worse", action="store_true")
        if name == "diff":
            p.add_argument("--from", dest="frm")
            p.add_argument("--to")
        else:
            p.add_argument("--last", type=int, default=5)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "record":
            rec = make_record(to_report(_load_json(a.input), _load_json(a.config)), a.run, a.at)
            n = append(a.ledger, rec)
            print(f"recorded run {a.run} ({len(rec['worlds'])} worlds); ledger has {n} runs")
            return 0
        recs = read_ledger(a.ledger)
        if a.cmd == "diff":
            if len(recs) < 2 and (a.frm is None or a.to is None):
                raise LedgerError("diff needs at least two runs")
            out = diff(_pick(recs, a.frm, -2), _pick(recs, a.to, -1))
            bad = out["verdict"] == "worse"
            txt = text_diff(out)
        else:
            out = trend(recs, a.last)
            bad = out["tally"] == "rising"
            txt = text_trend(out)
    except LedgerError as e:
        print(f"budget_ledger: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(out, indent=2, sort_keys=True) + "\n" if a.json else txt)
    return 1 if a.fail_on_worse and bad else 0


if __name__ == "__main__":
    sys.exit(main())
