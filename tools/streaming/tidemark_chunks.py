# SPDX-License-Identifier: MIT
"""G175 Tidemark Chunks (DiskSaver Island, quest q_tidemark_chunks).

Every G86 Compaction Shoals island (read-only) keeps a save on DiskSaver
Island. Each season the islands save a new version with a few seeded small
edits: inserted runs, deleted runs and overwritten runs. The save vault
stores every chunk once (by sha256), so whatever chunks two versions share
cost nothing the second time. Each stored chunk and every chunk reference in
a version's recipe also costs `ref_bytes` of index. The vault quota is the
G39 Byte Spring streaming budget cap times `byte_unit` (read-only).
Tallyman Oro picks the chunker:
  whole   one chunk per save: any edit stores the whole save again
  fixed   fixed-size chunks: one inserted byte shifts every later boundary,
          so nothing after the edit dedupes
  cdc     content-defined chunks: a rolling hash over the last `window` bytes
          marks a tidemark (cut) when its low `mask_bits` bits are zero, with
          `min_chunk`/`max_chunk` limits, so boundaries follow the content and
          resync right after an edit
Win: the vault cost of all versions fits the quota. Deterministic, offline.

Science (pinned in tests): the rolling hash equals the from-scratch window
hash at every byte; chunks always rebuild the save exactly and respect the
size limits; after one byte inserted at the front, fixed chunks share ~none
of the old chunks while CDC shares most; the CDC mean chunk is about
min_chunk - 1 + 2**mask_bits (seeded Monte Carlo); the vault cost equals a
brute-force oracle that compares chunk bytes directly; seeded replays are
identical.

Reusable pieces:
  validate(cfg) -> Config ; run(config, mode) -> Result
  window_hash / rolling_hashes / chunk_cdc / chunk_fixed / chunk / vault_cost / cost_oracle
  saves(config) -> versions ; shared_after_edit(data, edited, config, mode)
  islands_from_shoals(shoals_cfg)  tie-in: island saves = G86 islands
  quota_from_byte_spring(spring_cfg, byte_unit)  tie-in: quota = G39 budget cap
  npc_say / receipt (G12-style quest receipt)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

QUEST_ID = "q_tidemark_chunks"
VERSION = 1
MODES = ("whole", "fixed", "cdc")
WON, FAILED = "won", "failed"
FAIL_QUOTA = "over_quota"
NPC_KEYS = ("start", "tidemark", "shift", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "chunks", "shoals_data", "spring_data", "seed", "npc"}
C_KEYS = {"versions", "bytes_per_weight", "edits", "max_run", "insert_permille", "delete_permille",
          "window", "mask_bits", "min_chunk", "max_chunk", "fixed_size", "ref_bytes", "byte_unit", "mode"}
# Locked chunker (G175 approval 50444): changing any of these moves every tidemark and
# breaks dedup against saves already in the vault, so the golden fixture test pins them.
BASE = 257                # polynomial base
PRIME = 2_147_483_647     # 2**31 - 1, polynomial modulus
WINDOW = 16               # rolling-hash window, bytes
MASK_BITS = 7             # cut when the low 7 hash bits are zero (mean chunk ~ min_chunk - 1 + 128)


class ChunkError(ValueError):
    pass


@dataclass(frozen=True)
class Island:
    id: str
    weight: int


@dataclass(frozen=True)
class Config:
    islands: Tuple[Island, ...]
    versions: int
    bytes_per_weight: int
    edits: int
    max_run: int
    insert_permille: int
    delete_permille: int
    window: int
    mask_bits: int
    min_chunk: int
    max_chunk: int
    fixed_size: int
    ref_bytes: int
    byte_unit: int
    quota: int
    mode: str
    seed: int
    npc_name: str
    lines: Dict[str, str]


@dataclass(frozen=True)
class Result:
    status: str
    reason: Optional[str]
    mode: str
    versions: int
    raw_bytes: int
    refs: int
    unique_chunks: int
    stored_bytes: int
    cost: int
    quota: int


def islands_from_shoals(shoals_cfg) -> List[Island]:
    """G86 tie-in: one save per Compaction Shoals island (id, weight), read-only."""
    return [Island(it["id"], it["weight"]) for it in shoals_cfg["islands"]]


def quota_from_byte_spring(spring_cfg, byte_unit: int) -> int:
    """G39 tie-in: vault quota = Byte Spring streaming budget cap * byte_unit bytes (read-only)."""
    return spring_cfg["cistern"]["budget_cap"] * byte_unit


def _load(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _int(d, k, lo, hi):
    v = d.get(k)
    if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
        raise ChunkError(f"{k} must be an int in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict) or set(cfg) != TOP_KEYS:
        raise ChunkError(f"top-level keys must be {sorted(TOP_KEYS)}")
    if cfg["v"] != VERSION or cfg["quest"] != QUEST_ID:
        raise ChunkError("wrong version or quest")
    c = cfg["chunks"]
    if not isinstance(c, dict) or set(c) != C_KEYS:
        raise ChunkError(f"chunks keys must be {sorted(C_KEYS)}")
    if c["mode"] not in MODES:
        raise ChunkError(f"mode must be one of {MODES}")
    npc = cfg["npc"]
    if not isinstance(npc, dict) or set(npc.get("lines", {})) != set(NPC_KEYS) or not npc.get("name"):
        raise ChunkError("npc needs a name and lines " + ",".join(NPC_KEYS))
    ins = _int(c, "insert_permille", 0, 1000)
    dele = _int(c, "delete_permille", 0, 1000 - ins)
    window = _int(c, "window", 2, 64)
    if window != WINDOW or c["mask_bits"] != MASK_BITS:
        raise ChunkError(f"chunker is locked: window must be {WINDOW} and mask_bits {MASK_BITS}")
    mn = _int(c, "min_chunk", 1, 1 << 16)
    mx = _int(c, "max_chunk", mn, 1 << 20)
    islands = islands_from_shoals(_load(cfg["shoals_data"]))
    if not islands:
        raise ChunkError("need at least one G86 island")
    byte_unit = _int(c, "byte_unit", 1, 1 << 20)
    return Config(tuple(islands), _int(c, "versions", 1, 1000), _int(c, "bytes_per_weight", 1, 1 << 16),
                  _int(c, "edits", 0, 1000), _int(c, "max_run", 1, 1 << 12), ins, dele, window,
                  _int(c, "mask_bits", 1, 20), mn, mx, _int(c, "fixed_size", 1, 1 << 20),
                  _int(c, "ref_bytes", 0, 1024), byte_unit,
                  quota_from_byte_spring(_load(cfg["spring_data"]), byte_unit), c["mode"],
                  _int(cfg, "seed", 0, 2**31 - 1), npc["name"], dict(npc["lines"]))


def window_hash(win: Sequence[int]) -> int:
    """From-scratch polynomial hash of a byte window (oldest byte has the highest power)."""
    h = 0
    for b in win:
        h = (h * BASE + b + 1) % PRIME
    return h


def rolling_hashes(data: bytes, window: int) -> Iterable[Tuple[int, int]]:
    """Yield (i, hash of data[i-window+1 : i+1]) for every i >= window-1, rolling in O(1) per byte."""
    top = pow(BASE, window - 1, PRIME)
    h = 0
    for i, b in enumerate(data):
        if i >= window:
            h = (h - (data[i - window] + 1) * top) % PRIME
        h = (h * BASE + b + 1) % PRIME
        if i >= window - 1:
            yield i, h


def chunk_cdc(data: bytes, window: int, mask_bits: int, min_chunk: int, max_chunk: int) -> List[bytes]:
    """Content-defined chunks: cut after byte i when the window hash's low bits are zero (size limits apply)."""
    mask = (1 << mask_bits) - 1
    out: List[bytes] = []
    start = 0
    hashes = dict(rolling_hashes(data, window))
    for i in range(len(data)):
        size = i + 1 - start
        h = hashes.get(i)
        if size >= max_chunk or (size >= min_chunk and h is not None and h & mask == 0):
            out.append(data[start:i + 1])
            start = i + 1
    if start < len(data):
        out.append(data[start:])
    return out


