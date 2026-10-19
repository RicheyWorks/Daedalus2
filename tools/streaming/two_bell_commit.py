# SPDX-License-Identifier: MIT
"""G144 Two-Bell Commit (DiskSaver Island, quest q_two_bell_commit).

Saves move between islands (islands and keys_per_island of G86 Compaction
Shoals, read-only). A move is one transaction with two participants: the
source island must delete the save and the destination island must write it.
Done halfway, a move either duplicates the save (written, never deleted) or
loses it (deleted, never written): a torn move.

Seeded trouble: a participant can refuse (full disk, `refuse_permille`), and
the harbourmaster coordinator can crash while ringing the decision
(`crash_permille`), after only some participants heard it; it comes back
`recover_ticks` later. The keeper picks the protocol:
  one_bell   ring COMMIT straight away; a refusal or a crash tears the move
  two_bell   ring PREPARE, collect votes, then ring the decision; but the
             decision lives only in the coordinator's head, so after a crash
             it presumes abort and tears moves some participant already
             committed
  two_bell_log  two bells with the decision written to the harbour log
             before it is rung; after a crash the log is replayed and every
             participant ends the same way (in-doubt participants hold their
             lock for `recover_ticks`)
Win: no torn move, every save on exactly one island, total lock-hold ticks
within `max_blocked`, and at least `min_committed` moves committed.
Deterministic and offline: integers only, the shared 32-bit LCG.

Reusable pieces:
  validate(cfg) -> Config
  plan(config) -> list of Move(key, src, dst, refuse_src, refuse_dst, crash_after)
  apply_move(state, move, protocol) -> Outcome
  simulate(config, protocol=None) -> Result
  islands_from_shoals(shoals_cfg)  tie-in: islands + keys_per_island = G86
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

QUEST_ID = "q_two_bell_commit"
VERSION = 1
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
PROTOCOLS = ("one_bell", "two_bell", "two_bell_log")
WON, FAILED = "won", "failed"
FAIL_TORN, FAIL_BLOCKED, FAIL_FEW = "torn_move", "blocked_exceeded", "too_few_commits"
COMMITTED, ABORTED, TORN = "committed", "aborted", "torn"
NPC_KEYS = ("start", "bell", "crash", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "harbour", "islands", "seed", "npc"}
H_KEYS = {"keys_per_island", "moves", "refuse_permille", "crash_permille", "recover_ticks",
          "protocol", "max_blocked", "min_committed"}


class CommitError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    keys_per_island: int
    moves: int
    refuse_permille: int
    crash_permille: int
    recover_ticks: int
    protocol: str
    max_blocked: int
    min_committed: int
    islands: Tuple[str, ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise CommitError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise CommitError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise CommitError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise CommitError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise CommitError(f"quest must be {QUEST_ID}")
    h = cfg.get("harbour")
    if not isinstance(h, dict) or set(h) != H_KEYS:
        raise CommitError(f"harbour must have exactly {sorted(H_KEYS)}")
    kpi = _int(h["keys_per_island"], "keys_per_island", 1, 100_000)
    mv = _int(h["moves"], "moves", 1, 1_000_000)
    rp = _int(h["refuse_permille"], "refuse_permille", 0, 1000)
    cp = _int(h["crash_permille"], "crash_permille", 0, 1000)
    rt = _int(h["recover_ticks"], "recover_ticks", 0, 1_000_000)
    if h["protocol"] not in PROTOCOLS:
        raise CommitError(f"protocol must be one of {PROTOCOLS}")
    mb = _int(h["max_blocked"], "max_blocked", 0, 10 ** 12)
    mc = _int(h["min_committed"], "min_committed", 0, mv)
    isl = cfg.get("islands")
    if not isinstance(isl, list) or len(isl) < 2:
        raise CommitError("islands must list at least two islands")
    seen = []
    for it in isl:
        iid = it.get("id") if isinstance(it, dict) else None
        if not isinstance(iid, str) or not iid or set(iid) - ID_CHARS or iid in seen:
            raise CommitError(f"bad or duplicate island id: {iid!r}")
        seen.append(iid)
    seed = _int(cfg.get("seed", 1), "seed", 0, 2 ** 32 - 1)
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or not isinstance(npc.get("name"), str):
        raise CommitError("npc must have a name")
    lines = npc.get("lines")
    if not isinstance(lines, dict) or set(lines) != set(NPC_KEYS):
        raise CommitError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    if not all(isinstance(v, str) and v for v in lines.values()):
        raise CommitError("npc lines must be non-empty strings")
    return Config(kpi, mv, rp, cp, rt, h["protocol"], mb, mc, tuple(seen), seed, npc["name"], dict(lines))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self, n: int) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) % n


@dataclass(frozen=True)
class Move:
    key: str
    src: str
    dst: str
    refuse_src: bool
    refuse_dst: bool
    crash_after: Optional[int]  # participants that heard the decision before the crash (0 or 1); None = no crash


def initial_state(c: Config) -> Dict[str, Set[str]]:
    """key -> set of islands holding it; every save starts on its home island."""
    return {f"{i}:{k:04d}": {i} for i in c.islands for k in range(c.keys_per_island)}


def plan(c: Config) -> List[Move]:
    rng, out = Lcg(c.seed), []
    home = {f"{i}:{k:04d}": i for i in c.islands for k in range(c.keys_per_island)}
    keys = list(home)
    for _ in range(c.moves):
        key = keys[rng.next(len(keys))]
        src = home[key]
        dst = c.islands[(c.islands.index(src) + 1 + rng.next(len(c.islands) - 1)) % len(c.islands)]
        rs = rng.next(1000) < c.refuse_permille
        rd = rng.next(1000) < c.refuse_permille
        crash = rng.next(1000) < c.crash_permille
        heard = rng.next(2)
        out.append(Move(key, src, dst, rs, rd, heard if crash else None))
        home[key] = dst  # planned location if the move commits; a later move of an aborted key is skipped
    return out


@dataclass
class Outcome:
    status: str
    blocked: int


def _commit_part(state, mv: Move, who: str):
    if who == "src":
        state[mv.key].discard(mv.src)
    else:
        state[mv.key].add(mv.dst)


def apply_move(state: Dict[str, Set[str]], mv: Move, protocol: str, recover_ticks: int) -> Outcome:
    if mv.src not in state[mv.key]:
        return Outcome(ABORTED, 0)  # the save is not where the plan expected (an earlier move aborted)
    parts = ("src", "dst")
    refused = {"src": mv.refuse_src, "dst": mv.refuse_dst}
    if protocol == "one_bell":
        heard = parts if mv.crash_after is None else parts[:mv.crash_after]
        done = [p for p in heard if not refused[p]]
        for p in done:
            _commit_part(state, mv, p)
        if len(done) == 2:
            return Outcome(COMMITTED, 0)
        return Outcome(TORN if done else ABORTED, 0)
    if protocol not in ("two_bell", "two_bell_log"):
        raise CommitError(f"unknown protocol {protocol!r}")
    decision = COMMITTED if not (mv.refuse_src or mv.refuse_dst) else ABORTED
    if mv.crash_after is None:
        if decision == COMMITTED:
            for p in parts:
                _commit_part(state, mv, p)
        return Outcome(decision, 0)
    # coordinator crashed while ringing the decision; `crash_after` participants heard it
    heard = parts[:mv.crash_after]
    if decision == COMMITTED:
        for p in heard:
            _commit_part(state, mv, p)
    in_doubt = 2 - len(heard)
    if protocol == "two_bell_log":
        if decision == COMMITTED:
            for p in parts[mv.crash_after:]:
                _commit_part(state, mv, p)
        return Outcome(decision, in_doubt * recover_ticks)
    # no log: recovery presumes abort for the participants that never heard
    if decision == COMMITTED and heard:
        return Outcome(TORN, in_doubt * recover_ticks)
    return Outcome(ABORTED, in_doubt * recover_ticks)


@dataclass
class Result:
    status: str
    reason: Optional[str]
    moves: int
    committed: int
    aborted: int
    torn: int
    blocked: int
    lost_saves: int
    duplicated_saves: int


def simulate(c: Config, protocol: Optional[str] = None) -> Result:
    pol = c.protocol if protocol is None else protocol
    if pol not in PROTOCOLS:
        raise CommitError(f"unknown protocol {pol!r}")
    state = initial_state(c)
    counts = {COMMITTED: 0, ABORTED: 0, TORN: 0}
    blocked = 0
    for mv in plan(c):
        o = apply_move(state, mv, pol, c.recover_ticks)
        counts[o.status] += 1
        blocked += o.blocked
    lost = sum(1 for v in state.values() if not v)
    dup = sum(1 for v in state.values() if len(v) > 1)
    if sum(counts.values()) != c.moves:
        raise AssertionError("a move vanished")
    if counts[TORN] or lost or dup:
        status, reason = FAILED, FAIL_TORN
    elif blocked > c.max_blocked:
        status, reason = FAILED, FAIL_BLOCKED
    elif counts[COMMITTED] < c.min_committed:
        status, reason = FAILED, FAIL_FEW
    else:
        status, reason = WON, None
    return Result(status, reason, c.moves, counts[COMMITTED], counts[ABORTED], counts[TORN], blocked, lost, dup)


def islands_from_shoals(shoals_cfg) -> Tuple[List[dict], int]:
    """G86 tie-in: islands and keys_per_island from Compaction Shoals, read-only."""
    return ([{"id": it["id"]} for it in shoals_cfg["islands"]],
            shoals_cfg["shoals"]["keys_per_island"])


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result, protocol: str) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason, "protocol": protocol,
            "moves": r.moves, "committed": r.committed, "aborted": r.aborted, "torn": r.torn,
            "lost_saves": r.lost_saves, "duplicated_saves": r.duplicated_saves,
            "blocked": r.blocked, "max_blocked": c.max_blocked}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--protocol", choices=PROTOCOLS, default=None, help="commit protocol override")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    pol = c.protocol if a.protocol is None else a.protocol
    r = simulate(c, pol)
    print(npc_say(c, "start"))
    print(json.dumps(receipt(c, r, pol), sort_keys=True))
    print(npc_say(c, "win" if r.status == WON else "fail"))
    return 0 if r.status == WON else 1


if __name__ == "__main__":
    sys.exit(main())
