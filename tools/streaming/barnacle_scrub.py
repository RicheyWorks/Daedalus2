# SPDX-License-Identifier: MIT
"""G151 Barnacle Scrub (DiskSaver Island, quest q_barnacle_scrub).

Every archived save (islands and keys_per_island of G86 Compaction Shoals,
read-only) is kept as two copies on the archive reef. Barnacles grow on the
copies: `barnacles_per_kilotick` barnacles land per 1000 ticks, each on a
random copy, and a good copy that is hit silently rots. Nothing notices rot
until the scrubber visits.

The scrub diver visits `rate` saves a tick, round robin, reading both copies
(2 reads per visit, counted against `max_reads`). With checksums the diver
knows which copy is good and rewrites a rotted copy from the good one; if both
copies have rotted, the save is lost. Without checksums the diver can only see
that the copies differ and copies A over B, so half the time it spreads the
rot over the good copy (the save is then lost silently).

Win: at season end at most `max_lost` saves have no good copy and the diver
stayed within `max_reads`. Too slow a diver lets both copies rot between
visits; too fast a diver blows the read budget; skipping checksums loses
saves to blind repairs. Unlike G90 Merkle Mangroves (finding drift between
two whole replicas), this is about silent corruption, checksums and the
scrub interval. Deterministic and offline: integers only, the shared LCG.

Reusable pieces:
  validate(cfg) -> Config
  Reef(n): rot(rng, hits) / visit(i, checksum) -> event
  simulate(config, rate=None, checksum=None) -> Result
  islands_from_shoals(shoals_cfg)  tie-in: islands + keys_per_island = G86
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

QUEST_ID = "q_barnacle_scrub"
VERSION = 1
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
WON, FAILED = "won", "failed"
FAIL_LOST, FAIL_READS = "saves_lost", "reads_exceeded"
OK, REPAIRED, LOST, SPREAD = "ok", "repaired", "lost", "spread"
NPC_KEYS = ("start", "dive", "barnacle", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "reef", "islands", "seed", "npc"}
R_KEYS = {"keys_per_island", "ticks", "barnacles_per_kilotick", "rate", "checksum", "max_lost", "max_reads"}


class ScrubError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    keys_per_island: int
    ticks: int
    barnacles_per_kilotick: int
    rate: int
    checksum: bool
    max_lost: int
    max_reads: int
    islands: Tuple[str, ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise ScrubError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise ScrubError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise ScrubError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise ScrubError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise ScrubError(f"quest must be {QUEST_ID}")
    h = cfg.get("reef")
    if not isinstance(h, dict) or set(h) != R_KEYS:
        raise ScrubError(f"reef must have exactly {sorted(R_KEYS)}")
    kpi = _int(h["keys_per_island"], "keys_per_island", 1, 100_000)
    t = _int(h["ticks"], "ticks", 1, 1_000_000)
    rp = _int(h["barnacles_per_kilotick"], "barnacles_per_kilotick", 0, 1_000_000)
    rate = _int(h["rate"], "rate", 0, 1_000_000)
    if not isinstance(h["checksum"], bool):
        raise ScrubError("checksum must be true or false")
    ml = _int(h["max_lost"], "max_lost", 0, 10_000_000)
    mr = _int(h["max_reads"], "max_reads", 0, 10 ** 12)
    isl = cfg.get("islands")
    if not isinstance(isl, list) or not isl:
        raise ScrubError("islands must be a non-empty list")
    seen = []
    for it in isl:
        iid = it.get("id") if isinstance(it, dict) else None
        if not isinstance(iid, str) or not iid or set(iid) - ID_CHARS or iid in seen:
            raise ScrubError(f"bad or duplicate island id: {iid!r}")
        seen.append(iid)
    seed = _int(cfg.get("seed", 1), "seed", 0, 2 ** 32 - 1)
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or not isinstance(npc.get("name"), str):
        raise ScrubError("npc must have a name")
    lines = npc.get("lines")
    if not isinstance(lines, dict) or set(lines) != set(NPC_KEYS):
        raise ScrubError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    if not all(isinstance(v, str) and v for v in lines.values()):
        raise ScrubError("npc lines must be non-empty strings")
    return Config(kpi, t, rp, rate, h["checksum"], ml, mr, tuple(seen), seed, npc["name"], dict(lines))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self, n: int) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) % n


class Reef:
    """Two copies per save; True = good copy."""

    def __init__(self, n: int):
        self.a = [True] * n
        self.b = [True] * n

    def rot(self, rng: Lcg, hits: int) -> int:
        """`hits` barnacles land on random copies; a good copy that is hit rots."""
        n, rotted = len(self.a), 0
        for _ in range(hits):
            j = rng.next(2 * n)
            side, i = (self.a, j) if j < n else (self.b, j - n)
            if side[i]:
                side[i] = False
                rotted += 1
        return rotted

    def visit(self, i: int, checksum: bool) -> str:
        a, b = self.a[i], self.b[i]
        if a and b:
            return OK
        if not a and not b:
            return LOST
        if checksum:
            self.a[i] = self.b[i] = True
            return REPAIRED
        # copies differ but the diver cannot tell which is good: copy A over B
        self.b[i] = a
        return REPAIRED if a else SPREAD

    def lost(self) -> int:
        return sum(1 for x, y in zip(self.a, self.b) if not x and not y)


def keys_for(c: Config) -> List[str]:
    return [f"{i}:{k:04d}" for i in c.islands for k in range(c.keys_per_island)]


@dataclass
class Result:
    status: str
    reason: Optional[str]
    saves: int
    rotted: int
    repaired: int
    spread: int
    lost: int
    reads: int


def simulate(c: Config, rate: Optional[int] = None, checksum: Optional[bool] = None) -> Result:
    rate = c.rate if rate is None else rate
    cs = c.checksum if checksum is None else checksum
    if rate < 0:
        raise ScrubError("rate must be >= 0")
    n = len(keys_for(c))
    reef, rng = Reef(n), Lcg(c.seed)
    rotted = repaired = spread = reads = 0
    cursor = acc = 0
    for _ in range(c.ticks):
        acc += c.barnacles_per_kilotick
        rotted += reef.rot(rng, acc // 1000)
        acc %= 1000
        for _ in range(rate):
            ev = reef.visit(cursor, cs)
            reads += 2
            repaired += ev == REPAIRED
            spread += ev == SPREAD
            cursor = (cursor + 1) % n
    lost = reef.lost()
    if lost > c.max_lost:
        status, reason = FAILED, FAIL_LOST
    elif reads > c.max_reads:
        status, reason = FAILED, FAIL_READS
    else:
        status, reason = WON, None
    return Result(status, reason, n, rotted, repaired, spread, lost, reads)


def islands_from_shoals(shoals_cfg) -> Tuple[List[dict], int]:
    """G86 tie-in: islands and keys_per_island from Compaction Shoals, read-only."""
    return ([{"id": it["id"]} for it in shoals_cfg["islands"]],
            shoals_cfg["shoals"]["keys_per_island"])


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result, rate: int, checksum: bool) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason, "rate": rate,
            "checksum": checksum, "saves": r.saves, "rotted": r.rotted, "repaired": r.repaired,
            "spread": r.spread, "lost": r.lost, "max_lost": c.max_lost, "reads": r.reads,
            "max_reads": c.max_reads}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--rate", type=int, default=None, help="saves visited per tick")
    ap.add_argument("--no-checksum", action="store_true", help="scrub by comparing copies only (trap)")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    rate = c.rate if a.rate is None else a.rate
    cs = False if a.no_checksum else c.checksum
    r = simulate(c, rate, cs)
    print(npc_say(c, "start"))
    print(json.dumps(receipt(c, r, rate, cs), sort_keys=True))
    print(npc_say(c, "win" if r.status == WON else "fail"))
    return 0 if r.status == WON else 1


if __name__ == "__main__":
    sys.exit(main())
