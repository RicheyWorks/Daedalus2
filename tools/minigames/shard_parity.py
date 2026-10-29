#!/usr/bin/env python3
"""Shardring parity fixtures: fixed seeded games from prism_shard.py for native ports.

Output: data/minigames/shardring-parity-v1.json

  python tools/minigames/shard_parity.py           # regenerate
  python tools/minigames/shard_parity.py --check   # CI: fail if the file is stale

Each case is one full game played with prism_shard.greedy_move: the raw shard
sequence from the seeded RNG, every move with its per-move events, to_state()
snapshots at fixed move numbers, and the final status. A C++/Unreal port passes
when it reproduces every field. Stdlib only. Never edits the game rules.
"""
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import prism_shard as ps  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/minigames/shardring-parity-v1.json"
SEEDS = (0, 1, 42, 2024)
SNAPSHOT_AT = (5, 20)
SEQUENCE_LEN = 64


def play_case(seed, difficulty):
    g = ps.start(seed, difficulty)
    r = random.Random(f"{ps.GAME_ID}:{seed}:{difficulty}")
    sequence = [r.choice(g.hues) for _ in range(SEQUENCE_LEN)]
    moves, snapshots = [], []
    n = 0
    while not g.over:
        facet = ps.greedy_move(g)
        shard, spirits_before, ring_before = g.current, len(g.spirits), list(g.ring)
        gained = g.place(facet)
        n += 1
        moves.append({"n": n, "facet": facet, "shard": shard, "gained": gained, "score": g.score,
                      "chain": g.chain, "resonated": gained > 0,
                      "spirit": g.spirits[-1] if len(g.spirits) > spirits_before else None,
                      "ring_before": ring_before, "ring_after": list(g.ring),
                      "next_current": g.current, "next_next": g.next, "pouch": g.pouch})
        if n in SNAPSHOT_AT:
            snapshots.append({"after_move": n, "state": g.to_state()})
    return {"seed": seed, "difficulty": difficulty, "rng_seed_string": f"{ps.GAME_ID}:{seed}:{difficulty}",
            "sequence": sequence, "moves": moves, "snapshots": snapshots,
            "final": g.status(), "result": "won" if g.won else "lost", "move_count": n}


def build():
    data = {
        "schema": "daedalus.minigames.shardring_parity/v1",
        "generated_by": "tools/minigames/shard_parity.py",
        "rules": {"game_id": ps.GAME_ID, "hues": list(ps.HUES), "spirits": dict(ps.SPIRITS),
                  "difficulty": ps.DIFFICULTY, "run": ps.RUN, "spirit_every": ps.SPIRIT_EVERY,
                  "spirit_bonus": ps.SPIRIT_BONUS,
                  "rng": "CPython random.Random(str seed) v2: SHA-512 seeding, MT19937, choice via getrandbits"},
        "policy": "greedy_move: prefer a facet whose run reaches RUN, then the longest run, then the lowest facet index",
        "cases": [play_case(s, d) for d in ps.DIFFICULTY for s in SEEDS],
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n"


def main(argv):
    text = build()
    if "--check" in argv:
        cur = OUT.read_text(encoding="utf-8").replace("\r\n", "\n") if OUT.exists() else ""
        if cur != text:
            print("FAIL: data/minigames/shardring-parity-v1.json is stale; run python tools/minigames/shard_parity.py")
            return 1
        print("shardring parity ok")
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {len(json.loads(text)['cases'])} cases to {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
