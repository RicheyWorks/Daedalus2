# SPDX-License-Identifier: MIT
"""G105 Hash Ring Atolls (DiskSaver Island, quest q_hash_ring_atolls).

The archive atolls stand on a ring of tide markers. Every save (islands and
keys_per_island from G86 Compaction Shoals, read-only) belongs to the first
atoll marker clockwise from the save's hash. Through the season atolls rise
and sink (seeded join and leave events). After each event the saves whose
owner changed must be ferried to their new atoll.

Each event may ferry at most `max_moved_permille` of all saves, and after
each event no atoll may hold more than `load_cap_permille` of the average
load. Win: every event stays within both limits, and every save is found on
exactly the atoll the ring names (checked after every event).

Consistent hashing with enough virtual markers per atoll wins. Mod-N
re-sharding ferries almost every save on each event; a ring with one marker
per atoll leaves some atolls badly overloaded. Deterministic and offline:
integers only, the shared 32-bit LCG, zlib.crc32 + fmix32.

Reusable pieces:
  validate(cfg) -> Config
  HashRing(atolls, vnodes): owner(key) / add / remove
  ModN(atolls): owner(key)  (the trap)
  plan_events(config) -> list of ("join"|"leave", atoll)
  simulate(config, vnodes=None, mod_n=False) -> Result
  islands_from_shoals(shoals_cfg)  tie-in: islands + keys_per_island = G86
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import bisect
import json
import sys
import zlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

QUEST_ID = "q_hash_ring_atolls"
VERSION = 1
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
WON, FAILED = "won", "failed"
FAIL_MOVED, FAIL_LOAD = "moved_exceeded", "load_exceeded"
NPC_KEYS = ("start", "rise", "sink", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "ring", "islands", "atolls", "seed", "npc"}
RING_KEYS = {"events", "keys_per_island", "start_atolls", "vnodes",
             "max_moved_permille", "load_cap_permille"}
MIN_ATOLLS = 4


class RingError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    events: int
    keys_per_island: int
    start_atolls: int
    vnodes: int
    max_moved_permille: int
    load_cap_permille: int
    islands: Tuple[str, ...]
    atolls: Tuple[str, ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise RingError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def _ids(lst, name):
    if not isinstance(lst, list) or not lst:
        raise RingError(f"{name} must be a non-empty list")
    seen = []
    for it in lst:
        iid = it.get("id") if isinstance(it, dict) else None
        if not isinstance(iid, str) or not iid or set(iid) - ID_CHARS or iid in seen:
            raise RingError(f"bad or duplicate {name} id: {iid!r}")
        seen.append(iid)
    return tuple(seen)


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise RingError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise RingError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise RingError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise RingError(f"quest must be {QUEST_ID}")
    r = cfg.get("ring")
    if not isinstance(r, dict) or set(r) != RING_KEYS:
        raise RingError(f"ring must have exactly {sorted(RING_KEYS)}")
    islands = _ids(cfg.get("islands"), "island")
    atolls = _ids(cfg.get("atolls"), "atoll")
    ev = _int(r["events"], "events", 1, 10_000)
    kpi = _int(r["keys_per_island"], "keys_per_island", 1, 100_000)
    sa = _int(r["start_atolls"], "start_atolls", MIN_ATOLLS, len(atolls))
    if sa == len(atolls):
        raise RingError("start_atolls must leave at least one atoll to rise")
    vn = _int(r["vnodes"], "vnodes", 1, 1024)
    mm = _int(r["max_moved_permille"], "max_moved_permille", 0, 1000)
    lc = _int(r["load_cap_permille"], "load_cap_permille", 1000, 100_000)
    seed = _int(cfg.get("seed", 1), "seed", 0, 2 ** 32 - 1)
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or not isinstance(npc.get("name"), str):
        raise RingError("npc must have a name")
    lines = npc.get("lines")
    if not isinstance(lines, dict) or set(lines) != set(NPC_KEYS):
        raise RingError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    if not all(isinstance(v, str) and v for v in lines.values()):
        raise RingError("npc lines must be non-empty strings")
    return Config(ev, kpi, sa, vn, mm, lc, islands, atolls, seed, npc["name"], dict(lines))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self, n: int) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) % n


def h32(s: str) -> int:
    """zlib.crc32 followed by the murmur3 fmix32 finalizer (crc32 alone is linear)."""
    h = zlib.crc32(s.encode()) & 0xFFFFFFFF
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    return h ^ (h >> 16)


class HashRing:
    """Consistent hash ring; each atoll owns `vnodes` markers."""

    def __init__(self, atolls, vnodes: int):
        if vnodes < 1:
            raise RingError("vnodes must be >= 1")
        self.vnodes = vnodes
        self.points: List[Tuple[int, str]] = []
        for a in atolls:
            self.add(a)

    def add(self, atoll: str) -> None:
        for v in range(self.vnodes):
            bisect.insort(self.points, (h32(f"{atoll}#{v}"), atoll))

    def remove(self, atoll: str) -> None:
        self.points = [p for p in self.points if p[1] != atoll]

    def owner(self, key: str) -> str:
        if not self.points:
            raise RingError("ring is empty")
        i = bisect.bisect_left(self.points, (h32(key), ""))
        return self.points[i % len(self.points)][1]


class ModN:
    """The trap: owner = sorted_atolls[hash mod N]."""

    def __init__(self, atolls, vnodes: int = 1):
        self.atolls = sorted(atolls)

    def add(self, atoll: str) -> None:
        self.atolls = sorted(self.atolls + [atoll])

    def remove(self, atoll: str) -> None:
        self.atolls = [a for a in self.atolls if a != atoll]

    def owner(self, key: str) -> str:
        return self.atolls[h32(key) % len(self.atolls)]


def keys_for(c: Config) -> List[str]:
    return [f"{i}:{k:04d}" for i in c.islands for k in range(c.keys_per_island)]


def plan_events(c: Config) -> List[Tuple[str, str]]:
    rng = Lcg(c.seed)
    live = list(c.atolls[:c.start_atolls])
    sunk = list(c.atolls[c.start_atolls:])
    out = []
    for _ in range(c.events):
        rise = not live[MIN_ATOLLS:] or (sunk and rng.next(2) == 0)
        if rise:
            a = sunk.pop(rng.next(len(sunk)))
            live.append(a)
            out.append(("join", a))
        else:
            a = live.pop(rng.next(len(live)))
            sunk.append(a)
            out.append(("leave", a))
    return out


@dataclass
class Result:
    status: str
    reason: Optional[str]
    events_ok: int
    worst_moved: int
    total_moved: int
    worst_load_permille: int


def simulate(c: Config, vnodes: Optional[int] = None, mod_n: bool = False) -> Result:
    vn = c.vnodes if vnodes is None else vnodes
    keys = keys_for(c)
    ring = (ModN if mod_n else HashRing)(c.atolls[:c.start_atolls], vn)
    live = set(c.atolls[:c.start_atolls])
    where = {k: ring.owner(k) for k in keys}  # where each save is stored
    limit = c.max_moved_permille * len(keys) // 1000
    ok = worst_m = total = worst_l = 0
    reason = None
    for kind, a in plan_events(c):
        if kind == "join":
            ring.add(a)
            live.add(a)
        else:
            ring.remove(a)
            live.discard(a)
        moved = 0
        for k in keys:
            o = ring.owner(k)
            if o != where[k]:
                where[k] = o
                moved += 1
        if any(where[k] != ring.owner(k) or where[k] not in live for k in keys):
            raise AssertionError("a save is not on the atoll the ring names")
        load: Dict[str, int] = {x: 0 for x in live}
        for k in keys:
            load[where[k]] += 1
        lp = max(load.values()) * len(live) * 1000 // len(keys)
        worst_m, total, worst_l = max(worst_m, moved), total + moved, max(worst_l, lp)
        if moved > limit:
            reason = reason or FAIL_MOVED
        elif lp > c.load_cap_permille:
            reason = reason or FAIL_LOAD
        else:
            ok += 1
    status = WON if ok == c.events else FAILED
    return Result(status, None if status == WON else reason, ok, worst_m, total, worst_l)


def islands_from_shoals(shoals_cfg) -> Tuple[List[dict], int]:
    """G86 tie-in: islands and keys_per_island from Compaction Shoals, read-only."""
    return ([{"id": it["id"]} for it in shoals_cfg["islands"]],
            shoals_cfg["shoals"]["keys_per_island"])


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result, vnodes: int, mod_n: bool) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason,
            "scheme": "mod_n" if mod_n else f"ring_v{vnodes}",
            "events_ok": r.events_ok, "events": c.events, "worst_moved": r.worst_moved,
            "max_moved": c.max_moved_permille * len(keys_for(c)) // 1000,
            "total_moved": r.total_moved, "worst_load_permille": r.worst_load_permille,
            "load_cap_permille": c.load_cap_permille}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--vnodes", type=int, default=None, help="override markers per atoll")
    ap.add_argument("--mod-n", action="store_true", help="re-shard by hash mod N (trap)")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    vn = c.vnodes if a.vnodes is None else a.vnodes
    r = simulate(c, vn, a.mod_n)
    print(npc_say(c, "start"))
    print(json.dumps(receipt(c, r, vn, a.mod_n), sort_keys=True))
    print(npc_say(c, "win" if r.status == WON else "fail"))
    return 0 if r.status == WON else 1


if __name__ == "__main__":
    sys.exit(main())
