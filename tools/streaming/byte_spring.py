# SPDX-License-Identifier: MIT
"""G39 Byte Spring cistern (DiskSaver Island, quest q_byte_spring).

A leaking spring budgets RAM/disk "water" for resident islands against the DSB 1
streaming budget (ADR-063). Each tick the resident islands drink their cost from
the cistern; wet ticks refill it from the spring, dry ticks only leak. If the
resident set costs more than the streaming budget cap, the lowest-priority island
is dumped (unloaded). Keep the cistern from running dry for `drought_limit`
consecutive dry ticks, and keep the keystone island loaded, until `win_ticks`.

Deterministic and offline: integers only, a seeded 32-bit LCG for weather, no
wall clock, no floats, so a Java/C++ port can replay `trace()` line for line.

Reusable pieces (no Unreal, no I/O except the CLI):
  validate(cfg)            -> Config          strict byte-spring-v1 parser
  weather(seed, n, permille) -> [bool]        seeded dry/wet schedule
  new_state(config)        -> State
  tick(state, config, dry, action=None)       one step; player may load/unload
  simulate(cfg, weather, ...) -> State
  islands_from_dsb / pick_residents / config_from_dsb   DSB 1 composition (dsb.py)
  npc_say(state, config)   -> (key, line)     NPC bark for the last tick
  receipt(state, config)   -> dict            quest result (G12-style activity receipt)
Units: one water unit == `unit_kib` KiB of (ram + disk) cost (1 for hand fixtures).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

QUEST_ID = "q_byte_spring"
VERSION = 1
MAX_UNITS = 1_000_000_000
MAX_TICKS = 100_000
MAX_ISLANDS = 20_000
MAX_LINE = 200
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")  # same as DSB 1

RUNNING, WON, FAILED = "running", "won", "failed"
FAIL_DROUGHT, FAIL_KEYSTONE = "drought", "keystone_dumped"
NPC_KEYS = ("start", "wet", "dry", "spill", "low", "dump", "win", "fail_drought", "fail_keystone")
TOP_KEYS = {
    "v", "quest", "lore", "cistern", "islands", "start_residents", "keystone",
    "drought_limit", "win_ticks", "dry_permille", "npc",
}
CISTERN_KEYS = ("capacity", "level", "spring_fill", "leak", "budget_cap")

DEFAULT_NPC = {
    "name": "Spigot",
    "lines": {
        "start": "The Byte Spring runs thin this season. Keep the cistern wet and the caches loaded.",
        "wet": "Spring's flowing. Every kibibyte counts.",
        "dry": "Dry tick. The caches are still drinking.",
        "spill": "Cistern's brimming; the extra runs off into the sea.",
        "low": "Water's low. Unload a cache before the spring gives out.",
        "dump": "Too much streaming at once. The budget spilled and a cache was dumped.",
        "win": "The rains held. DiskSaver Island stays loaded.",
        "fail_drought": "The cistern's dry. The caches go cold.",
        "fail_keystone": "We lost the home cache. The spring has nothing left to guard.",
    },
}


class ByteSpringError(ValueError):
    pass


def _int(v, name, lo, hi):
    # bool is an int subclass in Python; reject it so JSON true/false never sneaks in as 1/0.
    if isinstance(v, bool) or not isinstance(v, int):
        raise ByteSpringError(f"{name} must be an integer")
    if v < lo or v > hi:
        raise ByteSpringError(f"{name} out of range [{lo}, {hi}]")
    return v


def _id(v, name):
    if not isinstance(v, str) or not v or len(v) > 64 or any(c not in ID_CHARS for c in v):
        raise ByteSpringError(f"bad {name}")
    return v


@dataclass(frozen=True)
class Island:
    """A resident candidate. cost = water units drunk per tick (ram + disk)."""

    id: str
    cost: int
    priority: int = 0  # lower dumps first on overflow


@dataclass(frozen=True)
class Config:
    capacity: int
    level: int
    spring_fill: int
    leak: int
    budget_cap: int
    islands: Tuple[Island, ...]
    start_residents: Tuple[str, ...]
    keystone: Optional[str]
    drought_limit: int
    win_ticks: int
    dry_permille: int
    npc_name: str
    npc_lines: Dict[str, str]

    def island(self, iid: str) -> Island:
        for i in self.islands:
            if i.id == iid:
                return i
        raise ByteSpringError(f"unknown island {iid}")


@dataclass
class State:
    level: int
    residents: List[Island] = field(default_factory=list)
    ticks: int = 0
    dry_streak: int = 0
    empty_streak: int = 0
    dumped: List[str] = field(default_factory=list)
    unloaded: List[str] = field(default_factory=list)
    outcome: str = RUNNING
    fail_reason: Optional[str] = None
    last_events: Tuple[str, ...] = ("start",)
    log: List[str] = field(default_factory=list)

    @property
    def won(self) -> bool:
        return self.outcome == WON

    @property
    def failed(self) -> bool:
        return self.outcome == FAILED

    def resident_ids(self) -> List[str]:
        return [r.id for r in self.residents]


def resident_cost(residents: Sequence[Island]) -> int:
    return sum(i.cost for i in residents)


def validate(cfg) -> Config:
    """Strict byte-spring-v1 parser. All or nothing; raises ByteSpringError(why)."""
    if not isinstance(cfg, dict):
        raise ByteSpringError("config must be an object")
    extra = sorted(set(cfg) - TOP_KEYS)
    if extra:
        raise ByteSpringError(f"unknown key {extra[0]}")
    if isinstance(cfg.get("v"), bool) or cfg.get("v") != VERSION:
        raise ByteSpringError("unsupported version")
    if "quest" in cfg and cfg["quest"] != QUEST_ID:
        raise ByteSpringError(f"quest must be {QUEST_ID}")
    c = cfg.get("cistern")
    if not isinstance(c, dict):
        raise ByteSpringError("missing cistern")
    extra = sorted(set(c) - set(CISTERN_KEYS))
    if extra:
        raise ByteSpringError(f"unknown cistern key {extra[0]}")
    capacity = _int(c.get("capacity"), "cistern.capacity", 1, MAX_UNITS)
    level = _int(c.get("level"), "cistern.level", 0, capacity)
    spring_fill = _int(c.get("spring_fill"), "cistern.spring_fill", 0, MAX_UNITS)
    leak = _int(c.get("leak"), "cistern.leak", 0, MAX_UNITS)
    budget_cap = _int(c.get("budget_cap"), "cistern.budget_cap", 0, MAX_UNITS)

    rows = cfg.get("islands")
    if not isinstance(rows, list) or not rows:
        raise ByteSpringError("islands must be a non-empty list")
    if len(rows) > MAX_ISLANDS:
        raise ByteSpringError("too many islands")
    islands, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or set(row) - {"id", "cost_kib", "priority"}:
            raise ByteSpringError("bad island row")
        iid = _id(row.get("id"), "island id")
        if iid in seen:
            raise ByteSpringError(f"duplicate island {iid}")
        seen.add(iid)
        cost = _int(row.get("cost_kib"), f"cost for {iid}", 1, MAX_UNITS)
        pri = _int(row.get("priority", 0), f"priority for {iid}", -1000, 1000)
        islands.append(Island(iid, cost, pri))

    start = cfg.get("start_residents", [])
    if not isinstance(start, list):
        raise ByteSpringError("start_residents must be a list")
    for iid in start:
        if iid not in seen:
            raise ByteSpringError(f"unknown start resident {iid}")
    if len(set(start)) != len(start):
        raise ByteSpringError("duplicate start resident")

    keystone = cfg.get("keystone")
    if keystone is not None:
        _id(keystone, "keystone")
        if keystone not in start:
            raise ByteSpringError("keystone must be a start resident")
        if next(i for i in islands if i.id == keystone).cost > budget_cap:
            raise ByteSpringError("keystone alone exceeds budget_cap")

    drought = _int(cfg.get("drought_limit", 3), "drought_limit", 1, MAX_TICKS)
    win = _int(cfg.get("win_ticks", 10), "win_ticks", 1, MAX_TICKS)
    permille = _int(cfg.get("dry_permille", 500), "dry_permille", 0, 1000)

    npc = cfg.get("npc", DEFAULT_NPC)
    if not isinstance(npc, dict) or not isinstance(npc.get("lines"), dict):
        raise ByteSpringError("bad npc")
    name = npc.get("name")
    if not isinstance(name, str) or not name.strip() or len(name) > 64:
        raise ByteSpringError("bad npc name")
    lines = npc["lines"]
    for k in NPC_KEYS:
        t = lines.get(k)
        if not isinstance(t, str) or not t.strip() or len(t) > MAX_LINE:
            raise ByteSpringError(f"bad npc line {k}")
    if set(lines) - set(NPC_KEYS):
        raise ByteSpringError(f"unknown npc line {sorted(set(lines) - set(NPC_KEYS))[0]}")

    return Config(capacity, level, spring_fill, leak, budget_cap, tuple(islands), tuple(start),
                  keystone, drought, win, permille, name, dict(lines))


# ---------------------------------------------------------------- weather

_LCG_A, _LCG_C, _MASK = 1664525, 1013904223, 0xFFFFFFFF


def weather(seed: int, n: int, dry_permille: int = 500) -> List[bool]:
    """Seeded dry/wet schedule. True = dry. Numerical Recipes LCG, top bits, so ports agree."""
    x = _int(seed, "seed", 0, _MASK)
    _int(n, "ticks", 0, MAX_TICKS)
    _int(dry_permille, "dry_permille", 0, 1000)
    out = []
    for _ in range(n):
        x = (x * _LCG_A + _LCG_C) & _MASK
        out.append(((x >> 16) % 1000) < dry_permille)
    return out


# ---------------------------------------------------------------- sim

def new_state(config: Config) -> State:
    st = State(level=config.level)
    for iid in config.start_residents:
        st.residents.append(config.island(iid))
    events = ["start"]
    if _enforce_budget(st, config):
        events.append("dump")
    st.last_events = tuple(events)
    _check_keystone(st, config)
    return st


def _enforce_budget(state: State, config: Config) -> bool:
    """Dump lowest priority (then highest cost, then id) until within budget_cap."""
    dumped = False
    while state.residents and resident_cost(state.residents) > config.budget_cap:
        victim = min(state.residents, key=lambda i: (i.priority, -i.cost, i.id))
        state.residents.remove(victim)
        state.dumped.append(victim.id)
        dumped = True
    return dumped


def _check_keystone(state: State, config: Config) -> None:
    if config.keystone and config.keystone in state.dumped and state.outcome == RUNNING:
        state.outcome, state.fail_reason = FAILED, FAIL_KEYSTONE


def _apply(state: State, config: Config, action) -> Optional[str]:
    if action is None:
        return None
    if (not isinstance(action, (tuple, list)) or len(action) != 2
            or action[0] not in ("load", "unload") or not isinstance(action[1], str)):
        raise ByteSpringError("action must be ('load'|'unload', island_id)")
    verb, iid = action
    isl = config.island(iid)
    if verb == "load":
        if any(r.id == iid for r in state.residents):
            raise ByteSpringError(f"already resident {iid}")
        state.residents.append(isl)
        return f"load {iid}"
    if not any(r.id == iid for r in state.residents):
        raise ByteSpringError(f"not resident {iid}")
    if iid == config.keystone:
        raise ByteSpringError(f"cannot unload keystone {iid}")
    state.residents = [r for r in state.residents if r.id != iid]
    state.unloaded.append(iid)
    return f"unload {iid}"


def tick(state: State, config: Config, dry: bool, action=None) -> State:
    """Advance one tick. dry=True: leak only; False: spring fills. Finished quests are frozen."""
    if state.outcome != RUNNING:
        return state
    if not isinstance(dry, bool):
        raise ByteSpringError("dry must be a bool")
    did = _apply(state, config, action)  # validate before mutating anything else
    events = []
    before_dump = len(state.dumped)
    if _enforce_budget(state, config):
        events.append("dump")
    state.ticks += 1
    if dry:
        state.level = max(0, state.level - config.leak)
        state.dry_streak += 1
        events.append("dry")
    else:
        filled = state.level + config.spring_fill
        if filled > config.capacity:
            events.append("spill")
        state.level = min(config.capacity, filled)
        state.dry_streak = 0
        events.append("wet")
    state.level = max(0, state.level - resident_cost(state.residents))
    if state.level == 0 and dry:
        state.empty_streak += 1
    elif state.level > 0 or not dry:
        state.empty_streak = 0
    if 0 < state.level * 4 <= config.capacity:
        events.append("low")
    _check_keystone(state, config)
    if state.outcome == RUNNING and state.empty_streak >= config.drought_limit:
        state.outcome, state.fail_reason = FAILED, FAIL_DROUGHT
    if state.outcome == RUNNING and state.ticks >= config.win_ticks and state.level > 0:
        state.outcome = WON
    state.last_events = tuple(events)
    dumps = ",".join(state.dumped[before_dump:]) or "-"
    state.log.append(
        f"t {state.ticks} {'dry' if dry else 'wet'} act {did.replace(' ', ':') if did else '-'} "
        f"level {state.level} res {','.join(state.resident_ids()) or '-'} dump {dumps} "
        f"empty {state.empty_streak} {state.outcome}"
        + (f" {state.fail_reason}" if state.fail_reason else "")
    )
    return state


def simulate(cfg, weather_seq: Sequence[bool], actions: Optional[Dict[int, tuple]] = None,
             start_ids: Optional[Sequence[str]] = None) -> State:
    """Run until won/failed or weather runs out. actions maps 1-based tick -> (verb, id)."""
    if isinstance(cfg, Config):
        config = cfg
    else:
        if start_ids is not None:
            cfg = dict(cfg, start_residents=list(start_ids))
        config = validate(cfg)
    if len(weather_seq) > MAX_TICKS:
        raise ByteSpringError("too many ticks")
    actions = dict(actions or {})
    for k in actions:
        _int(k, "action tick", 1, MAX_TICKS)
    state = new_state(config)
    for n, dry in enumerate(weather_seq, 1):
        if state.outcome != RUNNING:
            break
        tick(state, config, bool(dry), actions.get(n))
    return state


def simulate_seeded(cfg, seed: int, ticks: int, actions=None) -> State:
    config = cfg if isinstance(cfg, Config) else validate(cfg)
    return simulate(config, weather(seed, ticks, config.dry_permille), actions)


def trace(state: State) -> str:
    """Canonical replay text (LF); identical for identical inputs on any port."""
    return "".join(line + "\n" for line in state.log)


# ---------------------------------------------------------------- DSB 1 composition

def _dsb():
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import dsb  # tools/streaming/dsb.py, the DSB 1 Python port

    return dsb


def islands_from_dsb(rows, unit_kib: int = 1024, priorities: Optional[Dict[str, int]] = None) -> List[dict]:
    """DSB 1 rows (dsb.parse) -> byte-spring island rows. cost = ceil((ram+disk)/unit_kib)."""
    _int(unit_kib, "unit_kib", 1, MAX_UNITS)
    priorities = priorities or {}
    out = []
    for iid, _x, _y, ram, disk in rows:
        cost = -(-(ram + disk) // unit_kib)
        out.append({"id": iid, "cost_kib": cost, "priority": priorities.get(iid, 0)})
    return out


def pick_residents(rows, viewer: Tuple[int, int], load_cm: int, unload_cm: int,
                   ram_budget_kib: int, was_resident=()) -> List[str]:
    """Ask the DSB 1 picker (nearest-first under a RAM budget) which islands start resident."""
    flags, _ram, _disk, _n = _dsb().pick(rows, viewer[0], viewer[1], load_cm, unload_cm,
                                         ram_budget_kib, was_resident)
    return [rows[i][0] for i, f in enumerate(flags) if f]


def config_from_dsb(dsb_text: str, base_cfg: dict, viewer: Tuple[int, int], load_cm: int,
                    unload_cm: int, ram_budget_kib: int, unit_kib: int = 1024,
                    priorities: Optional[Dict[str, int]] = None) -> Config:
    """Build a quest from a real DSB 1 manifest: islands from its rows, residents from its picker.
    base_cfg supplies cistern/drought/win/npc; its islands/start_residents are replaced."""
    rows = _dsb().parse(dsb_text)
    cfg = dict(base_cfg)
    cfg["islands"] = islands_from_dsb(rows, unit_kib, priorities)
    cfg["start_residents"] = pick_residents(rows, viewer, load_cm, unload_cm, ram_budget_kib)
    if cfg.get("keystone") not in cfg["start_residents"]:
        cfg.pop("keystone", None)
    return validate(cfg)


# ---------------------------------------------------------------- quest / NPC

def npc_say(state: State, config: Config) -> Tuple[str, str]:
    """(key, line) for the NPC to bark after the last tick. End states beat events."""
    if state.outcome == WON:
        key = "win"
    elif state.outcome == FAILED:
        key = "fail_keystone" if state.fail_reason == FAIL_KEYSTONE else "fail_drought"
    else:
        key = next((k for k in ("dump", "low", "spill", "dry", "wet", "start") if k in state.last_events), "start")
    return key, config.npc_lines[key]


def receipt(state: State, config: Config) -> dict:
    """Quest result in the shape of a G12 activity receipt (activity, outcome, score)."""
    return {
        "quest": QUEST_ID,
        "activity": "byte_spring",
        "island": "disk-saver",
        "outcome": state.outcome,
        "fail_reason": state.fail_reason,
        "ticks": state.ticks,
        "level": state.level,
        "capacity": config.capacity,
        "residents": state.resident_ids(),
        "dumped": list(state.dumped),
        "unloaded": list(state.unloaded),
        # score: water kept (permille of capacity) only when won; 0 otherwise
        "score": (state.level * 1000) // config.capacity if state.outcome == WON else 0,
    }


def load(path: str) -> Config:
    with open(path, encoding="utf-8") as f:
        return validate(json.load(f))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G39 Byte Spring cistern (offline, seeded)")
    ap.add_argument("config", help="byte-spring-v1 JSON, e.g. data/islands/disk-saver/byte-spring-v1.json")
    ap.add_argument("--seed", type=int, default=39)
    ap.add_argument("--ticks", type=int, default=None, help="weather length (default win_ticks*2)")
    a = ap.parse_args(argv)
    try:
        config = load(a.config)
        st = simulate_seeded(config, a.seed, a.ticks if a.ticks is not None else config.win_ticks * 2)
    except (ByteSpringError, OSError, json.JSONDecodeError) as e:
        print(f"byte_spring: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(trace(st))
    print(f"{config.npc_name}: {npc_say(st, config)[1]}")
    print(json.dumps(receipt(st, config), sort_keys=True))
    return 0 if st.outcome == WON else 1


if __name__ == "__main__":
    sys.exit(main())
