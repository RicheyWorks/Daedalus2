# SPDX-License-Identifier: MIT
"""G120 Garbage Gulls (DiskSaver Island, quest q_garbage_gulls).

The island heap starts with every save (islands and keys_per_island from
G86 Compaction Shoals, read-only); each island is a root holding its saves,
and every save carries `fragments_per_save` fragments that link back to it,
so every save and its fragments form a loop. Every window storms cut
`replaced_per_window` saves loose from their islands and the tide washes in
new ones: each cut loop drifts where no island can reach it.

The heap holds at most `heap_cap` objects. The gulls can sweep: a
mark-and-sweep pass marks every reachable object and sweeps the whole heap,
costing (marked + heap size) work from a season `work_budget`. The keeper
picks how often the gulls sweep (`sweep_every` windows).

Win: the heap never exceeds `heap_cap`, total sweep work stays within
`work_budget`, and no reachable object is ever freed (checked every sweep).
A tuned sweep interval wins. Never sweeping overflows; sweeping every window
burns the work budget; reference counting is cheap but leaks every stranded
loop until the heap overflows. Deterministic and offline: integers only, the
shared 32-bit LCG.

Reusable pieces:
  validate(cfg) -> Config
  Heap: alloc / link / unlink / reachable / mark_sweep / refcount_collect
  simulate(config, sweep_every=None, refcount=False) -> Result
  islands_from_shoals(shoals_cfg)  tie-in: islands + keys_per_island = G86
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

QUEST_ID = "q_garbage_gulls"
VERSION = 1
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
WON, FAILED = "won", "failed"
FAIL_HEAP, FAIL_WORK = "heap_overflow", "work_exceeded"
NPC_KEYS = ("start", "storm", "sweep", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "gulls", "islands", "seed", "npc"}
G_KEYS = {"windows", "keys_per_island", "fragments_per_save", "replaced_per_window",
          "heap_cap", "work_budget", "sweep_every"}


class GullError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    windows: int
    keys_per_island: int
    fragments_per_save: int
    replaced_per_window: int
    heap_cap: int
    work_budget: int
    sweep_every: int
    islands: Tuple[str, ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise GullError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise GullError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise GullError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise GullError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise GullError(f"quest must be {QUEST_ID}")
    g = cfg.get("gulls")
    if not isinstance(g, dict) or set(g) != G_KEYS:
        raise GullError(f"gulls must have exactly {sorted(G_KEYS)}")
    w = _int(g["windows"], "windows", 1, 10_000)
    kpi = _int(g["keys_per_island"], "keys_per_island", 1, 100_000)
    al = _int(g["fragments_per_save"], "fragments_per_save", 0, 100)
    cu = _int(g["replaced_per_window"], "replaced_per_window", 0, 100_000)
    hc = _int(g["heap_cap"], "heap_cap", 1, 10 ** 8)
    wb = _int(g["work_budget"], "work_budget", 0, 10 ** 10)
    se = _int(g["sweep_every"], "sweep_every", 0, 10_000)
    isl = cfg.get("islands")
    if not isinstance(isl, list) or not isl:
        raise GullError("islands must be a non-empty list")
    seen = []
    for it in isl:
        iid = it.get("id") if isinstance(it, dict) else None
        if not isinstance(iid, str) or not iid or set(iid) - ID_CHARS or iid in seen:
            raise GullError(f"bad or duplicate island id: {iid!r}")
        seen.append(iid)
    seed = _int(cfg.get("seed", 1), "seed", 0, 2 ** 32 - 1)
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or not isinstance(npc.get("name"), str):
        raise GullError("npc must have a name")
    lines = npc.get("lines")
    if not isinstance(lines, dict) or set(lines) != set(NPC_KEYS):
        raise GullError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    if not all(isinstance(v, str) and v for v in lines.values()):
        raise GullError("npc lines must be non-empty strings")
    return Config(w, kpi, al, cu, hc, wb, se, tuple(seen), seed, npc["name"], dict(lines))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self, n: int) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) % n


class Heap:
    """Objects are ints; roots are strings (island ids). Edges are ordered lists."""

    def __init__(self):
        self.edges: Dict[object, List[int]] = {}
        self.objects: Set[int] = set()
        self.rc: Dict[int, int] = {}
        self._next = 0

    def add_root(self, root: str) -> None:
        self.edges.setdefault(root, [])

    def alloc(self) -> int:
        o = self._next
        self._next += 1
        self.objects.add(o)
        self.edges[o] = []
        self.rc[o] = 0
        return o

    def link(self, src, dst: int) -> None:
        self.edges[src].append(dst)
        self.rc[dst] += 1

    def unlink(self, src, idx: int) -> int:
        dst = self.edges[src].pop(idx)
        self.rc[dst] -= 1
        return dst

    def roots(self) -> List[str]:
        return [r for r in self.edges if isinstance(r, str)]

    def reachable(self) -> Set[int]:
        seen: Set[int] = set()
        stack = [d for r in self.roots() for d in self.edges[r]]
        while stack:
            o = stack.pop()
            if o in seen:
                continue
            seen.add(o)
            stack.extend(self.edges[o])
        return seen

    def _free(self, o: int) -> None:
        for d in self.edges.pop(o):
            if d in self.rc:
                self.rc[d] -= 1
        self.objects.discard(o)
        del self.rc[o]

    def mark_sweep(self) -> int:
        """Free every unreachable object; returns work = marked + heap size."""
        live = self.reachable()
        work = len(live) + len(self.objects)
        for o in sorted(self.objects - live):
            self._free(o)
        return work

    def refcount_collect(self, dropped: int) -> None:
        """Cascade-free objects whose count hit zero (cycles are never freed)."""
        stack = [dropped]
        while stack:
            o = stack.pop()
            if o in self.rc and self.rc[o] == 0:
                kids = list(self.edges[o])
                self._free(o)
                stack.extend(kids)


@dataclass
class Result:
    status: str
    reason: Optional[str]
    windows_ok: int
    peak_heap: int
    work: int
    sweeps: int
    freed: int


def simulate(c: Config, sweep_every: Optional[int] = None, refcount: bool = False) -> Result:
    se = c.sweep_every if sweep_every is None else sweep_every
    rng, heap = Lcg(c.seed), Heap()

    def wash_in(root: str) -> None:
        save = heap.alloc()
        heap.link(root, save)
        for _ in range(c.fragments_per_save):  # fragments tangle back: a loop
            f = heap.alloc()
            heap.link(save, f)
            heap.link(f, save)

    for isl in c.islands:
        heap.add_root(isl)
        for _ in range(c.keys_per_island):
            wash_in(isl)
    ok = peak = work = sweeps = freed = 0
    for w in range(1, c.windows + 1):
        for _ in range(c.replaced_per_window):  # storms cut a save loose, tide brings a new one
            isl = c.islands[rng.next(len(c.islands))]
            dst = heap.unlink(isl, rng.next(len(heap.edges[isl])))
            if refcount:
                before = len(heap.objects)
                heap.refcount_collect(dst)
                freed += before - len(heap.objects)
            wash_in(isl)
        if not refcount and se and w % se == 0:
            before_live = heap.reachable()
            before = len(heap.objects)
            work += heap.mark_sweep()
            sweeps += 1
            freed += before - len(heap.objects)
            if not before_live <= heap.objects:
                raise AssertionError("a reachable save was freed")
        peak = max(peak, len(heap.objects))
        ok += len(heap.objects) <= c.heap_cap
    if peak > c.heap_cap:
        status, reason = FAILED, FAIL_HEAP
    elif work > c.work_budget:
        status, reason = FAILED, FAIL_WORK
    else:
        status, reason = WON, None
    return Result(status, reason, ok, peak, work, sweeps, freed)


def islands_from_shoals(shoals_cfg) -> Tuple[List[dict], int]:
    """G86 tie-in: islands and keys_per_island from Compaction Shoals, read-only."""
    return ([{"id": it["id"]} for it in shoals_cfg["islands"]],
            shoals_cfg["shoals"]["keys_per_island"])


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result, se: int, refcount: bool) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason,
            "scheme": "refcount" if refcount else f"sweep_every_{se}",
            "windows_ok": r.windows_ok, "windows": c.windows, "peak_heap": r.peak_heap,
            "heap_cap": c.heap_cap, "work": r.work, "work_budget": c.work_budget,
            "sweeps": r.sweeps, "freed": r.freed}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--sweep-every", type=int, default=None, help="windows between sweeps (0 = never)")
    ap.add_argument("--refcount", action="store_true", help="reference counting instead (trap)")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    se = c.sweep_every if a.sweep_every is None else a.sweep_every
    r = simulate(c, se, a.refcount)
    print(npc_say(c, "start"))
    print(json.dumps(receipt(c, r, se, a.refcount), sort_keys=True))
    print(npc_say(c, "win" if r.status == WON else "fail"))
    return 0 if r.status == WON else 1


if __name__ == "__main__":
    sys.exit(main())
