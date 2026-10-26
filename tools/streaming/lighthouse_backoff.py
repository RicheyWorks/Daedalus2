# SPDX-License-Identifier: MIT
"""G134 Lighthouse Backoff (DiskSaver Island, quest q_lighthouse_backoff).

A storm knocks the archive lighthouse dark. Every island boat carrying a save
write (islands and keys_per_island of G86 Compaction Shoals, read-only; the
first `writes_per_island` keys of each island) is turned away and must try
again later. The lighthouse is dark for `outage` ticks; once lit, its keeper
can berth only `capacity` boats a tick and turns the rest away.

Each turned-away boat waits before its next try, by the keeper's chosen
retry policy (delay d for attempt a, base b, cap c):
  fixed        d = b
  expo         d = min(c, b * 2**a)
  full_jitter  d = 1 + rand(min(c, b * 2**a))
Win: every write berths by tick `deadline` and the total retries stay within
`max_retries`. Fixed retries hammer the dark lighthouse (retry storm);
exponential backoff without jitter keeps the fleet in lockstep, so each
synchronized wave overruns the berths and the last boat docks far too late
(thundering herd); full jitter spreads the fleet and wins. Deterministic and
offline: integers only, the shared 32-bit LCG.

Reusable pieces:
  validate(cfg) -> Config
  delay(policy, attempt, base, cap, rng) -> int
  simulate(config, policy=None) -> Result
  islands_from_shoals(shoals_cfg)  tie-in: islands + keys_per_island = G86
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

QUEST_ID = "q_lighthouse_backoff"
VERSION = 1
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
POLICIES = ("fixed", "expo", "full_jitter")
WON, FAILED = "won", "failed"
FAIL_RETRIES, FAIL_LATE = "retries_exceeded", "deadline_missed"
NPC_KEYS = ("start", "dark", "lit", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "lighthouse", "islands", "seed", "npc"}
L_KEYS = {"keys_per_island", "writes_per_island", "outage", "capacity", "base", "cap",
          "policy", "deadline", "max_retries"}


class LighthouseError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    keys_per_island: int
    writes_per_island: int
    outage: int
    capacity: int
    base: int
    cap: int
    policy: str
    deadline: int
    max_retries: int
    islands: Tuple[str, ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise LighthouseError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise LighthouseError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise LighthouseError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise LighthouseError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise LighthouseError(f"quest must be {QUEST_ID}")
    h = cfg.get("lighthouse")
    if not isinstance(h, dict) or set(h) != L_KEYS:
        raise LighthouseError(f"lighthouse must have exactly {sorted(L_KEYS)}")
    kpi = _int(h["keys_per_island"], "keys_per_island", 1, 100_000)
    wpi = _int(h["writes_per_island"], "writes_per_island", 1, kpi)
    out = _int(h["outage"], "outage", 0, 100_000)
    capy = _int(h["capacity"], "capacity", 1, 100_000)
    base = _int(h["base"], "base", 1, 10_000)
    cap = _int(h["cap"], "cap", base, 1_000_000)
    if h["policy"] not in POLICIES:
        raise LighthouseError(f"policy must be one of {POLICIES}")
    dl = _int(h["deadline"], "deadline", 1, 10_000_000)
    mr = _int(h["max_retries"], "max_retries", 0, 100_000_000)
    isl = cfg.get("islands")
    if not isinstance(isl, list) or not isl:
        raise LighthouseError("islands must be a non-empty list")
    seen = []
    for it in isl:
        iid = it.get("id") if isinstance(it, dict) else None
        if not isinstance(iid, str) or not iid or set(iid) - ID_CHARS or iid in seen:
            raise LighthouseError(f"bad or duplicate island id: {iid!r}")
        seen.append(iid)
    seed = _int(cfg.get("seed", 1), "seed", 0, 2 ** 32 - 1)
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or not isinstance(npc.get("name"), str):
        raise LighthouseError("npc must have a name")
    lines = npc.get("lines")
    if not isinstance(lines, dict) or set(lines) != set(NPC_KEYS):
        raise LighthouseError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    if not all(isinstance(v, str) and v for v in lines.values()):
        raise LighthouseError("npc lines must be non-empty strings")
    return Config(kpi, wpi, out, capy, base, cap, h["policy"], dl, mr, tuple(seen), seed,
                  npc["name"], dict(lines))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self, n: int) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) % n


def delay(policy: str, attempt: int, base: int, cap: int, rng: Lcg) -> int:
    """Ticks to wait after failed attempt number `attempt` (0-based)."""
    if policy == "fixed":
        return base
    span = min(cap, base << min(attempt, 40))
    if policy == "expo":
        return span
    if policy == "full_jitter":
        return 1 + rng.next(span)
    raise LighthouseError(f"unknown policy {policy!r}")


def boats(c: Config) -> List[str]:
    return [f"{i}:{k:04d}" for i in c.islands for k in range(c.writes_per_island)]


@dataclass
class Result:
    status: str
    reason: Optional[str]
    writes: int
    berthed: int
    retries: int
    last_berth: int
    peak_wave: int


def simulate(c: Config, policy: Optional[str] = None) -> Result:
    pol = c.policy if policy is None else policy
    if pol not in POLICIES:
        raise LighthouseError(f"unknown policy {pol!r}")
    rng = Lcg(c.seed)
    fleet = boats(c)
    due: Dict[int, List[Tuple[str, int]]] = {0: [(k, 0) for k in fleet]}
    berthed = retries = last = peak = 0
    stop = c.deadline + c.cap + 1  # nothing berthing after this matters
    t = 0
    while due and t <= stop:
        wave = due.pop(t, [])
        if wave:
            peak = max(peak, len(wave))
            ok = 0 if t < c.outage else min(c.capacity, len(wave))
            for _ in wave[:ok]:
                berthed += 1
                last = t
            for key, a in wave[ok:]:
                retries += 1
                due.setdefault(t + delay(pol, a, c.base, c.cap, rng), []).append((key, a + 1))
        t += 1
    if berthed + sum(len(w) for w in due.values()) != len(fleet):
        raise AssertionError("a boat vanished")
    if berthed < len(fleet) or last > c.deadline:
        status, reason = FAILED, FAIL_LATE
    elif retries > c.max_retries:
        status, reason = FAILED, FAIL_RETRIES
    else:
        status, reason = WON, None
    return Result(status, reason, len(fleet), berthed, retries, last, peak)


def islands_from_shoals(shoals_cfg) -> Tuple[List[dict], int]:
    """G86 tie-in: islands and keys_per_island from Compaction Shoals, read-only."""
    return ([{"id": it["id"]} for it in shoals_cfg["islands"]],
            shoals_cfg["shoals"]["keys_per_island"])


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result, policy: str) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason, "policy": policy,
            "writes": r.writes, "berthed": r.berthed, "retries": r.retries,
            "max_retries": c.max_retries, "last_berth": r.last_berth, "deadline": c.deadline,
            "peak_wave": r.peak_wave}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--policy", choices=POLICIES, default=None, help="retry policy override")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    pol = c.policy if a.policy is None else a.policy
    r = simulate(c, pol)
    print(npc_say(c, "start"))
    print(json.dumps(receipt(c, r, pol), sort_keys=True))
    print(npc_say(c, "win" if r.status == WON else "fail"))
    return 0 if r.status == WON else 1


if __name__ == "__main__":
    sys.exit(main())
