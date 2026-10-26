# SPDX-License-Identifier: MIT
"""G166 Tide Clocks (DiskSaver Island, quest q_tide_clocks).

Islands edit the same saves while the ferry is out, then the ferry carries
each island's saves to another island and they merge. The islands and the
save keys are the G86 Compaction Shoals ones (read-only). Every island's
wall clock is skewed by a seeded offset. The Clockwright picks the clock
that decides which edit survives a merge:
  wall      last-writer-wins by skewed wall time: a causally later edit on
            a slow clock loses to the edit it replaced, and concurrent
            edits are silently dropped
  lamport   last-writer-wins by Lamport time: consistent with causality,
            but concurrent edits are still silently dropped
  vector    vector clocks: a version is dropped only if another version
            dominates it; concurrent versions stay as siblings and go to
            the Merge Keeper, whose next edit supersedes them all
Win: after the final all-to-all sync no edit is lost (every edit is either
a surviving version or an ancestor of one). Deterministic and offline.

Science (pinned in tests): vc_lt(a, b) iff a happened-before b against a
brute-force causal-history oracle; Lamport hb(a, b) => L(a) < L(b) but not
the reverse; the conflicts the vector clock detects at merges equal the
oracle's concurrent pairs.

Reusable pieces:
  validate(cfg) -> Config
  run(config, clock) -> Result ; trace(config) -> versions
  vc_lt / concurrent / happened_before
  islands_from_shoals(shoals_cfg)  tie-in: islands + keys_per_island = G86
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

QUEST_ID = "q_tide_clocks"
VERSION = 1
CLOCKS = ("wall", "lamport", "vector")
WON, FAILED = "won", "failed"
FAIL_LOST = "edits_lost"
NPC_KEYS = ("start", "ferry", "conflict", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "clocks", "shoals_data", "seed", "npc"}
C_KEYS = {"islands", "saves", "steps", "edit_permille", "max_skew", "clock"}


class ClockError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    islands: Tuple[str, ...]
    saves: Tuple[str, ...]
    steps: int
    edit_permille: int
    max_skew: int
    clock: str
    seed: int
    npc_name: str
    lines: Dict[str, str]


@dataclass(frozen=True)
class Ver:
    vid: int
    save: str
    island: int
    wall: int
    lamport: int
    vc: Tuple[int, ...]
    history: FrozenSet[int]  # vids that happened before this edit (oracle)


@dataclass
class Result:
    status: str
    reason: Optional[str]
    clock: str
    edits: int
    lost: int
    detected_conflicts: int
    oracle_conflicts: int
    causal_inversions: int
    survivors: int
    lost_vids: List[int] = field(default_factory=list)


def islands_from_shoals(shoals_cfg) -> Tuple[List[str], int]:
    """G86 tie-in: island ids and keys_per_island from Compaction Shoals, read-only."""
    return [it["id"] for it in shoals_cfg["islands"]], shoals_cfg["shoals"]["keys_per_island"]


def _load_shoals(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def validate(cfg) -> Config:
    if not isinstance(cfg, dict) or set(cfg) != TOP_KEYS:
        raise ClockError(f"top-level keys must be {sorted(TOP_KEYS)}")
    if cfg["v"] != VERSION or cfg["quest"] != QUEST_ID:
        raise ClockError("bad version or quest")
    c = cfg["clocks"]
    if not isinstance(c, dict) or set(c) != C_KEYS:
        raise ClockError(f"clocks keys must be {sorted(C_KEYS)}")
    for k in ("islands", "saves", "steps", "edit_permille", "max_skew"):
        if not isinstance(c[k], int) or isinstance(c[k], bool) or c[k] < 0:
            raise ClockError(f"clocks.{k} must be a non-negative int")
    if c["clock"] not in CLOCKS:
        raise ClockError(f"clocks.clock must be one of {CLOCKS}")
    if not 1 <= c["edit_permille"] <= 999:
        raise ClockError("edit_permille must be 1..999")
    ids, kpi = islands_from_shoals(_load_shoals(cfg["shoals_data"]))
    if not 2 <= c["islands"] <= len(ids):
        raise ClockError(f"islands must be 2..{len(ids)} (G86 islands)")
    if not 1 <= c["saves"] <= kpi:
        raise ClockError(f"saves must be 1..{kpi} (G86 keys_per_island)")
    if c["steps"] < 1:
        raise ClockError("steps must be >= 1")
    npc = cfg["npc"]
    if not isinstance(npc, dict) or set(npc.get("lines", {})) != set(NPC_KEYS) or not npc.get("name"):
        raise ClockError(f"npc needs name and lines {NPC_KEYS}")
    if not isinstance(cfg["seed"], int):
        raise ClockError("seed must be int")
    return Config(tuple(ids[:c["islands"]]), tuple(f"save_{i:03d}" for i in range(c["saves"])),
                  c["steps"], c["edit_permille"], c["max_skew"], c["clock"], cfg["seed"],
                  npc["name"], dict(npc["lines"]))


def vc_le(a: Tuple[int, ...], b: Tuple[int, ...]) -> bool:
    return all(x <= y for x, y in zip(a, b))


def vc_lt(a: Tuple[int, ...], b: Tuple[int, ...]) -> bool:
    return vc_le(a, b) and a != b


def concurrent(a: Ver, b: Ver) -> bool:
    return not vc_le(a.vc, b.vc) and not vc_le(b.vc, a.vc)


def happened_before(a: Ver, b: Ver) -> bool:
    """Brute-force oracle: a is in b's causal history."""
    return a.vid in b.history


