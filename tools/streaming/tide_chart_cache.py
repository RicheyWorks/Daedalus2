# SPDX-License-Identifier: MIT
"""G70 Tide Chart Cache (DiskSaver Island, quest q_tide_chart).

DiskSaver Island's hot pool (RAM) holds only `capacity_kib` of island caches.
Each tide a seeded island asks to stream in. A hit is free; a miss stalls for
the island's cost and the keeper must evict residents until it fits. The
harbour's tide chart shows the next `chart_len` requests, so a sharp keeper can
evict the island needed furthest in the future (Belady's rule); a lazy one
evicts the least recently used. Keep the season's total stall within
`stall_budget_kib`.

Deterministic and offline: integers only, the shared 32-bit LCG (G39/G59/G63/G67).

Reusable pieces:
  validate(cfg) -> Config
  requests(config) -> [island id]            seeded, weighted by priority
  new_state(config) / step(state, config, policy)
  chart_policy(state, config, need)          Belady over the visible chart
  lru_policy(state, config, need)            least recently used
  simulate(config, policy=None) -> State
  config_from_byte_spring(spring, ...)       G39 tie-in: islands + capacity from Byte Spring
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

QUEST_ID = "q_tide_chart"
VERSION = 1
MAX_KIB = 1_000_000_000
MAX_TIDES = 100_000
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
RUNNING, WON, FAILED = "running", "won", "failed"
FAIL_STALL = "stall_over_budget"
NPC_KEYS = ("start", "hit", "miss", "evict", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "pool", "islands", "seed", "npc"}
POOL_KEYS = {"capacity_kib", "tides", "chart_len", "stall_budget_kib"}
ISLAND_KEYS = {"id", "cost_kib", "weight"}


class CacheError(ValueError):
    pass


@dataclass(frozen=True)
class Island:
    id: str
    cost_kib: int
    weight: int


@dataclass(frozen=True)
class Config:
    capacity_kib: int
    tides: int
    chart_len: int
    stall_budget_kib: int
    islands: Tuple[Island, ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]

    def cost(self, iid: str) -> int:
        for i in self.islands:
            if i.id == iid:
                return i.cost_kib
        raise KeyError(iid)


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise CacheError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise CacheError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise CacheError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise CacheError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise CacheError(f"quest must be {QUEST_ID}")
    p = cfg.get("pool")
    if not isinstance(p, dict) or set(p) != POOL_KEYS:
        raise CacheError(f"pool must have exactly {sorted(POOL_KEYS)}")
    cap = _int(p["capacity_kib"], "pool.capacity_kib", 1, MAX_KIB)
    raw = cfg.get("islands")
    if not isinstance(raw, list) or len(raw) < 2:
        raise CacheError("islands must list at least 2 islands")
    islands, seen = [], set()
    for n, r in enumerate(raw):
        if not isinstance(r, dict) or set(r) != ISLAND_KEYS:
            raise CacheError(f"islands[{n}] must have exactly {sorted(ISLAND_KEYS)}")
        iid = r["id"]
        if not isinstance(iid, str) or not iid or len(iid) > 64 or set(iid) - ID_CHARS:
            raise CacheError(f"islands[{n}].id must be 1..64 chars of [A-Za-z0-9_]")
        if iid in seen:
            raise CacheError(f"duplicate island {iid}")
        seen.add(iid)
        islands.append(Island(iid, _int(r["cost_kib"], f"islands[{n}].cost_kib", 1, cap),
                              _int(r["weight"], f"islands[{n}].weight", 1, 1000)))
    if sum(i.cost_kib for i in islands) <= cap:
        raise CacheError("every island fits at once; the pool needs pressure")
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or set(npc) != {"name", "lines"} or not isinstance(npc["name"], str) or not npc["name"]:
        raise CacheError("npc must have a name and lines")
    if not isinstance(npc["lines"], dict) or set(npc["lines"]) != set(NPC_KEYS):
        raise CacheError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    for k, v in npc["lines"].items():
        if not isinstance(v, str) or not v or len(v) > 200:
            raise CacheError(f"npc.lines.{k} must be 1..200 chars")
    return Config(cap, _int(p["tides"], "pool.tides", 1, MAX_TIDES),
                  _int(p["chart_len"], "pool.chart_len", 0, MAX_TIDES),
                  _int(p["stall_budget_kib"], "pool.stall_budget_kib", 0, MAX_KIB),
                  tuple(islands), _int(cfg.get("seed", 1), "seed", 0, 2**32 - 1),
                  npc["name"], dict(npc["lines"]))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self) -> int:
        self.s = (1664525 * self.s + 1013904223) & 0xFFFFFFFF
        return self.s

    def below(self, n: int) -> int:
        return (self.next() >> 8) % n


def requests(config: Config) -> List[str]:
    rng = Lcg(config.seed)
    total = sum(i.weight for i in config.islands)
    out = []
    for _ in range(config.tides):
        r = rng.below(total)
        for i in config.islands:
            if r < i.weight:
                out.append(i.id)
                break
            r -= i.weight
    return out


@dataclass
class State:
    reqs: List[str]
    resident: List[str] = field(default_factory=list)
    last_used: Dict[str, int] = field(default_factory=dict)
    tide: int = 0
    hits: int = 0
    misses: int = 0
    stall_kib: int = 0
    evictions: int = 0
    outcome: str = RUNNING
    fail_reason: Optional[str] = None
    events: List[str] = field(default_factory=list)
    log: List[str] = field(default_factory=list)

    def chart(self, config: Config) -> List[str]:
        """Requests after the current one that the tide chart shows."""
        return self.reqs[self.tide + 1:self.tide + 1 + config.chart_len]


def used_kib(state: State, config: Config) -> int:
    return sum(config.cost(i) for i in state.resident)


def new_state(config: Config) -> State:
    st = State(requests(config), events=["start"])
    st.log.append(f"t0 start capacity={config.capacity_kib} budget={config.stall_budget_kib}")
    return st


def lru_policy(state: State, config: Config, need: str) -> str:
    return min(state.resident, key=lambda i: (state.last_used.get(i, -1), i))


def chart_policy(state: State, config: Config, need: str) -> str:
    """Belady over the visible chart: evict the resident needed furthest ahead
    (never-on-chart counts as furthest); ties go to the larger cache, then id."""
    chart = state.chart(config)

    def nxt(i):
        try:
            return chart.index(i)
        except ValueError:
            return len(chart) + 1
    return max(state.resident, key=lambda i: (nxt(i), config.cost(i), i))


def step(state: State, config: Config, policy) -> State:
    if state.outcome != RUNNING:
        raise CacheError("game is over")
    need = state.reqs[state.tide]
    state.events = []
    if need in state.resident:
        state.hits += 1
        state.events.append("hit")
    else:
        state.misses += 1
        state.stall_kib += config.cost(need)
        state.events.append("miss")
        while used_kib(state, config) + config.cost(need) > config.capacity_kib:
            victim = policy(state, config, need)
            if victim not in state.resident:
                raise CacheError(f"policy evicted non-resident {victim!r}")
            state.resident.remove(victim)
            state.evictions += 1
            state.events.append("evict")
            state.log.append(f"t{state.tide + 1} evict {victim}")
        state.resident.append(need)
        state.log.append(f"t{state.tide + 1} miss {need} stall={state.stall_kib}")
    state.last_used[need] = state.tide
    state.tide += 1
    if state.stall_kib > config.stall_budget_kib:
        state.outcome, state.fail_reason = FAILED, FAIL_STALL
        state.events.append("fail")
        state.log.append(f"t{state.tide} FAIL stall={state.stall_kib}")
    elif state.tide >= config.tides:
        state.outcome = WON
        state.events.append("win")
        state.log.append(f"t{state.tide} WIN stall={state.stall_kib} hits={state.hits}")
    return state


def simulate(config: Config, policy=None) -> State:
    st = new_state(config)
    policy = policy or chart_policy
    while st.outcome == RUNNING:
        step(st, config, policy)
    return st


def config_from_byte_spring(spring: dict, tides: int, chart_len: int, stall_budget_kib: int,
                            npc: dict, seed: int = 1) -> dict:
    """G39 tie-in: Byte Spring islands become cacheable islands (cost_kib, weight =
    priority + 1) and the pool capacity is the Byte Spring budget cap minus the keystone
    (home) cache, which never leaves RAM."""
    keystone = spring["keystone"]
    home = next(i for i in spring["islands"] if i["id"] == keystone)
    return {
        "v": 1, "quest": QUEST_ID,
        "pool": {"capacity_kib": int(spring["cistern"]["budget_cap"]) - int(home["cost_kib"]),
                 "tides": tides, "chart_len": chart_len, "stall_budget_kib": stall_budget_kib},
        "islands": [{"id": i["id"], "cost_kib": int(i["cost_kib"]), "weight": int(i["priority"]) + 1}
                    for i in spring["islands"] if i["id"] != keystone],
        "seed": seed, "npc": npc,
    }


def npc_say(state: State, config: Config) -> Tuple[str, str]:
    for k in ("fail", "win", "evict", "miss", "hit", "start"):
        if k in state.events:
            return k, config.lines[k]
    return "hit", config.lines["hit"]


def receipt(state: State, config: Config) -> dict:
    return {
        "quest": QUEST_ID, "activity": "tide_chart_cache", "island": "disk-saver",
        "outcome": state.outcome, "fail_reason": state.fail_reason,
        "tides": state.tide, "hits": state.hits, "misses": state.misses,
        "evictions": state.evictions, "stall_kib": state.stall_kib,
        "stall_budget_kib": config.stall_budget_kib,
        # score: budget left (permille) only when won
        "score": ((config.stall_budget_kib - state.stall_kib) * 1000) // max(1, config.stall_budget_kib)
        if state.outcome == WON else 0,
    }


def load(path: str) -> Config:
    with open(path, encoding="utf-8") as f:
        return validate(json.load(f))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G70 Tide Chart Cache (offline, seeded)")
    ap.add_argument("config")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--lru", action="store_true", help="evict least recently used (ignore the chart)")
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
    st = simulate(cfg, lru_policy if a.lru else chart_policy)
    if a.trace:
        print("\n".join(st.log))
    print(json.dumps(receipt(st, cfg), sort_keys=True))
    print(f"{cfg.npc_name}: {npc_say(st, cfg)[1]}")
    return 0 if st.outcome == WON else 1


if __name__ == "__main__":
    sys.exit(main())
