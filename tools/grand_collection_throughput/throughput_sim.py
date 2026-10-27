#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Grand Collection throughput: measure per-chunk stage seconds from a run's own files, then project hours to a
target under speed-up options. Read-only; it never touches the producer, the editor, leases or Codex's scripts.

  extract  --campaign <GrandCollectionR18> --content <.../NativeDiscovery/20261024> --log <DaedalusRealm.log>
           --from N --to M --out stages.json
  simulate --stages stages.json --saved 2400 --target 10000 [--per-kind 10] [--relaunch-cost 300] [--md out.md]

Stages per chunk (boundaries are file mtimes and editor-log lines, all already written by the run):
  blender    SourceJobs/ChunkN/start.json utc -> terminal.json mtime
  pre        Blender end -> first Interchange import log line (no editor log; the r18 pin/hash/verify phase)
  import     first chunk asset mtime -> level .umap mtime (import, place, save)
  validate   .umap save -> last ContentValidation/AssetCheck line
  post       last validation line -> CatalogChunks/ChunkN.catalog-staging.csv mtime (receipt, catalog export)
  gap        csv -> next chunk's Blender start
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import sys
from pathlib import Path

UTC = dt.timezone.utc
STAGES = ("blender", "pre", "import", "validate", "post", "gap")
LOG_RX = re.compile(r"^\[(\d{4})\.(\d\d)\.(\d\d)-(\d\d)\.(\d\d)\.(\d\d):(\d{3})\]\[\s*\d+\](\w+): ?(.*)")
LOG_CATS = {"LogInterchangeImport", "LogContentValidation", "AssetCheck"}


def _mt(p) -> dt.datetime:
    return dt.datetime.fromtimestamp(os.path.getmtime(p), UTC)