def chunk_fixed(data: bytes, size: int) -> List[bytes]:
    return [data[i:i + size] for i in range(0, len(data), size)]


def chunk(data: bytes, c: Config, mode: str) -> List[bytes]:
    if mode == "whole":
        return [data] if data else []
    if mode == "fixed":
        return chunk_fixed(data, c.fixed_size)
    return chunk_cdc(data, c.window, c.mask_bits, c.min_chunk, c.max_chunk)


def _edit(rng: random.Random, data: bytearray, c: Config) -> None:
    run = rng.randint(1, c.max_run)
    pos = rng.randrange(len(data) + 1)
    r = rng.randrange(1000)
    if r < c.insert_permille or not data:
        data[pos:pos] = bytes(rng.randrange(256) for _ in range(run))
    elif r < c.insert_permille + c.delete_permille:
        del data[pos:pos + run]
    else:
        pos = min(pos, len(data) - 1)
        end = min(len(data), pos + run)
        data[pos:end] = bytes(rng.randrange(256) for _ in range(end - pos))


def saves(c: Config) -> List[List[bytes]]:
    """Seeded save history: versions[v][k] is island k's save at version v."""
    rng = random.Random(c.seed)
    cur = [bytearray(rng.randrange(256) for _ in range(it.weight * c.bytes_per_weight)) for it in c.islands]
    out = [[bytes(b) for b in cur]]
    for _ in range(1, c.versions):
        for b in cur:
            for _ in range(rng.randint(0, c.edits)):
                _edit(rng, b, c)
        out.append([bytes(b) for b in cur])
    return out


