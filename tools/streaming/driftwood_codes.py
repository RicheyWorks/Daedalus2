# SPDX-License-Identifier: MIT
"""G76 Driftwood Codes (DiskSaver Island, quest q_driftwood_codes).

Before a cache goes to the Reef it is packed into a bit stream. The Driftwood
Carver ties chunk kinds into bundles: each turn the keeper ties two bundles
into one (weight = sum), until one raft remains. Each chunk kind's code length
is its depth in the raft. The packed size is sum(freq * depth) bits and must
fit the reef slot (`bit_budget`). Tying the two lightest bundles every turn is
Huffman's rule and is optimal; tying in carving order is the trap.

Deterministic and offline: integers only, no randomness needed; ties are broken
by bundle id so a Java/C++ port gets the same codes.

Reusable pieces:
  validate(cfg) -> Config
  new_state(config) / tie(state, config, a, b)
  lightest_pair(state) -> (a, b)       Huffman's rule
  in_order_pair(state) -> (a, b)       the trap
  code_lengths(state) / codes(state)   canonical prefix codes from the raft
  encode / decode                      round trip over a symbol list
  kraft_ok(lengths)                    sum 2^-len == 1 for a full raft
  simulate(config, policy=None) -> State
  freqs_from_tide_chart(tide_cfg)      G70 tie-in: island request counts
  npc_say / receipt
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

QUEST_ID = "q_driftwood_codes"
VERSION = 1
MAX_KINDS = 256
MAX_FREQ = 1_000_000_000
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
RUNNING, WON, FAILED = "running", "won", "failed"
FAIL_BITS = "over_bit_budget"
NPC_KEYS = ("start", "tie", "light", "heavy", "win", "fail")
TOP_KEYS = {"v", "quest", "lore", "kinds", "bit_budget", "npc"}


class CodeError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    kinds: Tuple[Tuple[str, int], ...]
    bit_budget: int
    npc_name: str
    lines: Dict[str, str]


def _int(v, name, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or v < lo or v > hi:
        raise CodeError(f"{name} must be an integer in [{lo}, {hi}]")
    return v


def validate(cfg) -> Config:
    if not isinstance(cfg, dict):
        raise CodeError("config must be an object")
    if set(cfg) - TOP_KEYS:
        raise CodeError(f"unknown keys: {sorted(set(cfg) - TOP_KEYS)}")
    if cfg.get("v") != VERSION:
        raise CodeError("v must be 1")
    if cfg.get("quest", QUEST_ID) != QUEST_ID:
        raise CodeError(f"quest must be {QUEST_ID}")
    raw = cfg.get("kinds")
    if not isinstance(raw, list) or not 2 <= len(raw) <= MAX_KINDS:
        raise CodeError(f"kinds must list 2..{MAX_KINDS} chunk kinds")
    kinds, seen = [], set()
    for n, k in enumerate(raw):
        if not isinstance(k, dict) or set(k) != {"id", "freq"}:
            raise CodeError(f"kinds[{n}] must have exactly id and freq")
        kid = k["id"]
        if not isinstance(kid, str) or not kid or len(kid) > 64 or set(kid) - ID_CHARS:
            raise CodeError(f"kinds[{n}].id must be 1..64 chars of [A-Za-z0-9_]")
        if kid in seen:
            raise CodeError(f"duplicate kind {kid}")
        seen.add(kid)
        kinds.append((kid, _int(k["freq"], f"kinds[{n}].freq", 1, MAX_FREQ)))
    npc = cfg.get("npc")
    if not isinstance(npc, dict) or set(npc) != {"name", "lines"} or not isinstance(npc["name"], str) or not npc["name"]:
        raise CodeError("npc must have a name and lines")
    if not isinstance(npc["lines"], dict) or set(npc["lines"]) != set(NPC_KEYS):
        raise CodeError(f"npc.lines must have exactly {list(NPC_KEYS)}")
    for k, v in npc["lines"].items():
        if not isinstance(v, str) or not v or len(v) > 200:
            raise CodeError(f"npc.lines.{k} must be 1..200 chars")
    c = Config(tuple(kinds), _int(cfg.get("bit_budget"), "bit_budget", 1, 1 << 62), npc["name"], dict(npc["lines"]))
    if optimal_bits(c) > c.bit_budget:
        raise CodeError("bit_budget is below the Huffman optimum; the quest is unwinnable")
    return c


@dataclass
class Bundle:
    bid: int
    weight: int
    kids: Tuple  # (kind_id,) for a leaf, (Bundle, Bundle) for a tie


@dataclass
class State:
    bundles: List[Bundle]
    next_id: int
    ties: int = 0
    outcome: str = RUNNING
    fail_reason: Optional[str] = None
    bits: int = 0
    events: List[str] = field(default_factory=list)
    log: List[str] = field(default_factory=list)


def new_state(config: Config) -> State:
    bs = [Bundle(i, f, (k,)) for i, (k, f) in enumerate(config.kinds)]
    st = State(bs, len(bs), events=["start"])
    st.log.append(f"start kinds={len(bs)} budget={config.bit_budget}")
    return st


def _depths(b: Bundle, d: int, out: Dict[str, int]):
    if len(b.kids) == 1:
        out[b.kids[0]] = max(d, 1)
    else:
        _depths(b.kids[0], d + 1, out)
        _depths(b.kids[1], d + 1, out)


def code_lengths(state: State) -> Dict[str, int]:
    if len(state.bundles) != 1:
        raise CodeError("raft not finished")
    out: Dict[str, int] = {}
    _depths(state.bundles[0], 0, out)
    return out


def tie(state: State, config: Config, a: int, b: int) -> State:
    if state.outcome != RUNNING:
        raise CodeError("game is over")
    ids = {x.bid: x for x in state.bundles}
    if a == b or a not in ids or b not in ids:
        raise CodeError(f"bad tie {a}+{b}")
    light = sorted(state.bundles, key=lambda x: (x.weight, x.bid))[:2]
    is_light = sorted((ids[a].weight, ids[b].weight)) == [light[0].weight, light[1].weight]
    state.events = ["tie", "light" if is_light else "heavy"]
    nb = Bundle(state.next_id, ids[a].weight + ids[b].weight, (ids[a], ids[b]))
    state.next_id += 1
    state.bundles = [x for x in state.bundles if x.bid not in (a, b)] + [nb]
    state.ties += 1
    state.log.append(f"tie {a}+{b} -> {nb.bid} w={nb.weight}")
    if len(state.bundles) == 1:
        lens = code_lengths(state)
        state.bits = sum(f * lens[k] for k, f in config.kinds)
        if state.bits <= config.bit_budget:
            state.outcome = WON
            state.events.append("win")
            state.log.append(f"WIN bits={state.bits}")
        else:
            state.outcome, state.fail_reason = FAILED, FAIL_BITS
            state.events.append("fail")
            state.log.append(f"FAIL bits={state.bits}")
    return state


def lightest_pair(state: State) -> Tuple[int, int]:
    a, b = sorted(state.bundles, key=lambda x: (x.weight, x.bid))[:2]
    return a.bid, b.bid


def in_order_pair(state: State) -> Tuple[int, int]:
    return state.bundles[0].bid, state.bundles[1].bid


def simulate(config: Config, policy=None) -> State:
    st = new_state(config)
    policy = policy or lightest_pair
    while st.outcome == RUNNING:
        tie(st, config, *policy(st))
    return st


def optimal_bits(config: Config) -> int:
    import heapq
    h = [(f, i) for i, (_, f) in enumerate(config.kinds)]
    heapq.heapify(h)
    total, nid = 0, len(h)
    while len(h) > 1:
        a, b = heapq.heappop(h), heapq.heappop(h)
        total += a[0] + b[0]
        heapq.heappush(h, (a[0] + b[0], nid))
        nid += 1
    return total


def kraft_ok(lengths: Dict[str, int]) -> bool:
    m = max(lengths.values())
    return sum(1 << (m - l) for l in lengths.values()) == 1 << m


def codes(state: State) -> Dict[str, str]:
    """Canonical prefix codes from the raft's code lengths (length, then id)."""
    lens = code_lengths(state)
    out, code, prev = {}, 0, 0
    for k in sorted(lens, key=lambda k: (lens[k], k)):
        code <<= lens[k] - prev
        out[k] = format(code, f"0{lens[k]}b")
        code += 1
        prev = lens[k]
    return out


