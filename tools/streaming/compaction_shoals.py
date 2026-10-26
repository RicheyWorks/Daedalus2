# SPDX-License-Identifier: MIT
"""G86 Compaction Shoals (DiskSaver Island, quest q_compaction_shoals).

Recovered island writes (the G79 Journal Tide islands) settle on the shoals as
an LSM tree. Puts and deletes fill a memtable; a full memtable flushes into a
sorted run on level 0. Every lookup probes the memtable, then runs newest
first, until it finds the key (a tombstone means "deleted"): runs probed is the
read amplification. Compacting merges every run of level i with level i+1 into
one run on level i+1; rows written are the write amplification and are paid
from a fixed io_budget. Tombstones are dropped only when merging into the
deepest non-empty level.

The keeper wins when the season ends with io spent <= io_budget and average
probes per lookup <= max_probes_x100 / 100. Tuned leveled compaction wins;
never-compact drowns reads, compact-every-flush runs out of ink. Every lookup
is checked against a plain dict, so the tree never lies.

Deterministic and offline: integers only, the shared 32-bit LCG.

Reusable pieces:
  validate(cfg) -> Config
  ops(config) -> list of ("put"|"del"|"get", key, value)
  Shoals: put/delete/get/flush/compact/runs
  never_policy / every_flush_policy / leveled(l0_trigger, ratio)
  simulate(config, policy=None) -> Result
  islands_from_journal(journal_cfg)  tie-in: key weights = G79 islands
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

QUEST_ID = "q_compaction_shoals"
VERSION = 1
MAX_OPS = 200_000
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
WON, FAILED = "won", "failed"
FAIL_IO, FAIL_READS = "io_budget_exceeded", "read_amplification"
NPC_KEYS = ("start", "flush", "compact", "win", "fail_io", "fail_reads")
TOP_KEYS = {"v", "quest", "lore", "shoals", "islands", "seed", "npc"}
SHOAL_KEYS = {"ops", "keys_per_island", "memtable", "io_budget",
              "max_probes_x100", "get_permille", "del_permille"}
TOMB = None


class ShoalsError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    ops: int
    keys_per_island: int
    memtable: int
    io_budget: int
    max_probes_x100: int
    get_permille: int
    del_permille: int
    islands: Tuple[Tuple[str, int], ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise ShoalsError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise ShoalsError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise ShoalsError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise ShoalsError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise ShoalsError(f"quest must be {QUEST_ID}")
    s = cfg.get("shoals")
    if not isinstance(s, dict) or set(s) != SHOAL_KEYS:
        raise ShoalsError(f"shoals must have exactly {sorted(SHOAL_KEYS)}")
    ops = _int(s["ops"], "ops", 1, MAX_OPS)
    kpi = _int(s["keys_per_island"], "keys_per_island", 1, 10_000)
    mem = _int(s["memtable"], "memtable", 1, 10_000)
    io = _int(s["io_budget"], "io_budget", 0, 10 ** 9)
    mp = _int(s["max_probes_x100"], "max_probes_x100", 100, 100_000)
    gp = _int(s["get_permille"], "get_permille", 0, 1000)
    dp = _int(s["del_permille"], "del_permille", 0, 1000)
    if gp + dp > 1000:
        raise ShoalsError("get_permille + del_permille must be <= 1000")
    isl = cfg.get("islands")
    if not isinstance(isl, list) or not isl:
        raise ShoalsError("islands must be a non-empty list")
    seen, out = set(), []
    for it in isl:
        if not isinstance(it, dict) or set(it) != {"id", "weight"}:
            raise ShoalsError("island must be {id, weight}")
        iid = it["id"]
        if not isinstance(iid, str) or not iid or set(iid) - ID_CHARS or iid in seen:
            raise ShoalsError(f"bad or duplicate island id: {iid!r}")
        seen.add(iid)
        out.append((iid, _int(it["weight"], "weight", 1, 1000)))
    seed = _int(cfg.get("seed", 1), "seed", 0, 2 ** 32 - 1)
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or not isinstance(npc.get("name"), str):
        raise ShoalsError("npc must have a name")
    lines = npc.get("lines")
    if not isinstance(lines, dict) or set(lines) != set(NPC_KEYS):
        raise ShoalsError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    if not all(isinstance(v, str) and v for v in lines.values()):
        raise ShoalsError("npc lines must be non-empty strings")
    return Config(ops, kpi, mem, io, mp, gp, dp, tuple(out), seed, npc["name"], dict(lines))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self, n: int) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) % n


def ops(c: Config) -> List[Tuple[str, str, int]]:
    rng, total, out = Lcg(c.seed), sum(w for _, w in c.islands), []
    for i in range(c.ops):
        r = rng.next(total)
        for iid, w in c.islands:
            if r < w:
                break
            r -= w
        key = f"{iid}:{rng.next(c.keys_per_island):04d}"
        k = rng.next(1000)
        kind = "get" if k < c.get_permille else "del" if k < c.get_permille + c.del_permille else "put"
        out.append((kind, key, i))
    return out


Run = List[Tuple[str, Optional[int]]]  # sorted by key; value None = tombstone


def merge(newer: Run, older: Run, drop_tombs: bool) -> Run:
    d = dict(older)
    d.update(newer)
    return [(k, v) for k, v in sorted(d.items()) if not (drop_tombs and v is TOMB)]


class Shoals:
    def __init__(self, memtable: int):
        self.cap = memtable
        self.mem: Dict[str, Optional[int]] = {}
        self.levels: List[List[Run]] = [[]]  # each level: runs newest first
        self.io = 0
        self.probes = 0
        self.gets = 0
        self.flushes = 0
        self.compactions = 0

    def _write(self, k, v) -> bool:
        self.mem[k] = v
        if len(self.mem) >= self.cap:
            self.flush()
            return True
        return False

    def put(self, k, v):
        return self._write(k, v)

    def delete(self, k):
        return self._write(k, TOMB)

    def flush(self):
        if not self.mem:
            return
        run = sorted(self.mem.items())
        self.levels[0].insert(0, run)
        self.io += len(run)
        self.flushes += 1
        self.mem = {}

    def get(self, k) -> Optional[int]:
        self.gets += 1
        if k in self.mem:
            return self.mem[k]
        for level in self.levels:
            for run in level:
                self.probes += 1
                lo, hi = 0, len(run)
                while lo < hi:
                    mid = (lo + hi) // 2
                    if run[mid][0] < k:
                        lo = mid + 1
                    else:
                        hi = mid
                if lo < len(run) and run[lo][0] == k:
                    return run[lo][1]
        return None

    def size(self, i: int) -> int:
        return sum(len(r) for r in self.levels[i]) if i < len(self.levels) else 0

    def compact(self, i: int):
        """Merge every run of level i plus level i+1 into one run on level i+1."""
        if i >= len(self.levels) or not self.levels[i]:
            return
        if i + 1 == len(self.levels):
            self.levels.append([])
        merged: Run = []
        for run in reversed(self.levels[i + 1] + []):
            merged = merge(run, merged, False)
        for run in reversed(self.levels[i]):
            merged = merge(run, merged, False)
        bottom = all(not lv for lv in self.levels[i + 2:])
        if bottom:
            merged = [(k, v) for k, v in merged if v is not TOMB]
        self.levels[i] = []
        self.levels[i + 1] = [merged] if merged else []
        self.io += len(merged)
        self.compactions += 1

    def runs(self) -> int:
        return sum(len(lv) for lv in self.levels)


Policy = Callable[[Shoals], None]


def never_policy(sh: Shoals):
    pass


def every_flush_policy(sh: Shoals):
    for i in range(len(sh.levels) - 1):
        sh.compact(i)
    if len(sh.levels[-1]) > 1 or len(sh.levels) == 1:
        sh.compact(len(sh.levels) - 1)


def leveled(l0_trigger: int = 4, ratio: int = 10) -> Policy:
    def policy(sh: Shoals):
        if len(sh.levels[0]) >= l0_trigger:
            sh.compact(0)
        i = 1
        while i < len(sh.levels):
            if sh.size(i) > sh.cap * l0_trigger * ratio ** i:
                sh.compact(i)
            i += 1
    return policy


@dataclass
class Result:
    status: str
    reason: Optional[str]
    io: int
    gets: int
    probes: int
    probes_x100: int
    flushes: int
    compactions: int
    runs: int
    log: List[str]


def simulate(c: Config, policy: Optional[Policy] = None) -> Result:
    policy = policy or leveled()
    sh, ref, log = Shoals(c.memtable), {}, []
    for kind, key, val in ops(c):
        if kind == "get":
            if sh.get(key) != ref.get(key):
                raise AssertionError(f"lookup mismatch for {key}")
            continue
        flushed = sh.put(key, val) if kind == "put" else sh.delete(key)
        if kind == "put":
            ref[key] = val
        else:
            ref.pop(key, None)
        if flushed:
            before = sh.compactions
            policy(sh)
            if sh.compactions > before:
                log.append("compact")
            else:
                log.append("flush")
    px = (sh.probes * 100) // sh.gets if sh.gets else 0
    reason = FAIL_IO if sh.io > c.io_budget else FAIL_READS if px > c.max_probes_x100 else None
    return Result(FAILED if reason else WON, reason, sh.io, sh.gets, sh.probes, px,
                  sh.flushes, sh.compactions, sh.runs(), log)


def islands_from_journal(journal_cfg) -> List[dict]:
    """G79 tie-in: write weights are the Journal Tide islands, read-only."""
    return [{"id": it["id"], "weight": it["weight"]} for it in journal_cfg["islands"]]


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason, "io": r.io,
            "io_budget": c.io_budget, "probes_x100": r.probes_x100,
            "max_probes_x100": c.max_probes_x100, "flushes": r.flushes,
            "compactions": r.compactions, "runs": r.runs}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--policy", choices=["leveled", "never", "every_flush"], default="leveled")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    pol = {"leveled": leveled(), "never": never_policy, "every_flush": every_flush_policy}[a.policy]
    r = simulate(c, pol)
    print(npc_say(c, "start"))
    print(json.dumps(receipt(c, r), sort_keys=True))
    print(npc_say(c, "win" if r.status == WON else "fail_io" if r.reason == FAIL_IO else "fail_reads"))
    return 0 if r.status == WON else 1


if __name__ == "__main__":
    sys.exit(main())
