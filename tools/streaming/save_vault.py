# SPDX-License-Identifier: MIT
"""G59 Save Vault Keeper (DiskSaver Island, quest q_save_vault).

DiskSaver Island keeps every island's save snapshots in a vault with a hard disk
quota. Snapshots are lists of content-addressed chunks, so chunks shared between
snapshots are stored once (dedupe). Every tick the keeper may:
  * mirror a snapshot to the Reef vault (uploads only chunks the Reef lacks,
    limited by `mirror_kib_per_tick`; a snapshot counts as mirrored once every
    chunk is on the Reef and its digest re-verifies), and
  * prune a local snapshot to free space.
Rules (the real disk-saver rule, as a game): the newest snapshot of every island
is pinned and cannot be pruned, and pruning a snapshot that is not mirrored loses
work: instant fail. Going over the quota after the islands write is also a fail.
Survive `win_ticks` ticks.

Deterministic and offline: integers only, a seeded 32-bit LCG, sha256 digests,
no wall clock, so a Java/C++ port can replay `trace()` line for line.

Reusable pieces (no Unreal, no I/O except the CLI):
  validate(cfg) -> Config                     strict save-vault-v1 parser
  new_state(config) -> State
  tick(state, config, actions=())             one step
  keeper_policy(state, config) -> actions     reference safe policy
  simulate(config, policy=None) -> State
  quota_from_byte_spring(spring_cfg, unit_kib) G39 tie-in: quota = cistern budget cap
  npc_say(state, config) -> (key, line)
  receipt(state, config) -> dict              G12-style activity receipt
Units: KiB, the DSB 1 cost unit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

QUEST_ID = "q_save_vault"
VERSION = 1
MAX_KIB = 1_000_000_000
MAX_TICKS = 10_000
MAX_ISLANDS = 1_000
MAX_POOL = 10_000
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")  # DSB 1 ids

RUNNING, WON, FAILED = "running", "won", "failed"
FAIL_LOST, FAIL_QUOTA = "lost_unmirrored", "quota_overflow"
NPC_KEYS = ("start", "write", "mirror", "prune", "pinned", "near_full", "win", "fail_lost", "fail_quota")
TOP_KEYS = {"v", "quest", "lore", "vault", "islands", "win_ticks", "seed", "npc"}
VAULT_KEYS = ("quota_kib", "mirror_kib_per_tick")
ISLAND_KEYS = {"id", "chunk_kib", "pool", "chunks_per_snapshot", "write_permille", "churn_permille"}
NEAR_FULL_PERMILLE = 850


class VaultError(ValueError):
    pass


@dataclass(frozen=True)
class Island:
    id: str
    chunk_kib: int
    pool: int
    chunks_per_snapshot: int
    write_permille: int
    churn_permille: int


@dataclass(frozen=True)
class Config:
    quota_kib: int
    mirror_kib_per_tick: int
    islands: Tuple[Island, ...]
    win_ticks: int
    seed: int
    npc_name: str
    lines: Dict[str, str]

    def island(self, iid: str) -> Island:
        for i in self.islands:
            if i.id == iid:
                return i
        raise KeyError(iid)


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise VaultError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise VaultError("config must be an object")
    extra = set(cfg) - TOP_KEYS
    if extra:
        raise VaultError(f"unknown keys: {sorted(extra)}")
    if cfg.get("v") != VERSION:
        raise VaultError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise VaultError(f"quest must be {QUEST_ID}")
    vault = cfg.get("vault")
    if not isinstance(vault, dict) or set(vault) != set(VAULT_KEYS):
        raise VaultError(f"vault must have exactly {list(VAULT_KEYS)}")
    quota = _int(vault["quota_kib"], "vault.quota_kib", 1, MAX_KIB)
    bw = _int(vault["mirror_kib_per_tick"], "vault.mirror_kib_per_tick", 1, MAX_KIB)
    raw = cfg.get("islands")
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_ISLANDS:
        raise VaultError(f"islands must be a list of 1..{MAX_ISLANDS}")
    islands, seen = [], set()
    for n, r in enumerate(raw):
        if not isinstance(r, dict) or set(r) != ISLAND_KEYS:
            raise VaultError(f"islands[{n}] must have exactly {sorted(ISLAND_KEYS)}")
        iid = r["id"]
        if not isinstance(iid, str) or not iid or len(iid) > 64 or set(iid) - ID_CHARS:
            raise VaultError(f"islands[{n}].id must be 1..64 chars of [A-Za-z0-9_]")
        if iid in seen:
            raise VaultError(f"duplicate island id {iid}")
        seen.add(iid)
        pool = _int(r["pool"], f"islands[{n}].pool", 1, MAX_POOL)
        islands.append(Island(
            iid,
            _int(r["chunk_kib"], f"islands[{n}].chunk_kib", 1, MAX_KIB),
            pool,
            _int(r["chunks_per_snapshot"], f"islands[{n}].chunks_per_snapshot", 1, pool),
            _int(r["write_permille"], f"islands[{n}].write_permille", 0, 1000),
            _int(r["churn_permille"], f"islands[{n}].churn_permille", 0, 1000),
        ))
    win = _int(cfg.get("win_ticks"), "win_ticks", 1, MAX_TICKS)
    seed = _int(cfg.get("seed", 1), "seed", 0, 2**32 - 1)
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or set(npc) != {"name", "lines"}:
        raise VaultError("npc must have name and lines")
    if not isinstance(npc["name"], str) or not npc["name"]:
        raise VaultError("npc.name must be a non-empty string")
    lines = npc["lines"]
    if not isinstance(lines, dict) or set(lines) != set(NPC_KEYS):
        raise VaultError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    for k, v in lines.items():
        if not isinstance(v, str) or not v or len(v) > 200:
            raise VaultError(f"npc.lines.{k} must be 1..200 chars")
    smallest = sum(i.chunk_kib * i.chunks_per_snapshot for i in islands)
    if smallest > quota:
        raise VaultError("quota cannot hold one snapshot per island (pinned set overflows)")
    return Config(quota, bw, tuple(islands), win, seed, npc["name"], dict(lines))


class Lcg:
    """32-bit LCG (Numerical Recipes constants); next_permille in [0, 1000)."""

    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self) -> int:
        self.s = (1664525 * self.s + 1013904223) & 0xFFFFFFFF
        return self.s

    def below(self, n: int) -> int:
        return (self.next() >> 8) % n

    def next_permille(self) -> int:
        return self.below(1000)


def digest(chunks: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(chunks).encode("utf-8")).hexdigest()


@dataclass
class Snapshot:
    sid: str
    island: str
    tick: int
    chunks: Tuple[str, ...]
    digest: str
    mirrored: bool = False


@dataclass
class State:
    rng: Lcg
    tick_no: int = 0
    seq: int = 0
    snaps: Dict[str, Snapshot] = field(default_factory=dict)
    heads: Dict[str, List[str]] = field(default_factory=dict)   # island -> current chunk set
    gen: Dict[str, int] = field(default_factory=dict)            # island -> next fresh chunk number
    reef: Dict[str, int] = field(default_factory=dict)           # chunk -> kib, on the Reef
    queue: List[str] = field(default_factory=list)               # mirror queue (snapshot ids)
    outcome: str = RUNNING
    fail_reason: Optional[str] = None
    events: List[str] = field(default_factory=list)
    log: List[str] = field(default_factory=list)
    pruned: List[str] = field(default_factory=list)
    uploaded_kib: int = 0

    def newest(self, island: str) -> Optional[str]:
        best = None
        for s in self.snaps.values():
            if s.island == island and (best is None or s.tick > best.tick or (s.tick == best.tick and s.sid > best.sid)):
                best = s
        return best.sid if best else None

    def pinned(self) -> set:
        return {sid for sid in (self.newest(i) for i in self.heads) if sid}


def chunk_kib(config: Config, chunk: str) -> int:
    return config.island(chunk.split(":", 1)[0]).chunk_kib


def used_kib(state: State, config: Config) -> int:
    seen = set()
    for s in state.snaps.values():
        seen.update(s.chunks)
    return sum(chunk_kib(config, c) for c in seen)


def _write(state: State, config: Config, isl: Island) -> Snapshot:
    head = state.heads[isl.id]
    if head:
        new = []
        for c in head:
            if state.rng.next_permille() < isl.churn_permille:
                n = state.gen[isl.id]
                state.gen[isl.id] = n + 1
                new.append(f"{isl.id}:c{n}")
            else:
                new.append(c)
    else:
        new = [f"{isl.id}:c{k}" for k in range(isl.chunks_per_snapshot)]
        state.gen[isl.id] = isl.chunks_per_snapshot
    state.heads[isl.id] = new
    state.seq += 1
    sid = f"{isl.id}@{state.tick_no}#{state.seq}"
    snap = Snapshot(sid, isl.id, state.tick_no, tuple(new), digest(new))
    state.snaps[sid] = snap
    return snap


def new_state(config: Config) -> State:
    st = State(rng=Lcg(config.seed))
    for isl in config.islands:
        st.heads[isl.id] = []
        st.gen[isl.id] = 0
        _write(st, config, isl)
    st.events = ["start"]
    st.log.append(f"t0 start used={used_kib(st, config)} quota={config.quota_kib}")
    return st


def _fail(state: State, reason: str, detail: str):
    state.outcome, state.fail_reason = FAILED, reason
    state.events.append("fail_lost" if reason == FAIL_LOST else "fail_quota")
    state.log.append(f"t{state.tick_no} FAIL {reason} {detail}")


def tick(state: State, config: Config, actions: Sequence[Tuple[str, str]] = ()) -> State:
    """One tick: player actions, Reef upload, island writes, quota check, win check."""
    if state.outcome != RUNNING:
        raise VaultError("game is over")
    state.tick_no += 1
    state.events = []
    pinned = state.pinned()
    for act in actions:
        if not (isinstance(act, (tuple, list)) and len(act) == 2 and act[0] in ("mirror", "prune")):
            raise VaultError(f"bad action {act!r}")
        kind, sid = act
        snap = state.snaps.get(sid)
        if snap is None:
            raise VaultError(f"unknown snapshot {sid}")
        if kind == "mirror":
            if not snap.mirrored and sid not in state.queue:
                state.queue.append(sid)
        else:
            if sid in pinned:
                state.events.append("pinned")
                state.log.append(f"t{state.tick_no} refuse prune {sid} (newest, pinned)")
                continue
            if not snap.mirrored:
                del state.snaps[sid]
                _fail(state, FAIL_LOST, sid)
                return state
            del state.snaps[sid]
            state.pruned.append(sid)
            if sid in state.queue:
                state.queue.remove(sid)
            state.events.append("prune")
            state.log.append(f"t{state.tick_no} prune {sid}")
    # Reef upload in queue order, bandwidth-limited; partial chunks wait.
    budget = config.mirror_kib_per_tick
    while state.queue:
        snap = state.snaps[state.queue[0]]
        for c in snap.chunks:
            if c in state.reef:
                continue
            k = chunk_kib(config, c)
            if k > budget:
                break
            state.reef[c] = k
            budget -= k
            state.uploaded_kib += k
        if all(c in state.reef for c in snap.chunks):
            # verify: digest recomputed from the Reef copy must match
            if digest([c for c in snap.chunks if c in state.reef]) != snap.digest:
                raise AssertionError("reef digest mismatch")
            snap.mirrored = True
            state.queue.pop(0)
            state.events.append("mirror")
            state.log.append(f"t{state.tick_no} mirrored {snap.sid}")
        else:
            break
    for isl in config.islands:
        if state.rng.next_permille() < isl.write_permille:
            s = _write(state, config, isl)
            state.events.append("write")
            state.log.append(f"t{state.tick_no} write {s.sid}")
    used = used_kib(state, config)
    if used > config.quota_kib:
        _fail(state, FAIL_QUOTA, f"used={used}")
        return state
    if used * 1000 >= config.quota_kib * NEAR_FULL_PERMILLE:
        state.events.append("near_full")
    if state.tick_no >= config.win_ticks:
        state.outcome = WON
        state.events.append("win")
        state.log.append(f"t{state.tick_no} WIN used={used}")
    return state


def keeper_policy(state: State, config: Config) -> List[Tuple[str, str]]:
    """Reference policy: queue every unmirrored snapshot (oldest first) and prune
    mirrored, unpinned snapshots oldest-first while the vault sits above 60%."""
    acts: List[Tuple[str, str]] = []
    order = sorted(state.snaps.values(), key=lambda s: (s.tick, s.sid))
    for s in order:
        if not s.mirrored and s.sid not in state.queue:
            acts.append(("mirror", s.sid))
    pinned = state.pinned()
    live = {s.sid for s in order}
    for s in order:
        if s.mirrored and s.sid not in pinned:
            rest = live - {s.sid}
            if _kib_of(state, config, live) * 10 > config.quota_kib * 6:
                acts.append(("prune", s.sid))
                live = rest
    return acts


def _kib_of(state, config, sids) -> int:
    seen = set()
    for sid in sids:
        seen.update(state.snaps[sid].chunks)
    return sum(chunk_kib(config, c) for c in seen)


def greedy_policy(state: State, config: Config) -> List[Tuple[str, str]]:
    """The tempting wrong move: prune every unpinned snapshot without mirroring."""
    pinned = state.pinned()
    return [("prune", s) for s in sorted(state.snaps) if s not in pinned]


def simulate(config: Config, policy=None) -> State:
    st = new_state(config)
    policy = policy or keeper_policy
    while st.outcome == RUNNING:
        tick(st, config, policy(st, config))
    return st


def quota_from_byte_spring(spring_cfg: dict, unit_kib: int = 1) -> int:
    """G39 tie-in: the vault quota is the Byte Spring streaming budget cap."""
    cap = spring_cfg["cistern"]["budget_cap"]
    return _int(cap, "cistern.budget_cap", 1, MAX_KIB) * _int(unit_kib, "unit_kib", 1, MAX_KIB)


def npc_say(state: State, config: Config) -> Tuple[str, str]:
    prio = ("fail_lost", "fail_quota", "win", "pinned", "near_full", "prune", "mirror", "write", "start")
    for k in prio:
        if k in state.events:
            return k, config.lines[k]
    return "write", config.lines["write"]


def receipt(state: State, config: Config) -> dict:
    used = used_kib(state, config)
    return {
        "quest": QUEST_ID,
        "activity": "save_vault",
        "island": "disk-saver",
        "outcome": state.outcome,
        "fail_reason": state.fail_reason,
        "ticks": state.tick_no,
        "used_kib": used,
        "quota_kib": config.quota_kib,
        "snapshots": len(state.snaps),
        "mirrored": sum(1 for s in state.snaps.values() if s.mirrored),
        "pruned": len(state.pruned),
        "uploaded_kib": state.uploaded_kib,
        # score: free space kept (permille of quota) only when won
        "score": ((config.quota_kib - used) * 1000) // config.quota_kib if state.outcome == WON else 0,
    }


def load(path: str) -> Config:
    with open(path, encoding="utf-8") as f:
        return validate(json.load(f))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G59 Save Vault Keeper (offline, seeded)")
    ap.add_argument("config")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--greedy", action="store_true", help="play the prune-without-mirror policy")
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
    st = simulate(cfg, greedy_policy if a.greedy else None)
    if a.trace:
        print("\n".join(st.log))
    print(json.dumps(receipt(st, cfg), sort_keys=True))
    print(f"{cfg.npc_name}: {npc_say(st, cfg)[1]}")
    return 0 if st.outcome == WON else 1


if __name__ == "__main__":
    sys.exit(main())
