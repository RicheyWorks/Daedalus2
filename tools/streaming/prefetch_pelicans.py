# SPDX-License-Identifier: MIT
"""G123 Prefetch Pelicans (DiskSaver Island, quest q_prefetch_pelicans).

A traveller walks DiskSaver Island chunk by chunk along the save path (the
islands and keys_per_island of G86 Compaction Shoals, read-only, in order).
Pelicans fly chunks in from the archive: a flight takes `latency` ticks and
at most `flights_per_tick` pelicans can leave each tick. Each tick the
traveller steps onto the next chunk if it has landed, otherwise stalls.
Now and then (seeded, `jump_permille`) the traveller takes a ferry to the
start of a random island; every chunk already flown in
for the old stretch is wasted.

The keeper picks the readahead depth: how many chunks ahead the pelicans
keep in flight or landed. Win: the season ends with at most `max_stalls`
stalled ticks and at most `max_wasted` wasted flights. Too shallow a
readahead stalls on every step; too deep wastes a flock of flights every
ferry. Deterministic and offline: integers only, the shared 32-bit LCG.

Reusable pieces:
  validate(cfg) -> Config
  path_for(config) -> list of chunk ids; island_starts(config)
  Prefetcher(depth, latency, flights_per_tick): tick(now, pos, path) / ready(chunk, now) / drop_except(keep)
  simulate(config, depth=None) -> Result
  islands_from_shoals(shoals_cfg)  tie-in: islands + keys_per_island = G86
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

QUEST_ID = "q_prefetch_pelicans"
VERSION = 1
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
WON, FAILED = "won", "failed"
FAIL_STALL, FAIL_WASTE = "stalls_exceeded", "waste_exceeded"
NPC_KEYS = ("start", "flight", "ferry", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "pelicans", "islands", "seed", "npc"}
P_KEYS = {"ticks", "keys_per_island", "latency", "flights_per_tick", "depth",
          "jump_permille", "max_stalls", "max_wasted"}


class PelicanError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    ticks: int
    keys_per_island: int
    latency: int
    flights_per_tick: int
    depth: int
    jump_permille: int
    max_stalls: int
    max_wasted: int
    islands: Tuple[str, ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise PelicanError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise PelicanError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise PelicanError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise PelicanError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise PelicanError(f"quest must be {QUEST_ID}")
    p = cfg.get("pelicans")
    if not isinstance(p, dict) or set(p) != P_KEYS:
        raise PelicanError(f"pelicans must have exactly {sorted(P_KEYS)}")
    t = _int(p["ticks"], "ticks", 1, 1_000_000)
    kpi = _int(p["keys_per_island"], "keys_per_island", 1, 100_000)
    lat = _int(p["latency"], "latency", 0, 1000)
    fpt = _int(p["flights_per_tick"], "flights_per_tick", 1, 1000)
    d = _int(p["depth"], "depth", 1, 10_000)
    jp = _int(p["jump_permille"], "jump_permille", 0, 1000)
    ms = _int(p["max_stalls"], "max_stalls", 0, 1_000_000)
    mw = _int(p["max_wasted"], "max_wasted", 0, 1_000_000)
    isl = cfg.get("islands")
    if not isinstance(isl, list) or not isl:
        raise PelicanError("islands must be a non-empty list")
    seen = []
    for it in isl:
        iid = it.get("id") if isinstance(it, dict) else None
        if not isinstance(iid, str) or not iid or set(iid) - ID_CHARS or iid in seen:
            raise PelicanError(f"bad or duplicate island id: {iid!r}")
        seen.append(iid)
    seed = _int(cfg.get("seed", 1), "seed", 0, 2 ** 32 - 1)
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or not isinstance(npc.get("name"), str):
        raise PelicanError("npc must have a name")
    lines = npc.get("lines")
    if not isinstance(lines, dict) or set(lines) != set(NPC_KEYS):
        raise PelicanError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    if not all(isinstance(v, str) and v for v in lines.values()):
        raise PelicanError("npc lines must be non-empty strings")
    return Config(t, kpi, lat, fpt, d, jp, ms, mw, tuple(seen), seed, npc["name"], dict(lines))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self, n: int) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) % n


def path_for(c: Config) -> List[str]:
    return [f"{i}:{k:04d}" for i in c.islands for k in range(c.keys_per_island)]


def island_starts(c: Config) -> List[int]:
    return [n * c.keys_per_island for n in range(len(c.islands))]


class Prefetcher:
    """Keeps chunks pos..pos+depth-1 in flight or landed (path wraps around)."""

    def __init__(self, depth: int, latency: int, flights_per_tick: int):
        self.depth, self.latency, self.fpt = depth, latency, flights_per_tick
        self.lands: Dict[int, int] = {}  # path index -> tick it lands
        self.flights = 0

    def tick(self, now: int, pos: int, n: int) -> int:
        sent = 0
        for off in range(self.depth):
            if sent == self.fpt:
                break
            idx = (pos + off) % n
            if idx not in self.lands:
                self.lands[idx] = now + self.latency
                sent += 1
        self.flights += sent
        return sent

    def ready(self, idx: int, now: int) -> bool:
        return idx in self.lands and self.lands[idx] <= now

    def consume(self, idx: int) -> None:
        del self.lands[idx]

    def drop_except(self, keep) -> int:
        """Discard every chunk not in `keep`; returns how many were wasted."""
        gone = [i for i in self.lands if i not in keep]
        for i in gone:
            del self.lands[i]
        return len(gone)


@dataclass
class Result:
    status: str
    reason: Optional[str]
    steps: int
    stalls: int
    wasted: int
    flights: int
    ferries: int


def simulate(c: Config, depth: Optional[int] = None) -> Result:
    d = c.depth if depth is None else depth
    if d < 1:
        raise PelicanError("depth must be >= 1")
    rng, path, starts = Lcg(c.seed), path_for(c), island_starts(c)
    n = len(path)
    pf = Prefetcher(d, c.latency, c.flights_per_tick)
    pos = steps = stalls = wasted = ferries = 0
    for now in range(c.ticks):
        if rng.next(1000) < c.jump_permille:
            pos = starts[rng.next(len(starts))]
            ferries += 1
            wasted += pf.drop_except({(pos + off) % n for off in range(d)})
        pf.tick(now, pos, n)
        if pf.ready(pos, now):
            pf.consume(pos)
            pos = (pos + 1) % n
            steps += 1
        else:
            stalls += 1
    if stalls > c.max_stalls:
        status, reason = FAILED, FAIL_STALL
    elif wasted > c.max_wasted:
        status, reason = FAILED, FAIL_WASTE
    else:
        status, reason = WON, None
    return Result(status, reason, steps, stalls, wasted, pf.flights, ferries)


def islands_from_shoals(shoals_cfg) -> Tuple[List[dict], int]:
    """G86 tie-in: islands and keys_per_island from Compaction Shoals, read-only."""
    return ([{"id": it["id"]} for it in shoals_cfg["islands"]],
            shoals_cfg["shoals"]["keys_per_island"])


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result, depth: int) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason, "depth": depth,
            "steps": r.steps, "stalls": r.stalls, "max_stalls": c.max_stalls,
            "wasted": r.wasted, "max_wasted": c.max_wasted, "flights": r.flights,
            "ferries": r.ferries}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--depth", type=int, default=None, help="readahead depth override")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    d = c.depth if a.depth is None else a.depth
    r = simulate(c, d)
    print(npc_say(c, "start"))
    print(json.dumps(receipt(c, r, d), sort_keys=True))
    print(npc_say(c, "win" if r.status == WON else "fail"))
    return 0 if r.status == WON else 1


if __name__ == "__main__":
    sys.exit(main())
