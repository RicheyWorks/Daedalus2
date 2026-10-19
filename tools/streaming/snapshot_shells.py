# SPDX-License-Identifier: MIT
"""G113 Snapshot Shells (DiskSaver Island, quest q_snapshot_shells).

At the end of every window the keeper presses a shell: a snapshot of every
island save (islands and keys_per_island from G86 Compaction Shoals,
read-only). Between windows the islands keep writing. Every so often a
villager botches a save and asks for the island as it was some windows ago
(at most `restore_depth` back); the keeper must hand back that snapshot
exactly.

Shells are copy-on-write: a snapshot shares every block that has not changed
since, so only changed versions cost space. Space = distinct (save, version)
blocks referenced by the live islands or any kept shell, and must stay
within `space_budget`. The keeper picks how many shells to keep.

Win: every window stays within the space budget and every restore request
returns the exact snapshot. Keeping just enough copy-on-write shells wins;
keeping every shell runs out of space, full copies run out of space at once,
and keeping too few (or none) cannot restore. Deterministic and offline:
integers only, the shared 32-bit LCG.

Reusable pieces:
  validate(cfg) -> Config
  ShellStore(keep, full_copy): press(live) / restore(age) / space(live)
  simulate(config, keep=None, full_copy=False) -> Result
  islands_from_shoals(shoals_cfg)  tie-in: islands + keys_per_island = G86
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

QUEST_ID = "q_snapshot_shells"
VERSION = 1
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
WON, FAILED = "won", "failed"
FAIL_SPACE, FAIL_RESTORE = "space_exceeded", "restore_failed"
NPC_KEYS = ("start", "press", "restore", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "shells", "islands", "seed", "npc"}
S_KEYS = {"windows", "keys_per_island", "writes_per_window", "keep", "restore_depth",
          "restore_permille", "space_budget"}


class ShellError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    windows: int
    keys_per_island: int
    writes_per_window: int
    keep: int
    restore_depth: int
    restore_permille: int
    space_budget: int
    islands: Tuple[str, ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise ShellError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise ShellError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise ShellError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise ShellError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise ShellError(f"quest must be {QUEST_ID}")
    s = cfg.get("shells")
    if not isinstance(s, dict) or set(s) != S_KEYS:
        raise ShellError(f"shells must have exactly {sorted(S_KEYS)}")
    w = _int(s["windows"], "windows", 1, 10_000)
    kpi = _int(s["keys_per_island"], "keys_per_island", 1, 100_000)
    wpw = _int(s["writes_per_window"], "writes_per_window", 0, 1_000_000)
    keep = _int(s["keep"], "keep", 0, 10_000)
    rd = _int(s["restore_depth"], "restore_depth", 1, 10_000)
    rp = _int(s["restore_permille"], "restore_permille", 0, 1000)
    sb = _int(s["space_budget"], "space_budget", 1, 10 ** 9)
    isl = cfg.get("islands")
    if not isinstance(isl, list) or not isl:
        raise ShellError("islands must be a non-empty list")
    seen = []
    for it in isl:
        iid = it.get("id") if isinstance(it, dict) else None
        if not isinstance(iid, str) or not iid or set(iid) - ID_CHARS or iid in seen:
            raise ShellError(f"bad or duplicate island id: {iid!r}")
        seen.append(iid)
    seed = _int(cfg.get("seed", 1), "seed", 0, 2 ** 32 - 1)
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or not isinstance(npc.get("name"), str):
        raise ShellError("npc must have a name")
    lines = npc.get("lines")
    if not isinstance(lines, dict) or set(lines) != set(NPC_KEYS):
        raise ShellError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    if not all(isinstance(v, str) and v for v in lines.values()):
        raise ShellError("npc lines must be non-empty strings")
    return Config(w, kpi, wpw, keep, rd, rp, sb, tuple(seen), seed, npc["name"], dict(lines))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self, n: int) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) % n


class ShellStore:
    """Keeps the newest `keep` shells (keep < 0: every shell)."""

    def __init__(self, keep: int, full_copy: bool = False):
        self.keep, self.full_copy = keep, full_copy
        self.shells: List[Dict[str, int]] = []  # oldest first

    def press(self, live: Dict[str, int]) -> None:
        if self.keep == 0:
            return
        self.shells.append(dict(live))
        if self.keep > 0 and len(self.shells) > self.keep:
            self.shells.pop(0)

    def restore(self, age: int) -> Optional[Dict[str, int]]:
        """age 1 = the newest shell."""
        if age < 1 or age > len(self.shells):
            return None
        return dict(self.shells[-age])

    def space(self, live: Dict[str, int]) -> int:
        if self.full_copy:
            return len(live) + sum(len(s) for s in self.shells)
        blocks = set(live.items())
        for s in self.shells:
            blocks.update(s.items())
        return len(blocks)


def keys_for(c: Config) -> List[str]:
    return [f"{i}:{k:04d}" for i in c.islands for k in range(c.keys_per_island)]


@dataclass
class Result:
    status: str
    reason: Optional[str]
    windows_ok: int
    worst_space: int
    restores: int
    restores_ok: int


def simulate(c: Config, keep: Optional[int] = None, full_copy: bool = False) -> Result:
    keep = c.keep if keep is None else keep
    rng, keys = Lcg(c.seed), keys_for(c)
    live = {k: 0 for k in keys}
    store = ShellStore(keep, full_copy)
    truth: List[Dict[str, int]] = []  # every snapshot ever pressed, for checking
    ok = worst = asked = good = 0
    space_fail = False
    for _ in range(c.windows):
        for _ in range(c.writes_per_window):
            k = keys[rng.next(len(keys))]
            live[k] += 1
        store.press(live)
        truth.append(dict(live))
        sp = store.space(live)
        worst = max(worst, sp)
        w_ok = sp <= c.space_budget
        space_fail |= not w_ok
        if rng.next(1000) < c.restore_permille:
            age = 1 + rng.next(min(c.restore_depth, len(truth)))
            asked += 1
            got = store.restore(age)
            if got is not None and got == truth[-age]:
                good += 1
            else:
                w_ok = False
        ok += w_ok
    if ok == c.windows:
        status, reason = WON, None
    else:
        status, reason = FAILED, FAIL_SPACE if space_fail else FAIL_RESTORE
    return Result(status, reason, ok, worst, asked, good)


def islands_from_shoals(shoals_cfg) -> Tuple[List[dict], int]:
    """G86 tie-in: islands and keys_per_island from Compaction Shoals, read-only."""
    return ([{"id": it["id"]} for it in shoals_cfg["islands"]],
            shoals_cfg["shoals"]["keys_per_island"])


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result, keep: int, full_copy: bool) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason, "keep": keep,
            "full_copy": full_copy, "windows_ok": r.windows_ok, "windows": c.windows,
            "worst_space": r.worst_space, "space_budget": c.space_budget,
            "restores": r.restores, "restores_ok": r.restores_ok}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--keep", type=int, default=None, help="shells kept (-1 = all, 0 = none)")
    ap.add_argument("--full-copy", action="store_true", help="copy every block per shell (trap)")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    keep = c.keep if a.keep is None else a.keep
    r = simulate(c, keep, a.full_copy)
    print(npc_say(c, "start"))
    print(json.dumps(receipt(c, r, keep, a.full_copy), sort_keys=True))
    print(npc_say(c, "win" if r.status == WON else "fail"))
    return 0 if r.status == WON else 1


if __name__ == "__main__":
    sys.exit(main())
