# SPDX-License-Identifier: MIT
"""G126 Breakwater Queue (DiskSaver Island, quest q_breakwater_queue).

Save writes from the islands (islands and keys_per_island of G86 Compaction
Shoals, read-only) arrive at the archive harbour in waves: calm ticks bring
a trickle, swells bring bursts, and during the storm season
(`storm_len` ticks from `storm_start`) swells come faster than the crane. The archive crane lands exactly
`drain_per_tick` writes a tick. Writes that cannot be landed yet wait behind
the breakwater, a queue of `capacity` slots; a write arriving at a full
queue is lost to the sea (dropped).

Win: at most `max_dropped` writes lost and no landed write waited more than
`max_wait` ticks. The keeper picks the breakwater capacity. Too small a
breakwater drops every storm swell; too large a one lets the queue grow so
long that writes wait for ages (bufferbloat). Deterministic and offline:
integers only, the shared 32-bit LCG.

Reusable pieces:
  validate(cfg) -> Config
  Breakwater(capacity): offer(write, now) / drain(n, now) -> waits
  arrivals(config) -> per-tick list of arriving save keys
  simulate(config, capacity=None) -> Result
  islands_from_shoals(shoals_cfg)  tie-in: islands + keys_per_island = G86
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple

QUEST_ID = "q_breakwater_queue"
VERSION = 1
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
WON, FAILED = "won", "failed"
FAIL_DROP, FAIL_WAIT = "dropped_exceeded", "wait_exceeded"
NPC_KEYS = ("start", "swell", "crane", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "harbour", "islands", "seed", "npc"}
H_KEYS = {"ticks", "keys_per_island", "drain_per_tick", "calm_max", "swell_permille",
          "swell_size", "storm_start", "storm_len", "storm_swell_permille",
          "capacity", "max_dropped", "max_wait"}


class HarbourError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    ticks: int
    keys_per_island: int
    drain_per_tick: int
    calm_max: int
    swell_permille: int
    swell_size: int
    storm_start: int
    storm_len: int
    storm_swell_permille: int
    capacity: int
    max_dropped: int
    max_wait: int
    islands: Tuple[str, ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise HarbourError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise HarbourError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise HarbourError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise HarbourError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise HarbourError(f"quest must be {QUEST_ID}")
    h = cfg.get("harbour")
    if not isinstance(h, dict) or set(h) != H_KEYS:
        raise HarbourError(f"harbour must have exactly {sorted(H_KEYS)}")
    t = _int(h["ticks"], "ticks", 1, 1_000_000)
    kpi = _int(h["keys_per_island"], "keys_per_island", 1, 100_000)
    dr = _int(h["drain_per_tick"], "drain_per_tick", 1, 10_000)
    cm = _int(h["calm_max"], "calm_max", 0, 10_000)
    sp = _int(h["swell_permille"], "swell_permille", 0, 1000)
    ss = _int(h["swell_size"], "swell_size", 0, 100_000)
    st = _int(h["storm_start"], "storm_start", 0, t)
    sl = _int(h["storm_len"], "storm_len", 0, t - st)
    ssp = _int(h["storm_swell_permille"], "storm_swell_permille", 0, 1000)
    cap = _int(h["capacity"], "capacity", 0, 10_000_000)
    md = _int(h["max_dropped"], "max_dropped", 0, 10_000_000)
    mw = _int(h["max_wait"], "max_wait", 0, 1_000_000)
    isl = cfg.get("islands")
    if not isinstance(isl, list) or not isl:
        raise HarbourError("islands must be a non-empty list")
    seen = []
    for it in isl:
        iid = it.get("id") if isinstance(it, dict) else None
        if not isinstance(iid, str) or not iid or set(iid) - ID_CHARS or iid in seen:
            raise HarbourError(f"bad or duplicate island id: {iid!r}")
        seen.append(iid)
    seed = _int(cfg.get("seed", 1), "seed", 0, 2 ** 32 - 1)
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or not isinstance(npc.get("name"), str):
        raise HarbourError("npc must have a name")
    lines = npc.get("lines")
    if not isinstance(lines, dict) or set(lines) != set(NPC_KEYS):
        raise HarbourError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    if not all(isinstance(v, str) and v for v in lines.values()):
        raise HarbourError("npc lines must be non-empty strings")
    return Config(t, kpi, dr, cm, sp, ss, st, sl, ssp, cap, md, mw, tuple(seen), seed, npc["name"], dict(lines))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self, n: int) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) % n


class Breakwater:
    """Bounded FIFO of (key, arrival tick)."""

    def __init__(self, capacity: int):
        if capacity < 0:
            raise HarbourError("capacity must be >= 0")
        self.capacity = capacity
        self.q: Deque[Tuple[str, int]] = deque()
        self.dropped = 0

    def offer(self, key: str, now: int) -> bool:
        if len(self.q) >= self.capacity:
            self.dropped += 1
            return False
        self.q.append((key, now))
        return True

    def drain(self, n: int, now: int) -> List[int]:
        waits = []
        for _ in range(min(n, len(self.q))):
            _, t = self.q.popleft()
            waits.append(now - t)
        return waits


def keys_for(c: Config) -> List[str]:
    return [f"{i}:{k:04d}" for i in c.islands for k in range(c.keys_per_island)]


def arrivals(c: Config) -> List[List[str]]:
    rng, keys = Lcg(c.seed), keys_for(c)
    out = []
    for t in range(c.ticks):
        n = rng.next(c.calm_max + 1)
        storm = c.storm_start <= t < c.storm_start + c.storm_len
        if rng.next(1000) < (c.storm_swell_permille if storm else c.swell_permille):
            n += c.swell_size
        out.append([keys[rng.next(len(keys))] for _ in range(n)])
    return out


@dataclass
class Result:
    status: str
    reason: Optional[str]
    arrived: int
    landed: int
    dropped: int
    worst_wait: int
    peak_queue: int


def simulate(c: Config, capacity: Optional[int] = None) -> Result:
    cap = c.capacity if capacity is None else capacity
    bw = Breakwater(cap)
    arrived = landed = worst = peak = 0
    for now, wave in enumerate(arrivals(c)):
        for k in wave:
            bw.offer(k, now)
        arrived += len(wave)
        peak = max(peak, len(bw.q))
        waits = bw.drain(c.drain_per_tick, now)
        landed += len(waits)
        if waits:
            worst = max(worst, max(waits))
    if arrived != landed + bw.dropped + len(bw.q):
        raise AssertionError("a write vanished")
    if bw.dropped > c.max_dropped:
        status, reason = FAILED, FAIL_DROP
    elif worst > c.max_wait:
        status, reason = FAILED, FAIL_WAIT
    else:
        status, reason = WON, None
    return Result(status, reason, arrived, landed, bw.dropped, worst, peak)


def islands_from_shoals(shoals_cfg) -> Tuple[List[dict], int]:
    """G86 tie-in: islands and keys_per_island from Compaction Shoals, read-only."""
    return ([{"id": it["id"]} for it in shoals_cfg["islands"]],
            shoals_cfg["shoals"]["keys_per_island"])


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result, cap: int) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason, "capacity": cap,
            "arrived": r.arrived, "landed": r.landed, "dropped": r.dropped,
            "max_dropped": c.max_dropped, "worst_wait": r.worst_wait, "max_wait": c.max_wait,
            "peak_queue": r.peak_queue}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--capacity", type=int, default=None, help="breakwater capacity override")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    cap = c.capacity if a.capacity is None else a.capacity
    r = simulate(c, cap)
    print(npc_say(c, "start"))
    print(json.dumps(receipt(c, r, cap), sort_keys=True))
    print(npc_say(c, "win" if r.status == WON else "fail"))
    return 0 if r.status == WON else 1


if __name__ == "__main__":
    sys.exit(main())
