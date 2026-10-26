# SPDX-License-Identifier: MIT
"""G79 Journal Tide (DiskSaver Island, quest q_journal_tide).

Island saves reach the Reef through a write-ahead journal. Each save is
appended to an in-memory buffer; a commit flushes the buffer to the journal as
checksummed records (one IO each commit). A storm surge (power loss) can strike
after any save: every uncommitted save is lost. A surge can also hit in the
middle of a commit, leaving a torn record; recovery replays records in order,
verifying each CRC32, and stops at the first bad one. The keeper chooses when
to commit: commits cost from a fixed `io_budget`, and the season is lost if
more than `max_lost` saves are lost overall.

Recovery must rebuild exactly the state of the committed saves; tests prove it.

Deterministic and offline: integers only, the shared 32-bit LCG, zlib.crc32.

Reusable pieces:
  validate(cfg) -> Config
  record(seq, island, value) / parse(line) -> tuple | None
  recover(journal_lines) -> (state dict, good_records)
  new_state(config) / step(state, config, commit)
  every_k(k) / paced_policy / end_only_policy
  simulate(config, policy=None) -> State
  islands_from_coral(coral_cfg)  tie-in: save weights = G78 Coral Wear islands
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
import zlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

QUEST_ID = "q_journal_tide"
VERSION = 1
MAX_OPS = 1_000_000
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
RUNNING, WON, FAILED = "running", "won", "failed"
FAIL_LOST = "too_many_lost"
NPC_KEYS = ("start", "save", "commit", "surge", "torn", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "journal", "islands", "seed", "npc"}
JOURNAL_KEYS = {"saves", "io_budget", "max_lost", "surge_permille", "torn_permille"}


class JournalError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    saves: int
    io_budget: int
    max_lost: int
    surge_permille: int
    torn_permille: int
    islands: Tuple[Tuple[str, int], ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise JournalError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise JournalError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise JournalError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise JournalError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise JournalError(f"quest must be {QUEST_ID}")
    j = cfg.get("journal")
    if not isinstance(j, dict) or set(j) != JOURNAL_KEYS:
        raise JournalError(f"journal must have exactly {sorted(JOURNAL_KEYS)}")
    raw = cfg.get("islands")
    if not isinstance(raw, list) or not raw:
        raise JournalError("islands must be a non-empty list")
    isl, seen = [], set()
    for n, r in enumerate(raw):
        if not isinstance(r, dict) or set(r) != {"id", "weight"}:
            raise JournalError(f"islands[{n}] must have exactly id and weight")
        iid = r["id"]
        if not isinstance(iid, str) or not iid or len(iid) > 64 or set(iid) - ID_CHARS:
            raise JournalError(f"islands[{n}].id must be 1..64 chars of [A-Za-z0-9_]")
        if iid in seen:
            raise JournalError(f"duplicate island {iid}")
        seen.add(iid)
        isl.append((iid, _int(r["weight"], f"islands[{n}].weight", 1, 1000)))
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or set(npc) != {"name", "lines"} or not isinstance(npc["name"], str) or not npc["name"]:
        raise JournalError("npc must have a name and lines")
    if not isinstance(npc["lines"], dict) or set(npc["lines"]) != set(NPC_KEYS):
        raise JournalError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    for k, v in npc["lines"].items():
        if not isinstance(v, str) or not v or len(v) > 200:
            raise JournalError(f"npc.lines.{k} must be 1..200 chars")
    saves = _int(j["saves"], "journal.saves", 1, MAX_OPS)
    return Config(saves, _int(j["io_budget"], "journal.io_budget", 1, saves),
                  _int(j["max_lost"], "journal.max_lost", 0, saves),
                  _int(j["surge_permille"], "journal.surge_permille", 0, 1000),
                  _int(j["torn_permille"], "journal.torn_permille", 0, 1000),
                  tuple(isl), _int(cfg.get("seed", 1), "seed", 0, 2**32 - 1), npc["name"], dict(npc["lines"]))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self) -> int:
        self.s = (1664525 * self.s + 1013904223) & 0xFFFFFFFF
        return self.s

    def below(self, n: int) -> int:
        return (self.next() >> 8) % n


def record(seq: int, island: str, value: int) -> str:
    body = f"{seq}|{island}|{value}"
    return f"{body}|{zlib.crc32(body.encode('utf-8')):08x}"


def parse(line: str) -> Optional[Tuple[int, str, int]]:
    parts = line.split("|")
    if len(parts) != 4:
        return None
    body = "|".join(parts[:3])
    if format(zlib.crc32(body.encode("utf-8")), "08x") != parts[3]:
        return None
    try:
        return int(parts[0]), parts[1], int(parts[2])
    except ValueError:
        return None


def recover(journal: List[str]) -> Tuple[Dict[str, int], int]:
    """Replay records in order; stop at the first torn/corrupt or out-of-order record."""
    state: Dict[str, int] = {}
    good, last = 0, 0
    for line in journal:
        rec = parse(line)
        if rec is None or rec[0] != last + 1:
            break
        state[rec[1]] = rec[2]
        last = rec[0]
        good += 1
    return state, good


@dataclass
class State:
    rng: Lcg
    journal: List[str] = field(default_factory=list)
    buffer: List[Tuple[int, str, int]] = field(default_factory=list)
    truth: Dict[str, int] = field(default_factory=dict)      # state of durable saves
    seq: int = 0
    saves_done: int = 0
    commits: int = 0
    lost: int = 0
    surges: int = 0
    torn: int = 0
    outcome: str = RUNNING
    fail_reason: Optional[str] = None
    events: List[str] = field(default_factory=list)
    log: List[str] = field(default_factory=list)


def new_state(config: Config) -> State:
    st = State(Lcg(config.seed), events=["start"])
    st.log.append(f"t0 start saves={config.saves} io_budget={config.io_budget}")
    return st


def _draw(state: State, config: Config) -> str:
    total = sum(w for _, w in config.islands)
    r = state.rng.below(total)
    for iid, w in config.islands:
        if r < w:
            return iid
        r -= w
    raise AssertionError


def _surge(state: State, reason: str):
    state.lost += len(state.buffer)
    state.surges += 1
    state.log.append(f"t{state.saves_done} surge ({reason}) lost {len(state.buffer)}")
    state.buffer = []
    # Recovery: rebuild from the journal and drop the torn tail on disk.
    rebuilt, good = recover(state.journal)
    if good < len(state.journal):
        state.journal = state.journal[:good]
    state.seq = good
    if rebuilt != state.truth:
        raise AssertionError("recovery diverged from durable saves")
    state.events.append("surge")


def step(state: State, config: Config, commit: bool) -> State:
    """One save: append to the buffer, maybe a surge, then optionally commit."""
    if state.outcome != RUNNING:
        raise JournalError("game is over")
    state.events = []
    state.saves_done += 1
    island = _draw(state, config)
    value = state.rng.below(1 << 16)
    state.buffer.append((0, island, value))
    state.events.append("save")
    if state.rng.below(1000) < config.surge_permille:
        _surge(state, "after save")
    elif commit and state.buffer:
        if state.commits >= config.io_budget:
            raise JournalError("io budget spent")
        state.commits += 1
        torn_at = None
        if state.rng.below(1000) < config.torn_permille:
            torn_at = state.rng.below(len(state.buffer))
        for k, (_, isl, val) in enumerate(state.buffer):
            line = record(state.seq + 1, isl, val)
            if k == torn_at:
                state.journal.append(line[: len(line) // 2])   # torn write
                state.torn += 1
                state.events.append("torn")
                state.buffer = state.buffer[k:]
                _surge(state, "mid-commit")
                break
            state.journal.append(line)
            state.seq += 1
            state.truth[isl] = val
        else:
            state.buffer = []
            state.events.append("commit")
            state.log.append(f"t{state.saves_done} commit seq={state.seq}")
    if state.lost > config.max_lost:
        state.outcome, state.fail_reason = FAILED, FAIL_LOST
        state.events.append("fail")
        state.log.append(f"t{state.saves_done} FAIL lost={state.lost}")
    elif state.saves_done >= config.saves:
        if state.buffer:
            if state.commits < config.io_budget:
                state.commits += 1
                for _, isl, val in state.buffer:
                    state.journal.append(record(state.seq + 1, isl, val))
                    state.seq += 1
                    state.truth[isl] = val
                state.buffer = []
            else:
                state.lost += len(state.buffer)
                state.buffer = []
        if state.lost > config.max_lost:
            state.outcome, state.fail_reason = FAILED, FAIL_LOST
            state.events.append("fail")
        else:
            state.outcome = WON
            state.events.append("win")
            state.log.append(f"t{state.saves_done} WIN lost={state.lost} commits={state.commits}")
    return state


def every_k(k: int):
    def pol(state: State, config: Config) -> bool:
        return state.commits < config.io_budget and (state.saves_done + 1) % k == 0
    return pol


def paced_policy(state: State, config: Config) -> bool:
    """Spread the IO budget over the saves left: commit when the buffer (after this
    save) reaches ceil(saves_left / commits_left)."""
    left = config.io_budget - state.commits
    if left <= 0:
        return False
    saves_left = config.saves - state.saves_done
    need = -(-saves_left // left)
    return len(state.buffer) + 1 >= need


def end_only_policy(state: State, config: Config) -> bool:
    return False


def simulate(config: Config, policy=None) -> State:
    st = new_state(config)
    policy = policy or paced_policy
    while st.outcome == RUNNING:
        step(st, config, policy(st, config))
    return st


def islands_from_coral(coral_cfg: dict) -> List[dict]:
    """Tie-in: the G78 Coral Wear saves (G70 hot islands + G59 archives) are the saves
    that ride this journal, with the same weights."""
    return [{"id": i["id"], "weight": int(i["weight"])} for i in coral_cfg["islands"]]


def npc_say(state: State, config: Config) -> Tuple[str, str]:
    for k in ("fail", "win", "torn", "surge", "commit", "save", "start"):
        if k in state.events:
            return k, config.lines[k]
    return "save", config.lines["save"]


def receipt(state: State, config: Config) -> dict:
    return {
        "quest": QUEST_ID, "activity": "journal_tide", "island": "disk-saver",
        "outcome": state.outcome, "fail_reason": state.fail_reason,
        "saves": state.saves_done, "commits": state.commits, "lost": state.lost,
        "surges": state.surges, "torn": state.torn, "durable": state.seq,
        # score: saves kept (permille) only when won
        "score": ((config.saves - state.lost) * 1000) // config.saves if state.outcome == WON else 0,
    }


def load(path: str) -> Config:
    with open(path, encoding="utf-8") as f:
        return validate(json.load(f))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G79 Journal Tide (offline, seeded)")
    ap.add_argument("config")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--end-only", action="store_true", help="never commit until the season ends")
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
    st = simulate(cfg, end_only_policy if a.end_only else paced_policy)
    if a.trace:
        print("\n".join(st.log))
    print(json.dumps(receipt(st, cfg), sort_keys=True))
    print(f"{cfg.npc_name}: {npc_say(st, cfg)[1]}")
    return 0 if st.outcome == WON else 1


if __name__ == "__main__":
    sys.exit(main())
