# SPDX-License-Identifier: MIT
"""G39 Byte Spring cistern (DiskSaver Island).

A leaking spring budgets RAM/disk "water" for resident islands against the DSB
streaming budget. Deterministic offline tick sim; integers only.

Units: one water unit == 1 KiB of (ram + disk) cost from a DSB island row.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple


class ByteSpringError(ValueError):
    pass


@dataclass(frozen=True)
class Island:
    """A resident candidate. cost_kib = ram_kib + disk_kib (DSB lore)."""

    id: str
    cost_kib: int
    priority: int = 0  # lower dumps first on overflow


@dataclass
class Cistern:
    capacity: int
    level: int
    spring_fill: int  # added each wet tick
    leak: int  # removed each dry tick
    budget_cap: int  # max resident cost that may stay loaded


@dataclass
class State:
    cistern: Cistern
    residents: List[Island] = field(default_factory=list)
    dry_streak: int = 0
    dumped: List[str] = field(default_factory=list)
    ticks: int = 0
    failed: bool = False
    won: bool = False


def resident_cost(residents: Sequence[Island]) -> int:
    return sum(i.cost_kib for i in residents)


def validate(cfg: dict) -> Tuple[Cistern, List[Island], int, int]:
    """Parse byte-spring-v1 config. Returns (cistern, islands, drought_limit, win_ticks)."""
    if cfg.get("v") != 1:
        raise ByteSpringError("unsupported version")
    c = cfg["cistern"]
    for k in ("capacity", "level", "spring_fill", "leak", "budget_cap"):
        if not isinstance(c.get(k), int) or c[k] < 0:
            raise ByteSpringError(f"bad cistern.{k}")
    if c["level"] > c["capacity"]:
        raise ByteSpringError("level exceeds capacity")
    islands = []
    seen = set()
    for row in cfg.get("islands") or []:
        iid = row.get("id")
        if not isinstance(iid, str) or not iid or iid in seen:
            raise ByteSpringError("bad island id")
        seen.add(iid)
        cost = row.get("cost_kib")
        pri = row.get("priority", 0)
        if not isinstance(cost, int) or cost < 1:
            raise ByteSpringError(f"bad cost for {iid}")
        if not isinstance(pri, int):
            raise ByteSpringError(f"bad priority for {iid}")
        islands.append(Island(iid, cost, pri))
    drought = cfg.get("drought_limit", 3)
    win = cfg.get("win_ticks", 10)
    if not isinstance(drought, int) or drought < 1:
        raise ByteSpringError("bad drought_limit")
    if not isinstance(win, int) or win < 1:
        raise ByteSpringError("bad win_ticks")
    cistern = Cistern(c["capacity"], c["level"], c["spring_fill"], c["leak"], c["budget_cap"])
    return cistern, islands, drought, win


def load_residents(state: State, pool: Sequence[Island], ids: Sequence[str]) -> None:
    by_id = {i.id: i for i in pool}
    for iid in ids:
        if iid not in by_id:
            raise ByteSpringError(f"unknown island {iid}")
        if any(r.id == iid for r in state.residents):
            raise ByteSpringError(f"already resident {iid}")
        state.residents.append(by_id[iid])


def _enforce_budget(state: State) -> None:
    """Dump lowest-priority (then highest cost, then id) until under budget_cap."""
    while resident_cost(state.residents) > state.cistern.budget_cap and state.residents:
        victim = sorted(state.residents, key=lambda i: (i.priority, -i.cost_kib, i.id))[0]
        state.residents.remove(victim)
        state.dumped.append(victim.id)


def tick(state: State, dry: bool, drought_limit: int, win_ticks: int) -> State:
    """Advance one tick. dry=True = no spring fill, only leak."""
    if state.failed or state.won:
        return state
    state.ticks += 1
    c = state.cistern
    if dry:
        c.level = max(0, c.level - c.leak)
        # residents still drink their cost each dry tick
        drink = resident_cost(state.residents)
        c.level = max(0, c.level - drink)
        state.dry_streak += 1
    else:
        c.level = min(c.capacity, c.level + c.spring_fill)
        drink = resident_cost(state.residents)
        c.level = max(0, c.level - drink)
        state.dry_streak = 0
    _enforce_budget(state)
    # drought: cistern empty for drought_limit consecutive dry ticks
    if c.level == 0 and state.dry_streak >= drought_limit:
        state.failed = True
        return state
    if state.ticks >= win_ticks and not state.failed and c.level > 0:
        state.won = True
    return state


def simulate(
    cfg: dict,
    weather: Sequence[bool],
    start_ids: Optional[Sequence[str]] = None,
) -> State:
    """weather[i] True = dry tick. start_ids load as initial residents."""
    cistern, pool, drought_limit, win_ticks = validate(cfg)
    state = State(cistern=cistern)
    load_residents(state, pool, list(start_ids or cfg.get("start_residents") or []))
    _enforce_budget(state)
    for dry in weather:
        tick(state, bool(dry), drought_limit, win_ticks)
        if state.failed or state.won:
            break
    return state
