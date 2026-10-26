# SPDX-License-Identifier: MIT
"""G110 Quorum Quays (DiskSaver Island, quest q_quorum_quays).

Every save (islands and keys_per_island from G86 Compaction Shoals,
read-only) is kept on `replicas` quays. Storms close quays: each tick up to
`max_down` of the quays are cut off by the surf. A write must reach W open
quays to count (each copy carries a version number); a read asks R open quays
and trusts the highest version it hears. An operation that cannot find
enough open quays fails (the dock is unavailable for it).

Win: no read ever returns an older version than the last counted write
(no stale reads), and at least `min_available_permille` of operations
succeed. Quorums with R + W > replicas that still fit around the storms win.
R = W = 1 is quick but serves stale saves; R = W = replicas is never stale
but stalls whenever a single quay is closed. Deterministic and offline:
integers only, the shared 32-bit LCG.

Reusable pieces:
  validate(cfg) -> Config
  QuayCluster(replicas): write(key, version, open_quays, w) / read(key, open_quays, r)
  overlapping(r, w, n) -> bool   (R + W > N)
  simulate(config, r=None, w=None) -> Result
  best_quorums(config) -> list of winning (r, w)
  islands_from_shoals(shoals_cfg)  tie-in: islands + keys_per_island = G86
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

QUEST_ID = "q_quorum_quays"
VERSION = 1
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
WON, FAILED = "won", "failed"
FAIL_STALE, FAIL_AVAIL = "stale_read", "unavailable"
NPC_KEYS = ("start", "storm", "read", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "quays", "islands", "seed", "npc"}
Q_KEYS = {"ticks", "keys_per_island", "replicas", "read_quorum", "write_quorum",
          "max_down", "write_permille", "min_available_permille"}


class QuayError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    ticks: int
    keys_per_island: int
    replicas: int
    read_quorum: int
    write_quorum: int
    max_down: int
    write_permille: int
    min_available_permille: int
    islands: Tuple[str, ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise QuayError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise QuayError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise QuayError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise QuayError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise QuayError(f"quest must be {QUEST_ID}")
    q = cfg.get("quays")
    if not isinstance(q, dict) or set(q) != Q_KEYS:
        raise QuayError(f"quays must have exactly {sorted(Q_KEYS)}")
    t = _int(q["ticks"], "ticks", 1, 1_000_000)
    kpi = _int(q["keys_per_island"], "keys_per_island", 1, 100_000)
    n = _int(q["replicas"], "replicas", 1, 15)
    r = _int(q["read_quorum"], "read_quorum", 1, n)
    w = _int(q["write_quorum"], "write_quorum", 1, n)
    md = _int(q["max_down"], "max_down", 0, n)
    wp = _int(q["write_permille"], "write_permille", 0, 1000)
    ma = _int(q["min_available_permille"], "min_available_permille", 0, 1000)
    isl = cfg.get("islands")
    if not isinstance(isl, list) or not isl:
        raise QuayError("islands must be a non-empty list")
    seen = []
    for it in isl:
        iid = it.get("id") if isinstance(it, dict) else None
        if not isinstance(iid, str) or not iid or set(iid) - ID_CHARS or iid in seen:
            raise QuayError(f"bad or duplicate island id: {iid!r}")
        seen.append(iid)
    seed = _int(cfg.get("seed", 1), "seed", 0, 2 ** 32 - 1)
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or not isinstance(npc.get("name"), str):
        raise QuayError("npc must have a name")
    lines = npc.get("lines")
    if not isinstance(lines, dict) or set(lines) != set(NPC_KEYS):
        raise QuayError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    if not all(isinstance(v, str) and v for v in lines.values()):
        raise QuayError("npc lines must be non-empty strings")
    return Config(t, kpi, n, r, w, md, wp, ma, tuple(seen), seed, npc["name"], dict(lines))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self, n: int) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) % n


def overlapping(r: int, w: int, n: int) -> bool:
    return r + w > n


class QuayCluster:
    """`replicas` quays, each a dict key -> version."""

    def __init__(self, replicas: int):
        self.quays: List[Dict[str, int]] = [dict() for _ in range(replicas)]

    def write(self, key: str, version: int, open_quays: List[int], w: int) -> bool:
        if len(open_quays) < w:
            return False
        for q in open_quays[:w]:
            self.quays[q][key] = version
        return True

    def read(self, key: str, open_quays: List[int], r: int) -> Optional[int]:
        if len(open_quays) < r:
            return None
        return max(self.quays[q].get(key, 0) for q in open_quays[:r])


def keys_for(c: Config) -> List[str]:
    return [f"{i}:{k:04d}" for i in c.islands for k in range(c.keys_per_island)]


@dataclass
class Result:
    status: str
    reason: Optional[str]
    ops: int
    ok_ops: int
    stale_reads: int
    available_permille: int


def simulate(c: Config, r: Optional[int] = None, w: Optional[int] = None) -> Result:
    r = c.read_quorum if r is None else r
    w = c.write_quorum if w is None else w
    if not (1 <= r <= c.replicas and 1 <= w <= c.replicas):
        raise QuayError("quorums must be in 1..replicas")
    rng, keys = Lcg(c.seed), keys_for(c)
    cluster = QuayCluster(c.replicas)
    latest = {k: 0 for k in keys}
    ok = stale = 0
    for _ in range(c.ticks):
        down = set()
        for _ in range(rng.next(c.max_down + 1)):
            down.add(rng.next(c.replicas))
        open_q = [q for q in range(c.replicas) if q not in down]
        start = rng.next(c.replicas)  # coordinator picks a rotating subset
        open_q = sorted(open_q, key=lambda q: (q - start) % c.replicas)
        k = keys[rng.next(len(keys))]
        if rng.next(1000) < c.write_permille:
            if cluster.write(k, latest[k] + 1, open_q, w):
                latest[k] += 1
                ok += 1
        else:
            got = cluster.read(k, open_q, r)
            if got is not None:
                ok += 1
                if got < latest[k]:
                    stale += 1
    avail = ok * 1000 // c.ticks
    if stale:
        status, reason = FAILED, FAIL_STALE
    elif avail < c.min_available_permille:
        status, reason = FAILED, FAIL_AVAIL
    else:
        status, reason = WON, None
    return Result(status, reason, c.ticks, ok, stale, avail)


def best_quorums(c: Config) -> List[Tuple[int, int]]:
    return [(r, w) for r in range(1, c.replicas + 1) for w in range(1, c.replicas + 1)
            if simulate(c, r, w).status == WON]


def islands_from_shoals(shoals_cfg) -> Tuple[List[dict], int]:
    """G86 tie-in: islands and keys_per_island from Compaction Shoals, read-only."""
    return ([{"id": it["id"]} for it in shoals_cfg["islands"]],
            shoals_cfg["shoals"]["keys_per_island"])


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, res: Result, r: int, w: int) -> dict:
    return {"quest": QUEST_ID, "status": res.status, "reason": res.reason, "r": r, "w": w,
            "replicas": c.replicas, "ops": res.ops, "ok_ops": res.ok_ops,
            "stale_reads": res.stale_reads, "available_permille": res.available_permille,
            "min_available_permille": c.min_available_permille}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--r", type=int, default=None, help="read quorum")
    ap.add_argument("--w", type=int, default=None, help="write quorum")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    r = c.read_quorum if a.r is None else a.r
    w = c.write_quorum if a.w is None else a.w
    res = simulate(c, r, w)
    print(npc_say(c, "start"))
    print(json.dumps(receipt(c, res, r, w), sort_keys=True))
    print(npc_say(c, "win" if res.status == WON else "fail"))
    return 0 if res.status == WON else 1


if __name__ == "__main__":
    sys.exit(main())
