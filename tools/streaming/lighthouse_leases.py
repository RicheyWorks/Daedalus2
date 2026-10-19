# SPDX-License-Identifier: MIT
"""G171 Lighthouse Leases (DiskSaver Island, quest q_lighthouse_leases).

Only one lighthouse keeper (the leader) may write the island save log at a
time. The keepers are the G86 Compaction Shoals islands (read-only). The
harbour store grants a lease of `lease` ticks per epoch, then hands the
light to the next keeper. Every keeper's clock drifts by a seeded per-mille
rate, and sometimes a keeper freezes (a stop-the-world pause) between
checking its lease and its write landing. Keeper Ines picks the rule:
  none     no lease: the old keeper keeps writing until news of the new
           keeper reaches it (split brain after the hand-over)
  naive    time lease checked on the keeper's own drifting clock: a slow
           clock writes after the lease really ended
  guard    lease shortened by a drift guard: safe against drift, but a
           pause between check and write still lands a stale write
  fenced   guard + fencing token: each epoch's token rises and the store
           rejects any write whose token is below the highest it accepted
Win: the store never accepts a stale write (a write whose token is below a
token it already accepted). Deterministic and offline.

Science (pinned in tests): drift_bound(L, d) = L - floor(L*(1000-d)/1000)
is the smallest guard that keeps a drift-d keeper inside its lease (equals
a brute-force scan); with no pauses and guard >= drift_bound the overlap is
zero; fencing rejects every stale write; the stale count equals a
brute-force oracle over the store log; seeded replays are identical.

Reusable pieces:
  validate(cfg) -> Config ; run(config, mode) -> Result
  drift_bound / local_elapsed / stale_oracle
  islands_from_shoals(shoals_cfg)  tie-in: keepers = G86 islands
  npc_say / receipt (G12-style quest receipt)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

QUEST_ID = "q_lighthouse_leases"
VERSION = 1
MODES = ("none", "naive", "guard", "fenced")
WON, FAILED = "won", "failed"
FAIL_STALE = "stale_write_accepted"
NPC_KEYS = ("start", "handover", "fenced", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "leases", "shoals_data", "seed", "npc"}
L_KEYS = {"lease", "epochs", "write_permille", "max_drift_permille", "pause_permille",
          "max_pause", "news_delay", "guard", "mode"}


class LeaseError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    keepers: Tuple[str, ...]
    lease: int
    epochs: int
    write_permille: int
    max_drift_permille: int
    pause_permille: int
    max_pause: int
    news_delay: int
    guard: int
    mode: str
    seed: int
    npc_name: str
    lines: Dict[str, str]


@dataclass(frozen=True)
class Write:
    land: int
    token: int
    keeper: int
    checked: int


@dataclass
class Result:
    status: str
    reason: Optional[str]
    mode: str
    writes: int
    accepted: int
    rejected: int
    stale_accepted: int
    outside_lease: int
    log: List[Tuple[Write, bool]] = field(default_factory=list, repr=False)


def islands_from_shoals(shoals_cfg) -> List[str]:
    """G86 tie-in: the keepers are the Compaction Shoals island ids, read-only."""
    return [it["id"] for it in shoals_cfg["islands"]]


def _load_shoals(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _int(d, k, lo, hi):
    v = d.get(k)
    if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
        raise LeaseError(f"{k} must be an int in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict) or set(cfg) != TOP_KEYS:
        raise LeaseError(f"top-level keys must be {sorted(TOP_KEYS)}")
    if cfg["v"] != VERSION or cfg["quest"] != QUEST_ID:
        raise LeaseError("wrong version or quest")
    l = cfg["leases"]
    if not isinstance(l, dict) or set(l) != L_KEYS:
        raise LeaseError(f"leases keys must be {sorted(L_KEYS)}")
    if l["mode"] not in MODES:
        raise LeaseError(f"mode must be one of {MODES}")
    lease = _int(l, "lease", 2, 1000)
    npc = cfg["npc"]
    if not isinstance(npc, dict) or set(npc.get("lines", {})) != set(NPC_KEYS) or not npc.get("name"):
        raise LeaseError("npc needs a name and lines " + ",".join(NPC_KEYS))
    keepers = islands_from_shoals(_load_shoals(cfg["shoals_data"]))
    if len(keepers) < 2:
        raise LeaseError("need at least two G86 islands")
    return Config(tuple(keepers), lease, _int(l, "epochs", 1, 10000), _int(l, "write_permille", 1, 1000),
                  _int(l, "max_drift_permille", 0, 500), _int(l, "pause_permille", 0, 1000),
                  _int(l, "max_pause", 0, 1000), _int(l, "news_delay", 0, 1000),
                  _int(l, "guard", 0, lease - 1), l["mode"], _int(cfg, "seed", 0, 2**31 - 1),
                  npc["name"], dict(npc["lines"]))


def local_elapsed(true_elapsed: int, drift: int) -> int:
    """Ticks a keeper's clock shows after true_elapsed ticks at drift per-mille (negative = slow)."""
    return true_elapsed * (1000 + drift) // 1000


