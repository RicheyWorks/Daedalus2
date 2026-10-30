# SPDX-License-Identifier: MIT
"""G78 Coral Wear (DiskSaver Island, quest q_coral_wear).

The Reef's newest shelf is living coral: flash-like cells that wear out. Each
island's save lives in one cell. Every tick a seeded island rewrites its save:
the keeper picks a free cell, the save moves there (that cell gains one wear),
and the old cell is freed. A cell that reaches its seeded endurance retires
for good. Hot islands write often and cold ones rarely, so cells under cold
saves never wear. Once per tick the keeper may also *relocate* one save to
another free cell (costs one wear on the target) to free an unworn cell
(static wear leveling). The season is lost when a write finds no free living
cell. Survive `season_ticks`.

Deterministic and offline: integers only, the shared 32-bit LCG.

Reusable pieces:
  validate(cfg) -> Config
  new_state(config) / tick(state, config, target, relocate=None)
  first_free_policy  (the trap: always the lowest free cell)
  least_worn_policy  (dynamic leveling)
  leveling_policy    (dynamic + static: move the coldest save off the least-worn cell)
  simulate(config, policy=None) -> State
  islands_from_tide_chart(tide_cfg)  tie-in: write weights = G70 request weights
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

QUEST_ID = "q_coral_wear"
VERSION = 1
MAX_CELLS = 10_000
MAX_TICKS = 1_000_000
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
RUNNING, WON, FAILED = "running", "won", "failed"
FAIL_FULL = "no_living_cell"
NPC_KEYS = ("start", "write", "relocate", "retire", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "coral", "islands", "seed", "npc"}
CORAL_KEYS = {"cells", "endurance_min", "endurance_max", "season_ticks"}


class WearError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    cells: int
    endurance_min: int
    endurance_max: int
    season_ticks: int
    islands: Tuple[Tuple[str, int], ...]   # (id, write weight)
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise WearError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise WearError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise WearError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise WearError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise WearError(f"quest must be {QUEST_ID}")
    c = cfg.get("coral")
    if not isinstance(c, dict) or set(c) != CORAL_KEYS:
        raise WearError(f"coral must have exactly {sorted(CORAL_KEYS)}")
    cells = _int(c["cells"], "coral.cells", 2, MAX_CELLS)
    emin = _int(c["endurance_min"], "coral.endurance_min", 1, 1 << 30)
    emax = _int(c["endurance_max"], "coral.endurance_max", emin, 1 << 30)
    raw = cfg.get("islands")
    if not isinstance(raw, list) or not raw:
        raise WearError("islands must be a non-empty list")
    if len(raw) >= cells:
        raise WearError("need at least one spare cell beyond one per island")
    isl, seen = [], set()
    for n, r in enumerate(raw):
        if not isinstance(r, dict) or set(r) != {"id", "weight"}:
            raise WearError(f"islands[{n}] must have exactly id and weight")
        iid = r["id"]
        if not isinstance(iid, str) or not iid or len(iid) > 64 or set(iid) - ID_CHARS:
            raise WearError(f"islands[{n}].id must be 1..64 chars of [A-Za-z0-9_]")
        if iid in seen:
            raise WearError(f"duplicate island {iid}")
        seen.add(iid)
        isl.append((iid, _int(r["weight"], f"islands[{n}].weight", 1, 1000)))
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or set(npc) != {"name", "lines"} or not isinstance(npc["name"], str) or not npc["name"]:
        raise WearError("npc must have a name and lines")
    if not isinstance(npc["lines"], dict) or set(npc["lines"]) != set(NPC_KEYS):
        raise WearError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    for k, v in npc["lines"].items():
        if not isinstance(v, str) or not v or len(v) > 200:
            raise WearError(f"npc.lines.{k} must be 1..200 chars")
    return Config(cells, emin, emax, _int(c["season_ticks"], "coral.season_ticks", 1, MAX_TICKS),
                  tuple(isl), _int(cfg.get("seed", 1), "seed", 0, 2**32 - 1), npc["name"], dict(npc["lines"]))


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
    endurance: List[int]
    wear: List[int]
    holder: List[Optional[str]]        # cell -> island id
    home: Dict[str, int]               # island -> cell
    last_write: Dict[str, int]
    tick_no: int = 0
    writes: int = 0
    relocations: int = 0
    pending: Optional[str] = None      # island writing this tick
    outcome: str = RUNNING
    fail_reason: Optional[str] = None
    events: List[str] = field(default_factory=list)
    log: List[str] = field(default_factory=list)

    def alive(self, c: int) -> bool:
        return self.wear[c] < self.endurance[c]

    def free_cells(self) -> List[int]:
        return [c for c in range(len(self.wear)) if self.holder[c] is None and self.alive(c)]


def _draw(state: State, config: Config) -> str:
    total = sum(w for _, w in config.islands)
    r = state.rng.below(total)
    for iid, w in config.islands:
        if r < w:
            return iid
        r -= w
    raise AssertionError


def new_state(config: Config) -> State:
    rng = Lcg(config.seed)
    span = config.endurance_max - config.endurance_min + 1
    endu = [config.endurance_min + rng.below(span) for _ in range(config.cells)]
    holder: List[Optional[str]] = [None] * config.cells
    home = {}
    for n, (iid, _) in enumerate(config.islands):
        holder[n] = iid
        home[iid] = n
    st = State(rng, endu, [0] * config.cells, holder, home, {i: -1 for i, _ in config.islands}, events=["start"])
    st.pending = _draw(st, config)
    st.log.append(f"t0 start cells={config.cells} endurance_total={sum(endu)}")
    return st


def _put(state: State, iid: str, target: int):
    old = state.home[iid]
    state.holder[old] = None
    state.holder[target] = iid
    state.home[iid] = target
    state.wear[target] += 1
    if not state.alive(target):
        state.events.append("retire")
        state.log.append(f"t{state.tick_no} cell {target} retires after this save")


def tick(state: State, config: Config, target: int, relocate: Optional[Tuple[str, int]] = None) -> State:
    """Write the pending island's save into `target`; optionally relocate one save first."""
    if state.outcome != RUNNING:
        raise WearError("game is over")
    state.tick_no += 1
    state.events = []
    if relocate is not None:
        iid, cell = relocate
        if iid not in state.home or cell not in state.free_cells():
            raise WearError(f"bad relocate {relocate!r}")
        _put(state, iid, cell)
        state.relocations += 1
        state.events.append("relocate")
    if target not in state.free_cells():
        raise WearError(f"cell {target!r} is not a free living cell")
    iid = state.pending
    _put(state, iid, target)
    state.writes += 1
    state.last_write[iid] = state.tick_no
    state.events.append("write")
    if state.tick_no >= config.season_ticks:
        state.outcome = WON
        state.events.append("win")
        state.log.append(f"t{state.tick_no} WIN writes={state.writes} relocations={state.relocations}")
        return state
    state.pending = _draw(state, config)
    if not state.free_cells():
        state.outcome, state.fail_reason = FAILED, FAIL_FULL
        state.events.append("fail")
        state.log.append(f"t{state.tick_no} FAIL no free living cell")
    return state


