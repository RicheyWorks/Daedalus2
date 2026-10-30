# SPDX-License-Identifier: MIT
"""G179 Bottle Census (DiskSaver Island, quest q_bottle_census).

The G86 Compaction Shoals islands (read-only) hold save credits (weight x
`credits_per_weight`) and keep passing them to each other in bottles over
one sea lane per ordered pair of islands. A bottle sails for a seeded 1 ..
`max_delay` ticks; FIFO lanes never let a later bottle overtake an earlier
one. Credits are never made or lost, so the true total never changes.
Harbourmaster Tilde must count every credit while the bottles keep sailing:
  local    each island counts its own balance at tick `start` + a seeded
           clock skew (0 .. `max_skew`); bottles at sea are not counted, and a
           bottle sent after the sender counted but received before the
           receiver counted is counted twice
  sync     every island counts at tick `start` exactly; bottles at sea are missed
  marker   Chandy-Lamport: the initiator counts at `start` and sends a marker
           down every outgoing lane; an island counts on its first marker and
           sends markers on; it then adds every bottle that arrives on a lane
           after it counted and before that lane's marker
Win: the census total equals the true total and the cut is consistent (no
bottle counted as received whose send is not counted). Deterministic, offline.

Science (pinned in tests): the marker census total equals the true total and
its cut is consistent on every seed; the recorded lane bottles equal a
brute-force in-transit oracle (sent inside the cut, received outside it);
the sync shortfall equals the credits at sea at `start`; lanes without FIFO
can break the marker census; seeded replays are identical.

Reusable pieces:
  validate(cfg) -> Config ; run(config, mode, fifo=True) -> Result
  in_transit_oracle / cut_consistent
  islands_from_shoals(shoals_cfg)  tie-in: islands = G86 islands
  npc_say / receipt (G12-style quest receipt)
"""
from __future__ import annotations

import argparse
import heapq
import json
import os
import random
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

QUEST_ID = "q_bottle_census"
VERSION = 1
MODES = ("local", "sync", "marker")
WON, FAILED = "won", "failed"
FAIL_TOTAL, FAIL_CUT = "total_wrong", "inconsistent_cut"
NPC_KEYS = ("start", "marker", "lane", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "census", "shoals_data", "seed", "npc"}
C_KEYS = {"ticks", "credits_per_weight", "send_permille", "max_amount", "max_delay", "start",
          "max_skew", "initiator", "mode"}


class CensusError(ValueError):
    pass


@dataclass(frozen=True)
class Island:
    id: str
    weight: int


@dataclass(frozen=True)
class Config:
    islands: Tuple[Island, ...]
    ticks: int
    credits_per_weight: int
    send_permille: int
    max_amount: int
    max_delay: int
    start: int
    max_skew: int
    initiator: int
    mode: str
    seed: int
    npc_name: str
    lines: Dict[str, str]


@dataclass(frozen=True)
class Bottle:
    seq: int
    src: int
    dst: int
    amount: int
    sent: int      # tick sent
    arrive: int    # tick received
    send_ev: int   # sender's local event index
    recv_ev: int   # receiver's local event index


@dataclass
class Result:
    status: str
    reason: Optional[str]
    mode: str
    fifo: bool
    true_total: int
    census_total: int
    counted_balances: int
    counted_at_sea: int
    bottles: int
    consistent: bool
    cut: Tuple[int, ...] = field(repr=False, default=())          # per-island event index of the count
    lane_bottles: Tuple[int, ...] = field(repr=False, default=())  # seqs recorded as lane state
    log: Tuple[Bottle, ...] = field(repr=False, default=())


def islands_from_shoals(shoals_cfg) -> List[Island]:
    """G86 tie-in: the census islands are the Compaction Shoals islands (id, weight), read-only."""
    return [Island(it["id"], it["weight"]) for it in shoals_cfg["islands"]]


