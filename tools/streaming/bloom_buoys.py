# SPDX-License-Identifier: MIT
"""G99 Bloom Buoys (DiskSaver Island, quest q_bloom_buoys).

Buoys float over the archive reefs. Each buoy carries a Bloom filter of the
saves stored on the reef below it (islands and keys_per_island from G86
Compaction Shoals, read-only). Before diving for a save the keeper asks the
buoy: "definitely not here" skips the dive, "maybe" costs a dive. A dive for
a save that is really there is useful; a dive that finds nothing is wasted.

Each buoy has a fixed bit budget (`bits_per_key` x keys on the reef). The
keeper chooses how many hash probes the buoy uses. Each window brings
`lookups` requests, `absent_permille` of them for saves that are not on the
reef. Win: in every window the wasted dives stay within `max_wasted`, and the
buoy never says "not here" for a save that is there (no false negatives).

A tuned hash count (about bits_per_key x ln 2) wins. One hash, too many
hashes, or no buoy at all flood the reef with wasted dives. Deterministic and
offline: integers only, the shared 32-bit LCG, zlib.crc32 double hashing.

Reusable pieces:
  validate(cfg) -> Config
  BloomFilter(bits, hashes): add / might_contain / fill_permille
  optimal_hashes(bits_per_key)  integer round(bits_per_key * ln 2)
  build_buoys(config, hashes) -> {island: BloomFilter}
  simulate(config, hashes=None, use_buoys=True) -> Result
  islands_from_shoals(shoals_cfg)  tie-in: islands + keys_per_island = G86
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
import zlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

QUEST_ID = "q_bloom_buoys"
VERSION = 1
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
WON, FAILED = "won", "failed"
FAIL_WASTE = "wasted_dives_exceeded"
NPC_KEYS = ("start", "ask", "dive", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "buoys", "islands", "seed", "npc"}
BUOY_KEYS = {"windows", "keys_per_island", "bits_per_key", "hashes", "lookups",
             "absent_permille", "max_wasted"}
MAX_HASHES = 32


class BuoyError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    windows: int
    keys_per_island: int
    bits_per_key: int
    hashes: int
    lookups: int
    absent_permille: int
    max_wasted: int
    islands: Tuple[str, ...]
    seed: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise BuoyError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise BuoyError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise BuoyError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise BuoyError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise BuoyError(f"quest must be {QUEST_ID}")
    b = cfg.get("buoys")
    if not isinstance(b, dict) or set(b) != BUOY_KEYS:
        raise BuoyError(f"buoys must have exactly {sorted(BUOY_KEYS)}")
    w = _int(b["windows"], "windows", 1, 10_000)
    kpi = _int(b["keys_per_island"], "keys_per_island", 1, 100_000)
    bpk = _int(b["bits_per_key"], "bits_per_key", 1, 64)
    h = _int(b["hashes"], "hashes", 1, MAX_HASHES)
    lk = _int(b["lookups"], "lookups", 1, 1_000_000)
    ap = _int(b["absent_permille"], "absent_permille", 0, 1000)
    mw = _int(b["max_wasted"], "max_wasted", 0, 1_000_000)
    isl = cfg.get("islands")
    if not isinstance(isl, list) or not isl:
        raise BuoyError("islands must be a non-empty list")
    seen = []
    for it in isl:
        iid = it.get("id") if isinstance(it, dict) else None
        if not isinstance(iid, str) or not iid or set(iid) - ID_CHARS or iid in seen:
            raise BuoyError(f"bad or duplicate island id: {iid!r}")
        seen.append(iid)
    seed = _int(cfg.get("seed", 1), "seed", 0, 2 ** 32 - 1)
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or not isinstance(npc.get("name"), str):
        raise BuoyError("npc must have a name")
    lines = npc.get("lines")
    if not isinstance(lines, dict) or set(lines) != set(NPC_KEYS):
        raise BuoyError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    if not all(isinstance(v, str) and v for v in lines.values()):
        raise BuoyError("npc lines must be non-empty strings")
    return Config(w, kpi, bpk, h, lk, ap, mw, tuple(seen), seed, npc["name"], dict(lines))


class Lcg:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self, n: int) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return (self.s >> 8) % n


def optimal_hashes(bits_per_key: int) -> int:
    """round(bits_per_key * ln 2) in integers, at least 1."""
    return max(1, min(MAX_HASHES, (bits_per_key * 693 + 500) // 1000))


class BloomFilter:
    """Bit-array Bloom filter with Kirsch-Mitzenmacher double hashing."""

    def __init__(self, bits: int, hashes: int):
        if bits < 1 or not 1 <= hashes <= MAX_HASHES:
            raise BuoyError("filter needs bits >= 1 and 1..32 hashes")
        self.bits, self.hashes = bits, hashes
        self.arr = bytearray((bits + 7) // 8)

    def _probes(self, key: str) -> List[int]:
        raw = key.encode()
        h1 = zlib.crc32(raw)
        h2 = zlib.crc32(raw, 0x9E3779B9) | 1
        return [(h1 + i * h2) % self.bits for i in range(self.hashes)]

    def add(self, key: str) -> None:
        for p in self._probes(key):
            self.arr[p >> 3] |= 1 << (p & 7)

    def might_contain(self, key: str) -> bool:
        return all(self.arr[p >> 3] >> (p & 7) & 1 for p in self._probes(key))

    def fill_permille(self) -> int:
        ones = sum(bin(x).count("1") for x in self.arr)
        return ones * 1000 // self.bits


def reef_keys(c: Config, island: str) -> List[str]:
    return [f"{island}:{k:04d}" for k in range(c.keys_per_island)]


def build_buoys(c: Config, hashes: int) -> Dict[str, BloomFilter]:
    out = {}
    for isl in c.islands:
        f = BloomFilter(c.bits_per_key * c.keys_per_island, hashes)
        for k in reef_keys(c, isl):
            f.add(k)
        out[isl] = f
    return out


@dataclass
class Result:
    status: str
    reason: Optional[str]
    windows_ok: int
    worst_wasted: int
    total_wasted: int
    useful_dives: int
    skipped: int
    false_negatives: int


def simulate(c: Config, hashes: Optional[int] = None, use_buoys: bool = True) -> Result:
    h = c.hashes if hashes is None else hashes
    buoys = build_buoys(c, h) if use_buoys else None
    rng = Lcg(c.seed)
    ok = worst = total = useful = skipped = fneg = 0
    for _ in range(c.windows):
        wasted = 0
        for _ in range(c.lookups):
            isl = c.islands[rng.next(len(c.islands))]
            absent = rng.next(1000) < c.absent_permille
            k = rng.next(c.keys_per_island)
            key = f"{isl}:{c.keys_per_island + k:04d}" if absent else f"{isl}:{k:04d}"
            maybe = True if buoys is None else buoys[isl].might_contain(key)
            if not maybe:
                skipped += 1
                if not absent:
                    fneg += 1
            elif absent:
                wasted += 1
            else:
                useful += 1
        worst, total = max(worst, wasted), total + wasted
        if wasted <= c.max_wasted:
            ok += 1
    if fneg:
        raise AssertionError("Bloom filter returned a false negative")
    status = WON if ok == c.windows else FAILED
    return Result(status, None if status == WON else FAIL_WASTE, ok, worst, total,
                  useful, skipped, fneg)


def islands_from_shoals(shoals_cfg) -> Tuple[List[dict], int]:
    """G86 tie-in: islands and keys_per_island from Compaction Shoals, read-only."""
    return ([{"id": it["id"]} for it in shoals_cfg["islands"]],
            shoals_cfg["shoals"]["keys_per_island"])


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result, hashes: int) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason, "hashes": hashes,
            "windows_ok": r.windows_ok, "windows": c.windows, "worst_wasted": r.worst_wasted,
            "max_wasted": c.max_wasted, "total_wasted": r.total_wasted,
            "useful_dives": r.useful_dives, "skipped": r.skipped}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config")
    ap.add_argument("--hashes", type=int, default=None, help="override the hash count")
    ap.add_argument("--no-buoys", action="store_true", help="dive for every lookup")
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as fh:
        c = validate(json.load(fh))
    h = c.hashes if a.hashes is None else a.hashes
    r = simulate(c, h, not a.no_buoys)
    print(npc_say(c, "start"))
    print(json.dumps(receipt(c, r, h), sort_keys=True))
    print(npc_say(c, "win" if r.status == WON else "fail"))
    return 0 if r.status == WON else 1


if __name__ == "__main__":
    sys.exit(main())