def drift_bound(lease: int, drift: int) -> int:
    """Smallest guard g so a keeper with clock drift -drift never writes at true elapsed >= lease."""
    return lease - local_elapsed(lease, -drift)


def stale_oracle(log: List[Tuple[Write, bool]]) -> int:
    """Brute force: accepted writes with some earlier accepted write of a higher token."""
    acc = [w for w, ok in log if ok]
    return sum(1 for i, w in enumerate(acc) if any(p.token > w.token for p in acc[:i]))


def run(c: Config, mode: Optional[str] = None) -> Result:
    mode = mode or c.mode
    rng = random.Random(c.seed)
    n = len(c.keepers)
    drift = [rng.randint(-c.max_drift_permille, c.max_drift_permille) for _ in range(n)]
    guard = c.guard if mode in ("guard", "fenced") else 0
    starts = [0]
    for _ in range(c.epochs):
        starts.append(starts[-1] + c.lease + rng.randrange(2))
    writes: List[Write] = []
    outside = 0
    keeper = 0
    for e in range(c.epochs):
        s, nxt = starts[e], starts[e + 1]
        keeper = (keeper + 1 + rng.randrange(n - 1)) % n if e else rng.randrange(n)
        stop = nxt + c.news_delay if mode == "none" else nxt + c.lease * 2
        for t in range(s, stop):
            if t > s and rng.randrange(1000) >= c.write_permille:
                continue
            if mode != "none" and local_elapsed(t - s, drift[keeper]) >= c.lease - guard:
                break
            pause = 0
            if t > s and c.max_pause and rng.randrange(1000) < c.pause_permille:
                pause = rng.randint(1, c.max_pause)
            w = Write(t + pause, e + 1, keeper, t)
            writes.append(w)
            if w.land >= s + c.lease:
                outside += 1
    writes.sort(key=lambda w: (w.land, w.checked, w.token))
    log: List[Tuple[Write, bool]] = []
    hi = 0
    for w in writes:
        ok = not (mode == "fenced" and w.token < hi)
        if ok:
            hi = max(hi, w.token)
        log.append((w, ok))
    stale = stale_oracle(log) if mode != "fenced" else 0
    acc = sum(1 for _, ok in log if ok)
    status = WON if stale == 0 else FAILED
    return Result(status, None if status == WON else FAIL_STALE, mode, len(writes), acc,
                  len(writes) - acc, stale, outside, log)


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason, "mode": r.mode, "writes": r.writes,
            "accepted": r.accepted, "rejected": r.rejected, "stale_accepted": r.stale_accepted,
            "outside_lease": r.outside_lease, "keepers": len(c.keepers), "seed": c.seed}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--mode", choices=MODES, default=None)
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    r = run(c, a.mode)
    print(npc_say(c, "start"))
    print(json.dumps(receipt(c, r), sort_keys=True))
    print(npc_say(c, "win" if r.status == WON else "fail"))
    return 0 if r.status == WON else 1


if __name__ == "__main__":
    sys.exit(main())