def _load(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _int(d, k, lo, hi):
    v = d.get(k)
    if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
        raise CensusError(f"{k} must be an int in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict) or set(cfg) != TOP_KEYS:
        raise CensusError(f"top-level keys must be {sorted(TOP_KEYS)}")
    if cfg["v"] != VERSION or cfg["quest"] != QUEST_ID:
        raise CensusError("wrong version or quest")
    c = cfg["census"]
    if not isinstance(c, dict) or set(c) != C_KEYS:
        raise CensusError(f"census keys must be {sorted(C_KEYS)}")
    if c["mode"] not in MODES:
        raise CensusError(f"mode must be one of {MODES}")
    npc = cfg["npc"]
    if not isinstance(npc, dict) or set(npc.get("lines", {})) != set(NPC_KEYS) or not npc.get("name"):
        raise CensusError("npc needs a name and lines " + ",".join(NPC_KEYS))
    islands = islands_from_shoals(_load(cfg["shoals_data"]))
    if len(islands) < 2:
        raise CensusError("need at least two G86 islands")
    ticks = _int(c, "ticks", 2, 100000)
    return Config(tuple(islands), ticks, _int(c, "credits_per_weight", 1, 10**6),
                  _int(c, "send_permille", 0, 1000), _int(c, "max_amount", 1, 10**6),
                  _int(c, "max_delay", 1, 1000), _int(c, "start", 0, ticks - 1),
                  _int(c, "max_skew", 0, 1000), _int(c, "initiator", 0, len(islands) - 1), c["mode"],
                  _int(cfg, "seed", 0, 2**31 - 1), npc["name"], dict(npc["lines"]))


def in_transit_oracle(log, cut) -> List[int]:
    """Brute force: bottles whose send is inside the cut and whose receive is outside it."""
    return sorted(b.seq for b in log if b.send_ev < cut[b.src] and b.recv_ev >= cut[b.dst])


def cut_consistent(log, cut) -> bool:
    """No bottle is received inside the cut unless its send is inside the cut too."""
    return all(not (b.recv_ev < cut[b.dst] and b.send_ev >= cut[b.src]) for b in log)


def run(c: Config, mode: Optional[str] = None, fifo: bool = True) -> Result:
    mode = mode or c.mode
    rng = random.Random(c.seed)
    n = len(c.islands)
    bal = [it.weight * c.credits_per_weight for it in c.islands]
    total = sum(bal)
    skew = [rng.randint(0, c.max_skew) for _ in range(n)]
    ev = [0] * n                         # local event counters
    lane_last: Dict[Tuple[int, int], int] = {}
    sea: List[tuple] = []                # heap of (arrive, seq, kind, src, dst, amount, sent, send_ev)
    seq = 0
    done: List[Bottle] = []
    cut: List[Optional[int]] = [None] * n
    counted = [0] * n
    recording: Dict[Tuple[int, int], bool] = {}
    lane_state: List[int] = []
    lane_amt = 0

    def post(t, kind, src, dst, amount):
        nonlocal seq
        arrive = t + rng.randint(1, c.max_delay)
        if fifo:
            arrive = max(arrive, lane_last.get((src, dst), 0))
            lane_last[(src, dst)] = arrive
        heapq.heappush(sea, (arrive, seq, kind, src, dst, amount, t, ev[src]))
        if kind == "b":
            ev[src] += 1
        seq += 1

    def count(i, t):
        cut[i] = ev[i]
        counted[i] = bal[i]
        if mode == "marker":
            for j in range(n):
                if j != i:
                    recording[(j, i)] = True
            for j in range(n):
                if j != i:
                    post(t, "m", i, j, 0)

    t = 0
    while t < c.ticks or (mode == "marker" and any(k == "m" for _, _, k, *_ in sea)):
        if mode == "sync" and t == c.start:
            for i in range(n):
                count(i, t)
        if mode == "local":
            for i in range(n):
                if cut[i] is None and t == c.start + skew[i]:
                    count(i, t)
        if mode == "marker" and t == c.start:
            count(c.initiator, t)
        while sea and sea[0][0] <= t:
            arrive, s, kind, src, dst, amount, sent, sev = heapq.heappop(sea)
            if kind == "m":
                if cut[dst] is None:
                    count(dst, t)
                recording[(src, dst)] = False
                continue
            bal[dst] += amount
            b = Bottle(s, src, dst, amount, sent, arrive, sev, ev[dst])
            ev[dst] += 1
            done.append(b)
            if mode == "marker" and cut[dst] is not None and recording.get((src, dst)):
                lane_state.append(s)
                lane_amt += amount
        if t < c.ticks:
            for i in range(n):
                if bal[i] and rng.randrange(1000) < c.send_permille:
                    amt = rng.randint(1, min(c.max_amount, bal[i]))
                    j = (i + 1 + rng.randrange(n - 1)) % n
                    bal[i] -= amt
                    post(t, "b", i, j, amt)
        t += 1
    # bottles still at sea at the end have no receive event yet: give them one past every cut
    while sea:
        arrive, s, kind, src, dst, amount, sent, sev = heapq.heappop(sea)
        if kind == "b":
            bal[dst] += amount
            done.append(Bottle(s, src, dst, amount, sent, arrive, sev, ev[dst]))
            ev[dst] += 1
    full_cut = tuple(x if x is not None else ev[i] for i, x in enumerate(cut))
    consistent = cut_consistent(done, full_cut)
    census = sum(counted) + lane_amt
    if census != total:
        status, reason = FAILED, FAIL_TOTAL
    elif not consistent:
        status, reason = FAILED, FAIL_CUT
    else:
        status, reason = WON, None
    return Result(status, reason, mode, fifo, total, census, sum(counted), lane_amt, len(done), consistent,
                  full_cut, tuple(sorted(lane_state)), tuple(done))


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason, "mode": r.mode, "fifo": r.fifo,
            "true_total": r.true_total, "census_total": r.census_total, "counted_balances": r.counted_balances,
            "counted_at_sea": r.counted_at_sea, "bottles": r.bottles, "consistent": r.consistent,
            "islands": len(c.islands), "seed": c.seed}


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
