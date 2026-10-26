# SPDX-License-Identifier: MIT
"""G136 The Storm Season Archive (DiskSaver Island story chapter, quest q_storm_season_archive).

One storm season strings the landed DiskSaver storage games into one keeper
arc. Archivist Maren walks the keeper through seven acts; each act runs a
landed game read-only on its own shipped data (the module is imported, never
changed):
  G99 Bloom Buoys, G105 Hash Ring Atolls, G110 Quorum Quays, G113 Snapshot
  Shells, G120 Garbage Gulls, G123 Prefetch Pelicans, G126 Breakwater Queue.
In each act the keeper plays that game's tuned choice or falls for its trap
(no buoys, hash mod N, R=W=1, full copies, refcounting, depth 1, a short
breakwater).

New mechanic: the end-of-season archive audit. Every G86 Compaction Shoals
save (islands x keys_per_island) is dealt, by a seeded shuffle, to exactly
one act's storm (`stakes`) or to the safe harbour. An act that is lost loses
its stake. Each act's record is chained with SHA-256 (entry = sha256(prev +
canonical record)); the audit recomputes the chain, so a record edited after
the fact is caught, and an audit with a broken chain or an unaccounted save
fails outright. Grade: gold (every act won), pass (survived permille >=
`pass_permille`), fail. The chapter result goes out as a G12
activity-result-v1 receipt (canonical JSON + SHA-256 digest).

Reusable pieces:
  validate(cfg) -> Config
  run_act(act, choice, root) -> dict record
  deal(config) -> {act id: [keys]}, harbour keys
  play(config, traps=(), root=ROOT) -> Season (records + chain)
  verify_chain(records, chain) -> bool
  audit(config, season) -> Audit
  g12_receipt(config, season, audit) -> dict; receipt_json / receipt_digest
  islands_from_shoals(shoals_cfg)  tie-in: islands + keys_per_island = G86
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib
import json
import os
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

QUEST_ID = "q_storm_season_archive"
ACTIVITY_ID = "disksaver.storm-season-archive"
VERSION = 1
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
GOLD, PASS, FAIL = "gold", "pass", "fail"
TUNED, TRAP = "tuned", "trap"
GENESIS = "0" * 64
NPC_KEYS = ("start", "act", "audit", "gold", "pass", "fail")
TOP_KEYS = {"v", "quest", "lore", "season", "acts", "islands", "seed", "keeper", "npc"}
S_KEYS = {"keys_per_island", "pass_permille", "session_id", "clock_boundary_ms"}

# act id -> (gap, landed module, shipped data file, trap overrides). Read-only use.
ACTS: Dict[str, Tuple[str, str, str, dict]] = {
    "bloom_buoys": ("G99", "bloom_buoys", "bloom-buoys-v1.json", {"use_buoys": False}),
    "hash_ring_atolls": ("G105", "hash_ring_atolls", "hash-ring-atolls-v1.json", {"mod_n": True}),
    "quorum_quays": ("G110", "quorum_quays", "quorum-quays-v1.json", {"r": 1, "w": 1}),
    "snapshot_shells": ("G113", "snapshot_shells", "snapshot-shells-v1.json", {"full_copy": True}),
    "garbage_gulls": ("G120", "garbage_gulls", "garbage-gulls-v1.json", {"refcount": True}),
    "prefetch_pelicans": ("G123", "prefetch_pelicans", "prefetch-pelicans-v1.json", {"depth": 1}),
    "breakwater_queue": ("G126", "breakwater_queue", "breakwater-queue-v1.json", {"capacity": 40}),
}
ACT_ORDER = tuple(ACTS)


class ArchiveError(ValueError):
    pass


@dataclass(frozen=True)
class Act:
    id: str
    stake: int
    storm: str


@dataclass(frozen=True)
class Config:
    keys_per_island: int
    pass_permille: int
    session_id: str
    clock_boundary_ms: int
    acts: Tuple[Act, ...]
    islands: Tuple[str, ...]
    seed: int
    keeper: Dict[str, str]
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise ArchiveError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def _str(v, name):
    if not isinstance(v, str) or not v:
        raise ArchiveError(f"{name} must be a non-empty string")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise ArchiveError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise ArchiveError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise ArchiveError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise ArchiveError(f"quest must be {QUEST_ID}")
    s = cfg.get("season")
    if not isinstance(s, dict) or set(s) != S_KEYS:
        raise ArchiveError(f"season must have exactly {sorted(S_KEYS)}")
    kpi = _int(s["keys_per_island"], "keys_per_island", 1, 100_000)
    pp = _int(s["pass_permille"], "pass_permille", 0, 1000)
    sid = _str(s["session_id"], "session_id")
    clk = _int(s["clock_boundary_ms"], "clock_boundary_ms", 0, 2 ** 53)
    isl = cfg.get("islands")
    if not isinstance(isl, list) or not isl:
        raise ArchiveError("islands must be a non-empty list")
    seen: List[str] = []
    for it in isl:
        iid = it.get("id") if isinstance(it, dict) else None
        if not isinstance(iid, str) or not iid or set(iid) - ID_CHARS or iid in seen:
            raise ArchiveError(f"bad or duplicate island id: {iid!r}")
        seen.append(iid)
    acts = cfg.get("acts")
    if not isinstance(acts, list) or [a.get("id") if isinstance(a, dict) else None for a in acts] != list(ACT_ORDER):
        raise ArchiveError(f"acts must be exactly {list(ACT_ORDER)} in order")
    total = len(seen) * kpi
    parsed = []
    for a in acts:
        if set(a) != {"id", "stake", "storm"}:
            raise ArchiveError("each act needs exactly id, stake, storm")
        parsed.append(Act(a["id"], _int(a["stake"], f"{a['id']}.stake", 0, total), _str(a["storm"], "storm")))
    if sum(a.stake for a in parsed) > total:
        raise ArchiveError("stakes exceed the archive")
    seed = _int(cfg.get("seed", 1), "seed", 0, 2 ** 32 - 1)
    kp = cfg.get("keeper")
    if not isinstance(kp, dict) or set(kp) != {"instanceId", "kind", "profile", "role"} \
            or kp.get("kind") not in ("LIFE", "COLONY") or not all(isinstance(v, str) and v for v in kp.values()):
        raise ArchiveError("keeper must be a G12 participant {instanceId, kind LIFE|COLONY, profile, role}")
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or not isinstance(npc.get("name"), str):
        raise ArchiveError("npc must have a name")
    lines = npc.get("lines")
    if not isinstance(lines, dict) or set(lines) != set(NPC_KEYS):
        raise ArchiveError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    if not all(isinstance(v, str) and v for v in lines.values()):
        raise ArchiveError("npc lines must be non-empty strings")
    return Config(kpi, pp, sid, clk, tuple(parsed), tuple(seen), seed, dict(kp), npc["name"], dict(lines))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self, n: int) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) % n


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def run_act(act: str, choice: str, root: str = ROOT) -> dict:
    """Run one landed game read-only on its shipped data; return the act record."""
    if act not in ACTS:
        raise ArchiveError(f"unknown act {act!r}")
    if choice not in (TUNED, TRAP):
        raise ArchiveError("choice must be tuned or trap")
    gap, modname, data, trap = ACTS[act]
    mod = importlib.import_module(modname)
    with open(os.path.join(root, "data", "islands", "disk-saver", data), encoding="utf-8") as fh:
        c = mod.validate(json.load(fh))
    r = mod.simulate(c, **(trap if choice == TRAP else {}))
    return {"act": act, "gap": gap, "quest": mod.QUEST_ID, "choice": choice,
            "status": r.status, "reason": r.reason, "result": dataclasses.asdict(r)}


def chain_of(records: Iterable[dict]) -> List[str]:
    prev, out = GENESIS, []
    for rec in records:
        prev = hashlib.sha256((prev + canonical(rec)).encode("utf-8")).hexdigest()
        out.append(prev)
    return out


def verify_chain(records: List[dict], chain: List[str]) -> bool:
    return len(records) == len(chain) and chain_of(records) == list(chain)


def keys_for(c: Config) -> List[str]:
    return [f"{i}:{k:04d}" for i in c.islands for k in range(c.keys_per_island)]


def deal(c: Config) -> Tuple[Dict[str, List[str]], List[str]]:
    keys, rng = keys_for(c), Lcg(c.seed)
    for i in range(len(keys) - 1, 0, -1):
        j = rng.next(i + 1)
        keys[i], keys[j] = keys[j], keys[i]
    out, at = {}, 0
    for a in c.acts:
        out[a.id] = keys[at:at + a.stake]
        at += a.stake
    return out, keys[at:]


@dataclass
class Season:
    records: List[dict]
    chain: List[str]


def play(c: Config, traps: Iterable[str] = (), root: str = ROOT) -> Season:
    traps = set(traps)
    if traps - set(ACTS):
        raise ArchiveError(f"unknown acts: {sorted(traps - set(ACTS))}")
    recs = [run_act(a.id, TRAP if a.id in traps else TUNED, root) for a in c.acts]
    return Season(recs, chain_of(recs))


@dataclass
class Audit:
    grade: str
    chain_ok: bool
    accounted: bool
    acts_won: int
    total: int
    survived: int
    lost: int
    survived_permille: int
    lost_by_act: Dict[str, int]


def audit(c: Config, s: Season) -> Audit:
    stakes, harbour = deal(c)
    chain_ok = verify_chain(s.records, s.chain) and [r["act"] for r in s.records] == [a.id for a in c.acts]
    status = {r["act"]: r["status"] for r in s.records}
    lost_by_act = {a: (len(k) if status.get(a) != "won" else 0) for a, k in stakes.items()}
    total = len(keys_for(c))
    lost = sum(lost_by_act.values())
    survived = len(harbour) + sum(len(k) for a, k in stakes.items() if not lost_by_act[a])
    accounted = survived + lost == total and len(set(harbour).union(*stakes.values())) == total
    won = sum(1 for r in s.records if r["status"] == "won")
    permille = survived * 1000 // total
    if not chain_ok or not accounted:
        grade = FAIL
    elif won == len(c.acts):
        grade = GOLD
    elif permille >= c.pass_permille:
        grade = PASS
    else:
        grade = FAIL
    return Audit(grade, chain_ok, accounted, won, total, survived, lost, permille, lost_by_act)


def g12_receipt(c: Config, s: Season, a: Audit) -> dict:
    """Chapter result in the G12 activity-result-v1 wire order (see docs/contracts/activity-result-v1)."""
    head = s.chain[-1] if s.chain else GENESIS
    return {
        "schema": "activity-result-v1",
        "resultId": f"res-dsa-{head[:12]}",
        "sessionId": c.session_id,
        "activityId": ACTIVITY_ID,
        "definitionRevision": 1,
        "mode": "AUTHORITATIVE",
        "issuer": "disksaver-archive-host",
        "verificationRef": f"verify:sha256:{head[:16]}",
        "outcome": "COMPLETED" if a.grade in (GOLD, PASS) else "FAILED",
        "participants": [dict(c.keeper)],
        "measures": dict(sorted({"acts_won": a.acts_won, "saves_lost": a.lost,
                                 "saves_survived": a.survived,
                                 "survived_permille": a.survived_permille}.items())),
        "sourceEventRefs": [f"evt:dsa-{r['gap'].lower()}-{r['act']}" for r in s.records],
        "clockBoundaryMs": c.clock_boundary_ms,
    }


def receipt_json(rc: dict) -> str:
    return json.dumps(rc, separators=(",", ":"))


def receipt_digest(rc: dict) -> str:
    return hashlib.sha256(receipt_json(rc).encode("utf-8")).hexdigest()


def islands_from_shoals(shoals_cfg) -> Tuple[List[dict], int]:
    """G86 tie-in: islands and keys_per_island from Compaction Shoals, read-only."""
    return ([{"id": it["id"]} for it in shoals_cfg["islands"]],
            shoals_cfg["shoals"]["keys_per_island"])


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--trap", action="append", default=[], choices=ACT_ORDER,
                    help="fall for this act's trap (repeatable)")
    ap.add_argument("--root", default=ROOT, help="repo root holding data/islands/disk-saver")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    s = play(c, a.trap, a.root)
    au = audit(c, s)
    print(npc_say(c, "start"))
    for r in s.records:
        print(f"{r['gap']} {r['act']} ({r['choice']}): {r['status']}" + (f" ({r['reason']})" if r["reason"] else ""))
    print(npc_say(c, "audit"))
    print(json.dumps(dataclasses.asdict(au), sort_keys=True))
    rc = g12_receipt(c, s, au)
    print(receipt_json(rc))
    print("digest", receipt_digest(rc))
    print(npc_say(c, au.grade))
    return 0 if au.grade != FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
