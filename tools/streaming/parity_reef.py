# SPDX-License-Identifier: MIT
"""G67 Parity Reef (DiskSaver Island, quest q_parity_reef).

The island caches are striped across `stones` reef stones. Each stripe holds
stones-1 data blocks plus one XOR parity block, and the parity stone rotates per
stripe (RAID 5 lore). A storm knocks out a whole stone: it is replaced by a
blank stone, and every block on it is unavailable until rebuilt. Each tick the
keeper rebuilds up to `rebuild_per_tick` blocks by XOR of the stripe's other
blocks; every rebuilt block is checked against the original. If any stripe has
two unavailable blocks at once, that data is lost (fail). After a storm the sky
recharges for `calm_ticks` ticks. Survive `season_ticks` ticks.

Deterministic and offline: integers only, the shared 32-bit LCG (G39/G59/G63),
no wall clock, so a Java/C++ port can replay `log` line for line.

Reusable pieces (no Unreal, no I/O except the CLI):
  validate(cfg) -> Config
  new_state(config) -> State
  parity_slot(stripe, stones) / reconstruct(state, stripe, stone)
  tick(state, config, rebuilds)          rebuilds: [(stone, stripe), ...]
  keeper_policy(state, config)           reference: rebuild failed stones, low stripes first
  simulate(config, policy=None) -> State
  stripes_from_defrag(defrag_cfg, stones) G63 tie-in: blocks of the Defrag Tide caches
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

QUEST_ID = "q_parity_reef"
VERSION = 1
MAX_STONES = 64
MAX_STRIPES = 100_000
MAX_TICKS = 100_000
RUNNING, WON, FAILED = "running", "won", "failed"
FAIL_LOST = "data_lost"
NPC_KEYS = ("start", "storm", "rebuild", "healthy", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "reef", "seed", "npc"}
REEF_KEYS = {"stones", "stripes", "rebuild_per_tick", "storm_permille", "calm_ticks", "season_ticks"}


class ReefError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    stones: int
    stripes: int
    rebuild_per_tick: int
    storm_permille: int
    calm_ticks: int
    season_ticks: int
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise ReefError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise ReefError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise ReefError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise ReefError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise ReefError(f"quest must be {QUEST_ID}")
    r = cfg.get("reef")
    if not isinstance(r, dict) or set(r) != REEF_KEYS:
        raise ReefError(f"reef must have exactly {sorted(REEF_KEYS)}")
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or set(npc) != {"name", "lines"} or not isinstance(npc["name"], str) or not npc["name"]:
        raise ReefError("npc must have a name and lines")
    if not isinstance(npc["lines"], dict) or set(npc["lines"]) != set(NPC_KEYS):
        raise ReefError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    for k, v in npc["lines"].items():
        if not isinstance(v, str) or not v or len(v) > 200:
            raise ReefError(f"npc.lines.{k} must be 1..200 chars")
    return Config(
        _int(r["stones"], "reef.stones", 3, MAX_STONES),
        _int(r["stripes"], "reef.stripes", 1, MAX_STRIPES),
        _int(r["rebuild_per_tick"], "reef.rebuild_per_tick", 1, MAX_STRIPES),
        _int(r["storm_permille"], "reef.storm_permille", 0, 1000),
        _int(r["calm_ticks"], "reef.calm_ticks", 0, MAX_TICKS),
        _int(r["season_ticks"], "reef.season_ticks", 1, MAX_TICKS),
        _int(cfg.get("seed", 1), "seed", 0, 2**32 - 1),
        npc["name"], dict(npc["lines"]))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self) -> int:
        self.s = (1664525 * self.s + 1013904223) & 0xFFFFFFFF
        return self.s

    def below(self, n: int) -> int:
        return (self.next() >> 8) % n


def parity_slot(stripe: int, stones: int) -> int:
    """Rotating parity (left-symmetric RAID 5): stripe 0 parity on the last stone."""
    return (stones - 1 - stripe) % stones


@dataclass
class State:
    rng: Lcg
    blocks: List[List[int]]            # [stone][stripe] byte, as written
    truth: List[List[int]]             # original bytes, for rebuild verification
    ok: List[List[bool]]               # [stone][stripe] available
    tick_no: int = 0
    calm_left: int = 0
    storms: int = 0
    rebuilt: int = 0
    outcome: str = RUNNING
    fail_reason: Optional[str] = None
    events: List[str] = field(default_factory=list)
    log: List[str] = field(default_factory=list)

    def missing(self) -> List[Tuple[int, int]]:
        return [(s, j) for s in range(len(self.ok)) for j in range(len(self.ok[s])) if not self.ok[s][j]]


def new_state(config: Config) -> State:
    rng = Lcg(config.seed)
    n, m = config.stones, config.stripes
    blocks = [[0] * m for _ in range(n)]
    for j in range(m):
        p = parity_slot(j, n)
        x = 0
        for s in range(n):
            if s != p:
                blocks[s][j] = rng.next() >> 24
                x ^= blocks[s][j]
        blocks[p][j] = x
    st = State(rng, blocks, [list(r) for r in blocks], [[True] * m for _ in range(n)], events=["start"])
    st.log.append(f"t0 start stones={n} stripes={m}")
    return st


def stripe_xor(state: State, stripe: int) -> int:
    x = 0
    for s in range(len(state.blocks)):
        x ^= state.blocks[s][stripe]
    return x


def reconstruct(state: State, stripe: int, stone: int) -> int:
    """XOR of every other block in the stripe; needs all of them available."""
    x = 0
    for s in range(len(state.blocks)):
        if s == stone:
            continue
        if not state.ok[s][stripe]:
            raise ReefError(f"stripe {stripe} has a second missing block (stone {s})")
        x ^= state.blocks[s][stripe]
    return x


def tick(state: State, config: Config, rebuilds: Sequence[Tuple[int, int]] = ()) -> State:
    """One tick: rebuilds, then maybe a storm, then the loss check, then the season check."""
    if state.outcome != RUNNING:
        raise ReefError("game is over")
    if len(rebuilds) > config.rebuild_per_tick:
        raise ReefError(f"at most {config.rebuild_per_tick} rebuilds per tick")
    state.tick_no += 1
    state.events = []
    for rb in rebuilds:
        if not (isinstance(rb, (tuple, list)) and len(rb) == 2):
            raise ReefError(f"bad rebuild {rb!r}")
        s, j = rb
        if not (isinstance(s, int) and 0 <= s < config.stones and isinstance(j, int) and 0 <= j < config.stripes):
            raise ReefError(f"bad block {rb!r}")
        if state.ok[s][j]:
            raise ReefError(f"block {rb!r} is not missing")
        v = reconstruct(state, j, s)
        if v != state.truth[s][j]:
            raise AssertionError("rebuild verification failed")
        state.blocks[s][j] = v
        state.ok[s][j] = True
        state.rebuilt += 1
    if rebuilds:
        state.events.append("rebuild")
        state.log.append(f"t{state.tick_no} rebuilt {len(rebuilds)} missing={len(state.missing())}")
        if not state.missing():
            state.events.append("healthy")
    if state.calm_left > 0:
        state.calm_left -= 1
    else:
        roll = state.rng.below(1000)
        if roll < config.storm_permille:
            stone = state.rng.below(config.stones)
            for j in range(config.stripes):
                state.blocks[stone][j] = 0
                state.ok[stone][j] = False
            state.storms += 1
            state.calm_left = config.calm_ticks
            state.events.append("storm")
            state.log.append(f"t{state.tick_no} storm stone {stone}")
    for j in range(config.stripes):
        if sum(1 for s in range(config.stones) if not state.ok[s][j]) >= 2:
            state.outcome, state.fail_reason = FAILED, FAIL_LOST
            state.events.append("fail")
            state.log.append(f"t{state.tick_no} FAIL data_lost stripe {j}")
            return state
    if state.tick_no >= config.season_ticks:
        state.outcome = WON
        state.events.append("win")
        state.log.append(f"t{state.tick_no} WIN storms={state.storms} rebuilt={state.rebuilt}")
    return state


def keeper_policy(state: State, config: Config) -> List[Tuple[int, int]]:
    """Reference: rebuild missing blocks in (stone, stripe) order, up to the tick budget."""
    return state.missing()[: config.rebuild_per_tick]


def simulate(config: Config, policy=None) -> State:
    st = new_state(config)
    policy = policy or keeper_policy
    while st.outcome == RUNNING:
        tick(st, config, policy(st, config))
    return st


def stripes_from_defrag(defrag_cfg: dict, stones: int) -> int:
    """G63 tie-in: the reef stores every Defrag Tide cache block once;
    stripes = ceil(total blocks / data blocks per stripe)."""
    _int(stones, "stones", 3, MAX_STONES)
    total = sum(int(f["blocks"]) for f in defrag_cfg["files"])
    return -(-total // (stones - 1))


def npc_say(state: State, config: Config) -> Tuple[str, str]:
    for k in ("fail", "win", "storm", "healthy", "rebuild", "start"):
        if k in state.events:
            return k, config.lines[k]
    return "rebuild", config.lines["rebuild"]


def receipt(state: State, config: Config) -> dict:
    return {
        "quest": QUEST_ID, "activity": "parity_reef", "island": "disk-saver",
        "outcome": state.outcome, "fail_reason": state.fail_reason,
        "ticks": state.tick_no, "storms": state.storms, "rebuilt": state.rebuilt,
        "missing": len(state.missing()),
        # score: storms weathered (x100) only when won
        "score": state.storms * 100 if state.outcome == WON else 0,
    }


def load(path: str) -> Config:
    with open(path, encoding="utf-8") as f:
        return validate(json.load(f))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G67 Parity Reef (offline, seeded)")
    ap.add_argument("config")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--idle", action="store_true", help="never rebuild")
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