def encode(cmap: Dict[str, str], symbols: Sequence[str]) -> str:
    return "".join(cmap[s] for s in symbols)


def decode(cmap: Dict[str, str], bits: str) -> List[str]:
    rev = {v: k for k, v in cmap.items()}
    out, cur = [], ""
    for ch in bits:
        cur += ch
        if cur in rev:
            out.append(rev[cur])
            cur = ""
    if cur:
        raise CodeError("trailing bits")
    return out


def freqs_from_tide_chart(tide_cfg) -> List[dict]:
    """G70 tie-in: chunk kinds = islands, freq = how often the tide chart requests them."""
    import tide_chart_cache as tc
    c = tc.validate(tide_cfg)
    reqs = tc.requests(c)
    return [{"id": i.id, "freq": reqs.count(i.id)} for i in c.islands if reqs.count(i.id)]


def npc_say(state: State, config: Config) -> Tuple[str, str]:
    for k in ("fail", "win", "heavy", "light", "tie", "start"):
        if k in state.events:
            return k, config.lines[k]
    return "tie", config.lines["tie"]


def receipt(state: State, config: Config) -> dict:
    opt = optimal_bits(config)
    return {
        "quest": QUEST_ID, "activity": "driftwood_codes", "island": "disk-saver",
        "outcome": state.outcome, "fail_reason": state.fail_reason,
        "ties": state.ties, "bits": state.bits, "optimal_bits": opt, "bit_budget": config.bit_budget,
        # score: 1000 at the optimum, less toward the budget, only when won
        "score": 1000 - ((state.bits - opt) * 1000) // max(1, config.bit_budget - opt + 1)
        if state.outcome == WON else 0,
    }


def load(path: str) -> Config:
    with open(path, encoding="utf-8") as f:
        return validate(json.load(f))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G76 Driftwood Codes (offline)")
    ap.add_argument("config")
    ap.add_argument("--in-order", action="store_true", help="tie bundles in carving order")
    ap.add_argument("--trace", action="store_true")
    a = ap.parse_args(argv)
    try:
        cfg = load(a.config)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    st = simulate(cfg, in_order_pair if a.in_order else lightest_pair)
    if a.trace:
        print("\n".join(st.log))
        print(json.dumps(codes(st), sort_keys=True))
    print(json.dumps(receipt(st, cfg), sort_keys=True))
    print(f"{cfg.npc_name}: {npc_say(st, cfg)[1]}")
    return 0 if st.outcome == WON else 1


if __name__ == "__main__":
    sys.exit(main())
