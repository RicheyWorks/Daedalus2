# SPDX-License-Identifier: MIT
"""G63 Defrag Tide (DiskSaver Island, quest q_defrag_tide).

The cache shelf under DiskSaver Island is a strip of disk blocks. Island caches
lie scattered across it in fragments, and every break in a cache costs a seek
when the island streams in. Each tide the keeper may move up to
`moves_per_tide` blocks into free slots; then the tide erodes one seeded free
block into a bad block that can never be used again. Get the weighted seek
count (sum of priority * (runs - 1)) down to `seek_target` before the tides
run out. Bad blocks only ever eat free space, so waiting makes it harder.

Deterministic and offline: integers only, a seeded 32-bit LCG (same constants
as G39/G59), no wall clock, so a Java/C++ port can replay `log` line for line.

Reusable pieces (no Unreal, no I/O except the CLI):
  validate(cfg) -> Config               strict defrag-tide-v1 parser
  new_state(config) -> State            seeded scatter of every cache
  runs(state, fid) / seeks(state, config)
  tick(state, config, moves)            one tide: moves, check, erosion
  keeper_policy(state, config)          reference planner (window packing)
  simulate(config, policy=None) -> State
  files_from_byte_spring(spring, block_kib)  G39 tie-in: caches from Byte Spring islands
  npc_say / receipt                     NPC bark, G12-style activity receipt
Units: one block == `block_kib` KiB (DSB 1 KiB cost unit).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

QUEST_ID = "q_defrag_tide"
VERSION = 1
MAX_BLOCKS = 100_000
MAX_TIDES = 10_000
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
RUNNING, WON, FAILED = "running", "won", "failed"
FAIL_TIDES = "tides_out"
FREE, BAD = None, "#bad"
NPC_KEYS = ("start", "move", "erode", "close", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "disk", "files", "seed", "npc"}
DISK_KEYS = {"blocks", "block_kib", "moves_per_tide", "tides", "seek_target"}
FILE_KEYS = {"id", "blocks", "priority"}


class DefragError(ValueError):
    pass


@dataclass(frozen=True)
class Cache:
    id: str
    blocks: int
    priority: int


@dataclass(frozen=True)
class Config:
    blocks: int
    block_kib: int
    moves_per_tide: int
    tides: int
    seek_target: int
    files: Tuple[Cache, ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]

    def prio(self, fid: str) -> int:
        for f in self.files:
            if f.id == fid:
                return f.priority
        raise KeyError(fid)


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise DefragError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise DefragError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise DefragError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise DefragError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise DefragError(f"quest must be {QUEST_ID}")
    d = cfg.get("disk")
    if not isinstance(d, dict) or set(d) != DISK_KEYS:
        raise DefragError(f"disk must have exactly {sorted(DISK_KEYS)}")
    nblocks = _int(d["blocks"], "disk.blocks", 2, MAX_BLOCKS)
    raw = cfg.get("files")
    if not isinstance(raw, list) or not raw:
        raise DefragError("files must be a non-empty list")
    files, seen = [], set()
    for n, r in enumerate(raw):
        if not isinstance(r, dict) or set(r) != FILE_KEYS:
            raise DefragError(f"files[{n}] must have exactly {sorted(FILE_KEYS)}")
        fid = r["id"]
        if not isinstance(fid, str) or not fid or len(fid) > 64 or set(fid) - ID_CHARS:
            raise DefragError(f"files[{n}].id must be 1..64 chars of [A-Za-z0-9_]")
        if fid in seen:
            raise DefragError(f"duplicate file id {fid}")
        seen.add(fid)
        files.append(Cache(fid, _int(r["blocks"], f"files[{n}].blocks", 1, nblocks),
                           _int(r["priority"], f"files[{n}].priority", 1, 100)))
    used = sum(f.blocks for f in files)
    tides = _int(d["tides"], "disk.tides", 1, MAX_TIDES)
    if used + tides >= nblocks:
        raise DefragError("disk needs more free blocks than tides (erosion would fill it)")
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or set(npc) != {"name", "lines"} or not isinstance(npc["name"], str) or not npc["name"]:
        raise DefragError("npc must have a name and lines")
    if not isinstance(npc["lines"], dict) or set(npc["lines"]) != set(NPC_KEYS):
        raise DefragError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    for k, v in npc["lines"].items():
        if not isinstance(v, str) or not v or len(v) > 200:
            raise DefragError(f"npc.lines.{k} must be 1..200 chars")
    return Config(nblocks, _int(d["block_kib"], "disk.block_kib", 1, 1 << 20),
                  _int(d["moves_per_tide"], "disk.moves_per_tide", 1, MAX_BLOCKS), tides,
                  _int(d["seek_target"], "disk.seek_target", 0, 1 << 30), tuple(files),
                  _int(cfg.get("seed", 1), "seed", 0, 2**32 - 1), npc["name"], dict(npc["lines"]))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self) -> int:
        self.s = (1664525 * self.s + 1013904223) & 0xFFFFFFFF
        return self.s

    def below(self, n: int) -> int:
        return (self.next() >> 8) % n


@dataclass
class State:
    rng: Lcg
    disk: List[Optional[object]]                 # slot -> (fid, k) | FREE | BAD
    where: Dict[str, List[int]]                  # fid -> slot of block k
    tide: int = 0
    moves_used: int = 0
    outcome: str = RUNNING
    fail_reason: Optional[str] = None
    events: List[str] = field(default_factory=list)
    log: List[str] = field(default_factory=list)


def new_state(config: Config) -> State:
    rng = Lcg(config.seed)
    slots = list(range(config.blocks))
    for i in range(len(slots) - 1, 0, -1):          # seeded Fisher-Yates
        j = rng.below(i + 1)
        slots[i], slots[j] = slots[j], slots[i]
    disk: List[Optional[object]] = [FREE] * config.blocks
    where: Dict[str, List[int]] = {}
    p = 0
    for f in config.files:
        where[f.id] = []
        for k in range(f.blocks):
            disk[slots[p]] = (f.id, k)
            where[f.id].append(slots[p])
            p += 1
    st = State(rng, disk, where, events=["start"])
    st.log.append(f"t0 start seeks={seeks(st, config)} target={config.seek_target}")
    return st


def runs(state: State, fid: str) -> int:
    w = state.where[fid]
    return 1 + sum(1 for k in range(1, len(w)) if w[k] != w[k - 1] + 1)


def seeks(state: State, config: Config) -> int:
    return sum(f.priority * (runs(state, f.id) - 1) for f in config.files)


def move(state: State, fid: str, k: int, dest: int):
    if fid not in state.where or not isinstance(k, int) or not 0 <= k < len(state.where[fid]):
        raise DefragError(f"bad block {fid}[{k}]")
    if not isinstance(dest, int) or not 0 <= dest < len(state.disk):
        raise DefragError(f"bad slot {dest}")
    if state.disk[dest] is not FREE:
        raise DefragError(f"slot {dest} is not free")
    src = state.where[fid][k]
    state.disk[src] = FREE
    state.disk[dest] = (fid, k)
    state.where[fid][k] = dest


def _check(state: State, config: Config) -> bool:
    if seeks(state, config) <= config.seek_target:
        state.outcome = WON
        state.events.append("win")
        state.log.append(f"t{state.tide} WIN seeks={seeks(state, config)} moves={state.moves_used}")
        return True
    return False


def tick(state: State, config: Config, moves: Sequence[Tuple[str, int, int]] = ()) -> State:
    """One tide: up to moves_per_tide moves, win check, then erosion, then fail check."""
    if state.outcome != RUNNING:
        raise DefragError("game is over")
    if len(moves) > config.moves_per_tide:
        raise DefragError(f"at most {config.moves_per_tide} moves per tide")
    state.tide += 1
    state.events = []
    before = seeks(state, config)
    for m in moves:
        if not (isinstance(m, (tuple, list)) and len(m) == 3):
            raise DefragError(f"bad move {m!r}")
        move(state, *m)
        state.moves_used += 1
    if moves:
        state.events.append("move")
        state.log.append(f"t{state.tide} moved {len(moves)} seeks {before}->{seeks(state, config)}")
    if _check(state, config):
        return state
    free = [i for i, s in enumerate(state.disk) if s is FREE]
    bad = free[state.rng.below(len(free))]
    state.disk[bad] = BAD
    state.events.append("erode")
    state.log.append(f"t{state.tide} erode slot {bad}")
    s = seeks(state, config)
    if s <= config.seek_target * 2 or s <= config.seek_target + 2:
        state.events.append("close")
    if state.tide >= config.tides:
        state.outcome, state.fail_reason = FAILED, FAIL_TIDES
        state.events.append("fail")
        state.log.append(f"t{state.tide} FAIL tides_out seeks={s}")
    return state


def _plan_file(state: State, fid: str, budget: int) -> List[Tuple[str, int, int]]:
    """Cheapest window for fid. A slot is free (1 move), already holding fid's block at
    that offset (0), or holding a block of a still-fragmented cache, which is evicted to
    the first free slot outside the window (1 extra move). Packed caches and bad blocks
    are never disturbed. At most `budget` moves; the window is finished next tide.
    Moves are applied to `state` (a planning copy) as they are made."""
    n = len(state.where[fid])
    free_total = sum(1 for x in state.disk if x is FREE)
    best = None
    for start in range(0, len(state.disk) - n + 1):
        cost, ev, ok = 0, 0, True
        for k in range(n):
            x = state.disk[start + k]
            if x == (fid, k):
                continue
            if x is FREE:
                cost += 1
            elif x == BAD or runs(state, x[0]) == 1 and x[0] != fid:
                ok = False
                break
            else:
                cost += 2
                ev += 1
        if not ok or cost == 0:
            continue
        free_outside = free_total - sum(1 for k in range(n) if state.disk[start + k] is FREE)
        if ev > free_outside:
            continue
        if best is None or cost < best[0]:
            best = (cost, start)
    if best is None:
        return []
    start = best[1]
    window = range(start, start + n)
    plan: List[Tuple[str, int, int]] = []
    for k in range(n):                                   # evict squatters
        if len(plan) >= budget:
            return plan
        x = state.disk[start + k]
        if isinstance(x, tuple) and x != (fid, k):
            dest = next(i for i, y in enumerate(state.disk) if y is FREE and i not in window)
            plan.append((x[0], x[1], dest))
            move(state, x[0], x[1], dest)
    for k in range(n):                                   # place own blocks
        if len(plan) >= budget:
            return plan
        if state.disk[start + k] != (fid, k):
            plan.append((fid, k, start + k))
            move(state, fid, k, start + k)
    return plan


def keeper_policy(state: State, config: Config) -> List[Tuple[str, int, int]]:
    """Reference planner: pack fragmented caches into free windows, largest cache
    first, using the cheapest window (finishing it over several tides if needed). Plans on a copy."""
    work = State(state.rng, list(state.disk), {k: list(v) for k, v in state.where.items()})
    budget = config.moves_per_tide
    plan: List[Tuple[str, int, int]] = []
    for f in sorted(config.files, key=lambda c: (-c.blocks, -c.priority, c.id)):
        if runs(work, f.id) == 1 or budget == 0:
            continue
        mv = _plan_file(work, f.id, budget)
        plan.extend(mv)
        budget -= len(mv)
    return plan


def simulate(config: Config, policy=None) -> State:
    st = new_state(config)
    policy = policy or keeper_policy
    while st.outcome == RUNNING:
        tick(st, config, policy(st, config))
    return st


def files_from_byte_spring(spring: dict, block_kib: int) -> List[dict]:
    """G39 tie-in: each Byte Spring island becomes a cache of ceil(cost_kib/block_kib)
    blocks; priority = Byte Spring priority + 1."""
    _int(block_kib, "block_kib", 1, 1 << 20)
    out = []
    for isl in spring["islands"]:
        out.append({"id": isl["id"], "blocks": -(-int(isl["cost_kib"]) // block_kib),
                    "priority": int(isl["priority"]) + 1})
    return out


def npc_say(state: State, config: Config) -> Tuple[str, str]:
    for k in ("fail", "win", "close", "move", "erode", "start"):
        if k in state.events:
            return k, config.lines[k]
    return "erode", config.lines["erode"]


def receipt(state: State, config: Config) -> dict:
    s = seeks(state, config)
    return {
        "quest": QUEST_ID, "activity": "defrag_tide", "island": "disk-saver",
        "outcome": state.outcome, "fail_reason": state.fail_reason,
        "tides": state.tide, "moves": state.moves_used, "seeks": s,
        "seek_target": config.seek_target,
        "bad_blocks": sum(1 for x in state.disk if x == BAD),
        # score: tides left (permille of all tides) only when won
        "score": ((config.tides - state.tide) * 1000) // config.tides if state.outcome == WON else 0,
    }


def load(path: str) -> Config:
    with open(path, encoding="utf-8") as f:
        return validate(json.load(f))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G63 Defrag Tide (offline, seeded)")
    ap.add_argument("config")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--idle", action="store_true", help="never move a block")
    ap.add_argument("--trace", action="store_true")
    a = ap.parse_args(argv)
    try:
        with open(a.config, encoding="utf-8") as f:
            raw = json.load(f)
        if a.seed is not None:
            raw["seed"] = a.seed
        cfg = validate(raw)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    st = simulate(cfg, (lambda s, c: []) if a.idle else None)
    if a.trace:
        print("\n".join(st.log))
    print(json.dumps(receipt(st, cfg), sort_keys=True))
    print(f"{cfg.npc_name}: {npc_say(st, cfg)[1]}")
    return 0 if st.outcome == WON else 1


if __name__ == "__main__":
    sys.exit(main())