def first_free_policy(state: State, config: Config):
    return min(state.free_cells()), None


def least_worn_policy(state: State, config: Config):
    return min(state.free_cells(), key=lambda c: (state.wear[c], c)), None


def leveling_policy(state: State, config: Config):
    """Dynamic leveling, plus static: when the least-worn held cell is far less worn than
    the most-worn free cell, move its (coldest) save onto that worn cell."""
    free = state.free_cells()
    reloc = None
    held = [c for c in range(config.cells)
            if state.holder[c] is not None and state.holder[c] != state.pending and state.alive(c)]
    if held and len(free) >= 2:
        cold = min(held, key=lambda c: (state.wear[c], c))
        worn = max(free, key=lambda c: (state.wear[c], -c))
        left = state.endurance[worn] - state.wear[worn]
        if state.wear[worn] - state.wear[cold] >= 4 and left >= 2:
            reloc = (state.holder[cold], worn)
            free = [c for c in free if c != worn] + [cold]
    tgt = min(free, key=lambda c: (state.wear[c], c))
    return tgt, reloc


def simulate(config: Config, policy=None) -> State:
    st = new_state(config)
    policy = policy or leveling_policy
    while st.outcome == RUNNING:
        tgt, rel = policy(st, config)
        tick(st, config, tgt, rel)
    return st


def islands_from_tide_chart(tide_cfg: dict, scale: int = 10, archives: int = 3) -> List[dict]:
    """G70 tie-in: islands that stream most also save most. Hot saves = the Tide Chart
    islands with weight x `scale`; plus `archives` cold archive saves (weight 1), the
    old snapshots the G59 Save Vault keeps on the Reef."""
    hot = [{"id": i["id"], "weight": int(i["weight"]) * scale} for i in tide_cfg["islands"]]
    cold = [{"id": f"archive_{chr(97 + n)}", "weight": 1} for n in range(archives)]
    return hot + cold


def npc_say(state: State, config: Config) -> Tuple[str, str]:
    for k in ("fail", "win", "retire", "relocate", "write", "start"):
        if k in state.events:
            return k, config.lines[k]
    return "write", config.lines["write"]


def receipt(state: State, config: Config) -> dict:
    dead = sum(1 for c in range(config.cells) if not state.alive(c))
    return {
        "quest": QUEST_ID, "activity": "coral_wear", "island": "disk-saver",
        "outcome": state.outcome, "fail_reason": state.fail_reason,
        "ticks": state.tick_no, "writes": state.writes, "relocations": state.relocations,
        "retired_cells": dead, "max_wear": max(state.wear), "min_wear": min(state.wear),
        # score: living cells left (permille) only when won
        "score": ((config.cells - dead) * 1000) // config.cells if state.outcome == WON else 0,
    }


def load(path: str) -> Config:
    with open(path, encoding="utf-8") as f:
        return validate(json.load(f))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G78 Coral Wear (offline, seeded)")
    ap.add_argument("config")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--policy", choices=("leveling", "least_worn", "first_free"), default="leveling")
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
    pol = {"leveling": leveling_policy, "least_worn": least_worn_policy, "first_free": first_free_policy}[a.policy]
    st = simulate(cfg, pol)
    if a.trace:
        print("\n".join(st.log))
    print(json.dumps(receipt(st, cfg), sort_keys=True))
    print(f"{cfg.npc_name}: {npc_say(st, cfg)[1]}")
    return 0 if st.outcome == WON else 1


if __name__ == "__main__":
    sys.exit(main())
