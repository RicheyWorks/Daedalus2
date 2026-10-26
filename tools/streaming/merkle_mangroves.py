# SPDX-License-Identifier: MIT
"""G90 Merkle Mangroves (DiskSaver Island, quest q_merkle_mangroves).

Every island save lives twice: on the shore replica and in the mangrove
replica. Storms flip saves in the mangroves each window. At the end of a
window the warden runs anti-entropy: both sides build a Merkle tree (binary,
`depth` levels, keys bucketed by CRC32) and compare hashes. Matching subtrees
are skipped, differing subtrees are descended, and every key of a differing
leaf bucket is copied shore -> mangrove. Each hash compared costs 1 bandwidth,
each key copied costs 1; a window's sync must fit in `bandwidth`. A sync over
budget is cut off and the window fails (replicas left unequal).

Win: every window syncs in budget and the replicas are equal afterwards.
Merkle descent wins; full copy and a flat scan of every leaf hash blow the
budget. Deterministic and offline: integers only, the shared 32-bit LCG,
zlib.crc32.

Reusable pieces:
  validate(cfg) -> Config
  keys_for(config) / bucket(key, depth)
  build_tree(replica, keys, depth) -> list of levels of hashes (root first)
  merkle_sync / full_copy_sync / leaf_scan_sync (shore, mangrove, keys, depth) -> cost
  simulate(config, sync=None) -> Result
  islands_from_shoals(shoals_cfg)  tie-in: islands + keys_per_island = G86
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
import zlib
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

QUEST_ID = "q_merkle_mangroves"
VERSION = 1
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
WON, FAILED = "won", "failed"
FAIL_BW = "bandwidth_exceeded"
NPC_KEYS = ("start", "storm", "sync", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "mangroves", "islands", "seed", "npc"}
MG_KEYS = {"windows", "keys_per_island", "depth", "bandwidth", "max_drift"}


class MangroveError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    windows: int
    keys_per_island: int
    depth: int
    bandwidth: int
    max_drift: int
    islands: Tuple[str, ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise MangroveError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise MangroveError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise MangroveError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise MangroveError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise MangroveError(f"quest must be {QUEST_ID}")
    g = cfg.get("mangroves")
    if not isinstance(g, dict) or set(g) != MG_KEYS:
        raise MangroveError(f"mangroves must have exactly {sorted(MG_KEYS)}")
    w = _int(g["windows"], "windows", 1, 10_000)
    kpi = _int(g["keys_per_island"], "keys_per_island", 1, 10_000)
    d = _int(g["depth"], "depth", 0, 16)
    bw = _int(g["bandwidth"], "bandwidth", 1, 10 ** 9)
    md = _int(g["max_drift"], "max_drift", 0, 10_000)
    isl = cfg.get("islands")
    if not isinstance(isl, list) or not isl:
        raise MangroveError("islands must be a non-empty list")
    seen = []
    for it in isl:
        iid = it.get("id") if isinstance(it, dict) else None
        if not isinstance(iid, str) or not iid or set(iid) - ID_CHARS or iid in seen:
            raise MangroveError(f"bad or duplicate island id: {iid!r}")
        seen.append(iid)
    seed = _int(cfg.get("seed", 1), "seed", 0, 2 ** 32 - 1)
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or not isinstance(npc.get("name"), str):
        raise MangroveError("npc must have a name")
    lines = npc.get("lines")
    if not isinstance(lines, dict) or set(lines) != set(NPC_KEYS):
        raise MangroveError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    if not all(isinstance(v, str) and v for v in lines.values()):
        raise MangroveError("npc lines must be non-empty strings")
    return Config(w, kpi, d, bw, md, tuple(seen), seed, npc["name"], dict(lines))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self, n: int) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) % n


def keys_for(c: Config) -> List[str]:
    return [f"{i}:{k:04d}" for i in c.islands for k in range(c.keys_per_island)]


def bucket(key: str, depth: int) -> int:
    return zlib.crc32(key.encode()) & ((1 << depth) - 1)


def build_tree(rep: Dict[str, int], keys: List[str], depth: int) -> List[List[int]]:
    leaves = [[] for _ in range(1 << depth)]
    for k in keys:
        leaves[bucket(k, depth)].append(k)
    level = [zlib.crc32(json.dumps([(k, rep[k]) for k in sorted(b)]).encode()) for b in leaves]
    levels = [level]
    while len(level) > 1:
        level = [zlib.crc32(f"{level[i]}:{level[i + 1]}".encode()) for i in range(0, len(level), 2)]
        levels.insert(0, level)
    return levels


def _leaf_keys(keys, depth, idx):
    return [k for k in keys if bucket(k, depth) == idx]


def _copy(shore, mangrove, ks) -> int:
    for k in ks:
        mangrove[k] = shore[k]
    return len(ks)


def merkle_sync(shore, mangrove, keys, depth) -> int:
    a, b = build_tree(shore, keys, depth), build_tree(mangrove, keys, depth)
    cost, frontier = 0, [0]
    for lvl in range(depth + 1):
        nxt = []
        for idx in frontier:
            cost += 1
            if a[lvl][idx] != b[lvl][idx]:
                if lvl == depth:
                    cost += _copy(shore, mangrove, _leaf_keys(keys, depth, idx))
                else:
                    nxt += [2 * idx, 2 * idx + 1]
        frontier = nxt
    return cost


def leaf_scan_sync(shore, mangrove, keys, depth) -> int:
    a, b = build_tree(shore, keys, depth)[-1], build_tree(mangrove, keys, depth)[-1]
    cost = 0
    for idx in range(len(a)):
        cost += 1
        if a[idx] != b[idx]:
            cost += _copy(shore, mangrove, _leaf_keys(keys, depth, idx))
    return cost


def full_copy_sync(shore, mangrove, keys, depth) -> int:
    return _copy(shore, mangrove, keys)


Sync = Callable[[Dict[str, int], Dict[str, int], List[str], int], int]


@dataclass
class Result:
    status: str
    reason: Optional[str]
    windows_ok: int
    worst_cost: int
    total_cost: int
    drifted: int
    equal: bool


def simulate(c: Config, sync: Optional[Sync] = None) -> Result:
    sync = sync or merkle_sync
    rng, keys = Lcg(c.seed), keys_for(c)
    shore = {k: 0 for k in keys}
    ok = worst = total = drifted = 0
    for w in range(c.windows):
        mangrove = dict(shore)
        n = rng.next(c.max_drift + 1)
        for _ in range(n):
            k = keys[rng.next(len(keys))]
            mangrove[k] = shore[k] + 1 + rng.next(9)
        drifted += n
        trial = dict(mangrove)
        cost = sync(shore, trial, keys, c.depth)
        if trial != shore:
            raise AssertionError("sync left replicas unequal")
        worst, total = max(worst, cost), total + cost
        if cost <= c.bandwidth:
            ok += 1
        for k in keys:  # shore keeps writing between windows
            if rng.next(100) == 0:
                shore[k] += 1
    status = WON if ok == c.windows else FAILED
    return Result(status, None if status == WON else FAIL_BW, ok, worst, total, drifted,
                  status == WON)


def islands_from_shoals(shoals_cfg) -> Tuple[List[dict], int]:
    """G86 tie-in: islands and keys_per_island from Compaction Shoals, read-only."""
    return ([{"id": it["id"]} for it in shoals_cfg["islands"]],
            shoals_cfg["shoals"]["keys_per_island"])


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason,
            "windows_ok": r.windows_ok, "windows": c.windows, "worst_cost": r.worst_cost,
            "bandwidth": c.bandwidth, "total_cost": r.total_cost, "drifted": r.drifted}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--sync", choices=["merkle", "leaf_scan", "full_copy"], default="merkle")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    s = {"merkle": merkle_sync, "leaf_scan": leaf_scan_sync, "full_copy": full_copy_sync}[a.sync]
    r = simulate(c, s)
    print(npc_say(c, "start"))
    print(json.dumps(receipt(c, r), sort_keys=True))
    print(npc_say(c, "win" if r.status == WON else "fail"))
    return 0 if r.status == WON else 1


if __name__ == "__main__":
    sys.exit(main())