def vault_cost(recipes: List[List[bytes]], ref_bytes: int) -> Tuple[int, int, int, int]:
    """(refs, unique chunks, stored bytes, cost) for a vault keyed by sha256."""
    store: Dict[str, int] = {}
    refs = 0
    for rec in recipes:
        for ch in rec:
            refs += 1
            store.setdefault(hashlib.sha256(ch).hexdigest(), len(ch))
    stored = sum(store.values())
    return refs, len(store), stored, stored + ref_bytes * (len(store) + refs)


def cost_oracle(recipes: List[List[bytes]], ref_bytes: int) -> int:
    """Brute force: compare chunk bytes directly (no hashing), keep the first copy of each."""
    seen: List[bytes] = []
    refs = 0
    for rec in recipes:
        for ch in rec:
            refs += 1
            if not any(ch == s for s in seen):
                seen.append(ch)
    return sum(len(s) for s in seen) + ref_bytes * (len(seen) + refs)


def shared_after_edit(old: bytes, new: bytes, c: Config, mode: str) -> Tuple[int, int]:
    """(chunks of `new` already in `old`'s chunk set, chunks of `new`)."""
    have = set(chunk(old, c, mode))
    nc = chunk(new, c, mode)
    return sum(1 for ch in nc if ch in have), len(nc)


def run(c: Config, mode: Optional[str] = None) -> Result:
    mode = mode or c.mode
    hist = saves(c)
    recipes = [chunk(save, c, mode) for ver in hist for save in ver]
    refs, uniq, stored, cost = vault_cost(recipes, c.ref_bytes)
    raw = sum(len(s) for ver in hist for s in ver)
    status = WON if cost <= c.quota else FAILED
    return Result(status, None if status == WON else FAIL_QUOTA, mode, len(hist), raw, refs, uniq,
                  stored, cost, c.quota)


def npc_say(c: Config, key: str) -> str:
    return f"{c.npc_name}: {c.lines[key]}"


def receipt(c: Config, r: Result) -> dict:
    return {"quest": QUEST_ID, "status": r.status, "reason": r.reason, "mode": r.mode,
            "versions": r.versions, "islands": len(c.islands), "raw_bytes": r.raw_bytes, "refs": r.refs,
            "unique_chunks": r.unique_chunks, "stored_bytes": r.stored_bytes, "cost": r.cost,
            "quota": r.quota, "seed": c.seed}


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