def _iso(s: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def read_log(path) -> list[tuple[dt.datetime, str]]:
    ev = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = LOG_RX.match(line)
            if m and m.group(8) in LOG_CATS:
                ev.append((dt.datetime(*map(int, m.groups()[:6]), int(m.group(7)) * 1000, tzinfo=UTC), m.group(8)))
    return ev


def extract(campaign: Path, content: Path, events, lo: int, hi: int) -> list[dict]:
    rows = []
    for n in range(lo, hi + 1):
        try:
            sj = campaign / "SourceJobs" / f"Chunk{n:04d}"
            bs = _iso(json.loads((sj / "start.json").read_text(encoding="utf-8-sig"))["utc"])
            be = _mt(sj / "terminal.json")
            files = [Path(r) / x for r, _, fs in os.walk(content / f"R18_C{n:04d}") for x in fs]
            umap = next(f for f in files if f.suffix == ".umap")
            first, save = min(_mt(f) for f in files), _mt(umap)
            csv = _mt(campaign / "CatalogChunks" / f"Chunk{n:04d}.catalog-staging.csv")
        except (OSError, StopIteration, KeyError, ValueError):
            continue
        nxt = campaign / "SourceJobs" / f"Chunk{n + 1:04d}" / "start.json"
        w = [e for e in events if be <= e[0] <= csv]
        imp = [t for t, c in w if c == "LogInterchangeImport"]
        val = [t for t, c in w if c != "LogInterchangeImport" and t >= save]
        s = lambda a, b: round((b - a).total_seconds(), 1)
        row = {"chunk": n, "blender": s(bs, be), "pre": s(be, imp[0]) if imp else None, "import": s(first, save),
               "validate": s(save, val[-1]) if val else None, "post": s(val[-1], csv) if val else None,
               "gap": s(csv, _iso(json.loads(nxt.read_text(encoding="utf-8-sig"))["utc"])) if nxt.exists() else None,
               "total": s(bs, csv)}
        rows.append(row)
    return rows


# ---------------- model ----------------

def sessions(rows: list[dict]) -> list[list[dict]]:
    """Split where the producer restarted (a gap over 10 minutes between chunks)."""
    out, cur = [], []
    for r in rows:
        cur.append(r)
        if r.get("gap") is not None and r["gap"] > 600:
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def fit(xs, ys):
    n = len(xs)
    if n < 2:
        return (ys[0] if ys else 0.0), 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    vx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / vx if vx else 0.0
    return my - b * mx, b


def model(rows: list[dict]) -> dict:
    """Per stage: start (s at chunk 0 of a session) and drift (s added per chunk within a session), from the
    latest session that has every stage measured."""
    ss = [s for s in sessions(rows) if all(r.get(k) is not None for r in s for k in STAGES[:-1])]
    if not ss:
        raise ValueError("no session with all stages measured")
    s = ss[-1]
    m = {}
    for k in STAGES:
        xs = [i for i, r in enumerate(s) if r.get(k) is not None and not (k == "gap" and r[k] > 600)]
        ys = [s[i][k] for i in xs]
        a, b = fit(xs, ys) if ys else (0.0, 0.0)
        m[k] = {"start": round(max(a, 0.0), 1), "drift": round(b, 3), "mean": round(sum(ys) / len(ys), 1) if ys else 0.0}
    m["_session"] = {"first": s[0]["chunk"], "last": s[-1]["chunk"], "n": len(s)}
    return m


# Option knobs. "scale" multiplies a stage's start, "drift" multiplies its drift; per_item marks stages whose
# cost scales with items per chunk (doubling chunk size doubles them; fixed costs are paid once per chunk).
PER_ITEM = {"blender": 0.9, "pre": 0.3, "import": 0.9, "validate": 0.9, "post": 0.2, "gap": 0.0}
OPTIONS = {
    "baseline (no relaunch)": {},
    "baseline + relaunch each 24 h window": {"relaunch_every_h": 24},
    "A pipeline Blender one chunk ahead": {"pipeline_blender": True, "relaunch_every_h": 24},
    "B incremental pins + hash (prev chunk only, full every 25th)": {"pre": (0.25, 0.0), "relaunch_every_h": 24},
    "C validate only the 20 new items once": {"validate": (0.5, 0.0), "relaunch_every_h": 24},
    "D incremental catalog export": {"post": (0.3, 0.0), "relaunch_every_h": 24},
    "E chunk size 20 per kind": {"per_kind": 20, "relaunch_every_h": 24},
    "F relaunch editor at the best interval": {"relaunch_best": True},
    "A+B+C+D": {"pipeline_blender": True, "pre": (0.25, 0.0), "validate": (0.5, 0.0), "post": (0.3, 0.0), "relaunch_every_h": 24},
    "A+B+C+D+E": {"pipeline_blender": True, "pre": (0.25, 0.0), "validate": (0.5, 0.0), "post": (0.3, 0.0), "per_kind": 20, "relaunch_every_h": 24},
}


def chunk_seconds(m: dict, k: int, opt: dict, base_kind: int) -> float:
    ratio = opt.get("per_kind", base_kind) / base_kind
    t = {}
    for st in STAGES:
        sc, dr = opt.get(st, (1.0, 1.0))
        start = m[st]["start"] * sc
        start = start * (PER_ITEM[st] * ratio + (1 - PER_ITEM[st]))
        t[st] = max(start + m[st]["drift"] * dr * k * ratio, 0.0)
    if opt.get("pipeline_blender"):
        rest = sum(v for s, v in t.items() if s != "blender")
        return max(rest, t["blender"])   # Blender for n+1 overlaps native n
    return sum(t.values())


def project(m: dict, saved: int, target: int, per_kind: int, opt: dict, relaunch_cost: float = 300.0,
            interval: int | None = None) -> dict:
    kind = opt.get("per_kind", per_kind)
    chunks = math.ceil(max(target - saved, 0) / kind)
    every_h = opt.get("relaunch_every_h")
    total, k, relaunches = 0.0, 0, 0
    since = 0.0
    for _ in range(chunks):
        if interval and k >= interval:
            total += relaunch_cost; relaunches += 1; k = 0
        elif every_h and since >= every_h * 3600:
            total += relaunch_cost; relaunches += 1; k = 0; since = 0.0
        c = chunk_seconds(m, k, opt, per_kind)
        total += c; since += c; k += 1
    return {"chunks": chunks, "hours": round(total / 3600, 1), "relaunches": relaunches,
            "first_chunk_min": round(chunk_seconds(m, 0, opt, per_kind) / 60, 2)}


def best_interval(m, saved, target, per_kind, opt, relaunch_cost):
    best = None
    for n in (10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 150, 200):
        r = project(m, saved, target, per_kind, opt, relaunch_cost, interval=n)
        if best is None or r["hours"] < best[1]["hours"]:
            best = (n, r)
    return best


def simulate(rows, saved, target, per_kind=10, relaunch_cost=300.0) -> list[dict]:
    m = model(rows)
    out = []
    for name, opt in OPTIONS.items():
        if opt.get("relaunch_best"):
            n, r = best_interval(m, saved, target, per_kind, opt, relaunch_cost)
            r["relaunch_every_chunks"] = n
        else:
            r = project(m, saved, target, per_kind, opt, relaunch_cost)
        out.append({"option": name, **r})
    return out


def to_md(m, res, saved, target) -> str:
    s = m["_session"]
    L = [f"Model from chunks {s['first']}-{s['last']} ({s['n']} chunks, one editor session).", "",
         "| stage | s at session start | drift s/chunk | mean s |", "|---|---|---|---|"]
    for k in STAGES:
        L.append(f"| {k} | {m[k]['start']} | {m[k]['drift']} | {m[k]['mean']} |")
    L += ["", f"Projection from {saved} saved per kind to {target}:", "",
          "| option | chunks | hours | first chunk min | relaunches |", "|---|---|---|---|---|"]
    for r in res:
        extra = f" (every {r['relaunch_every_chunks']} chunks)" if "relaunch_every_chunks" in r else ""
        L.append(f"| {r['option']} | {r['chunks']} | {r['hours']} | {r['first_chunk_min']} | {r['relaunches']}{extra} |")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("--campaign", required=True, type=Path)
    e.add_argument("--content", required=True, type=Path)
    e.add_argument("--log", required=True, type=Path)
    e.add_argument("--from", dest="lo", type=int, required=True)
    e.add_argument("--to", dest="hi", type=int, required=True)
    e.add_argument("--out", required=True, type=Path)
    s = sub.add_parser("simulate")
    s.add_argument("--stages", required=True, type=Path)
    s.add_argument("--saved", type=int, required=True)
    s.add_argument("--target", type=int, default=10000)
    s.add_argument("--per-kind", type=int, default=10)
    s.add_argument("--relaunch-cost", type=float, default=300.0)
    s.add_argument("--md", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "extract":
        rows = extract(a.campaign, a.content, read_log(a.log), a.lo, a.hi)
        a.out.write_text(json.dumps({"schema": "daedalus.gc-stage-times.v1", "rows": rows}, indent=1), encoding="utf-8")
        print(f"{len(rows)} chunks -> {a.out}")
        return 0 if rows else 1
    rows = json.loads(a.stages.read_text(encoding="utf-8"))["rows"]
    m = model(rows)
    res = simulate(rows, a.saved, a.target, a.per_kind, a.relaunch_cost)
    md = to_md(m, res, a.saved, a.target)
    if a.md:
        a.md.write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