def _key(clock: str, v: Ver):
    return (v.wall, v.island, v.vid) if clock == "wall" else (v.lamport, v.island, v.vid)


class _Island:
    def __init__(self, idx: int, n: int, skew: int):
        self.idx, self.skew = idx, skew
        self.lamport = 0
        self.vc = [0] * n
        self.seen: set = set()
        self.store: Dict[str, List[Ver]] = {}


def _merge_into(clock: str, isl: _Island, save: str, incoming: List[Ver], stats: dict):
    cur = isl.store.get(save, [])
    pool = {v.vid: v for v in cur + incoming}
    vs = list(pool.values())
    # oracle: concurrent pairs among the causally maximal versions meeting here
    top = [a for a in vs if not any(happened_before(a, b) for b in vs)]
    for a in top:
        for b in top:
            if a.vid < b.vid:
                stats["oracle"].add((a.vid, b.vid))
    if clock == "vector":
        keep = [v for v in vs if not any(vc_lt(v.vc, w.vc) for w in vs)]
        for a in keep:
            for b in keep:
                if a.vid < b.vid and concurrent(a, b):
                    stats["detected"].add((a.vid, b.vid))
    else:
        keep = [max(vs, key=lambda v: _key(clock, v))] if vs else []
    for v in vs:  # an edit dropped by a version that never saw it is silently lost
        if v not in keep and not any(happened_before(v, w) for w in keep):
            stats["lost"].add(v.vid)
    isl.store[save] = sorted(keep, key=lambda v: v.vid)


def _absorb(isl: _Island, vs: List[Ver]):
    for v in vs:
        isl.seen |= set(v.history) | {v.vid}
        isl.lamport = max(isl.lamport, v.lamport)
        isl.vc = [max(x, y) for x, y in zip(isl.vc, v.vc)]


def run(c: Config, clock: Optional[str] = None) -> Tuple[Result, List[Ver]]:
    clock = c.clock if clock is None else clock
    rng = random.Random(c.seed)
    n = len(c.islands)
    skews = [rng.randint(-c.max_skew, c.max_skew) for _ in range(n)]
    isl = [_Island(i, n, skews[i]) for i in range(n)]
    versions: List[Ver] = []
    stats = {"oracle": set(), "detected": set(), "lost": set()}

    def ferry(src: _Island, dst: _Island):
        for save, vs in sorted(src.store.items()):
            _merge_into(clock, dst, save, list(vs), stats)
            _absorb(dst, vs)

    for t in range(1, c.steps + 1):
        if rng.randrange(1000) < c.edit_permille:
            i = rng.randrange(n)
            save = c.saves[rng.randrange(len(c.saves))]
            me = isl[i]
            me.lamport += 1
            me.vc[i] += 1
            hist = frozenset(me.seen)
            v = Ver(len(versions), save, i, t + me.skew, me.lamport, tuple(me.vc), hist)
            versions.append(v)
            me.seen.add(v.vid)
            # the editor has seen every local sibling, so the new edit supersedes them
            me.store[save] = [v]
        else:
            i, j = rng.sample(range(n), 2)
            ferry(isl[i], isl[j])
    for _ in range(2):  # final all-to-all sync
        for a in isl:
            for b in isl:
                if a is not b:
                    ferry(a, b)
    survivors = {v.vid: v for x in isl for vs in x.store.values() for v in vs}
    lost = sorted(stats["lost"])
    inv = sum(1 for b in versions for a in versions if happened_before(a, b) and a.save == b.save and a.wall >= b.wall)
    status = WON if not lost else FAILED
    r = Result(status, None if status == WON else FAIL_LOST, clock, len(versions), len(lost),
               len(stats["detected"]), len(stats["oracle"]), inv, len(survivors), lost)
    r.oracle_pairs = stats["oracle"]  # type: ignore[attr-defined]
    r.detected_pairs = stats["detected"]  # type: ignore[attr-defined]
    return r, versions


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason, "clock": r.clock, "edits": r.edits,
            "lost": r.lost, "detected_conflicts": r.detected_conflicts, "oracle_conflicts": r.oracle_conflicts,
            "causal_inversions": r.causal_inversions, "survivors": r.survivors}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--clock", choices=CLOCKS, default=None)
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    r, _ = run(c, a.clock)
    print(npc_say(c, "start"))
    print(json.dumps(receipt(c, r), sort_keys=True))
    print(npc_say(c, "win" if r.status == WON else "fail"))
    return 0 if r.status == WON else 1


if __name__ == "__main__":
    sys.exit(main())
