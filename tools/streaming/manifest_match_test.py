# SPDX-License-Identifier: MIT
"""Tests for manifest_match (G556)."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census_budget as cb  # noqa: E402
import manifest_match as mm  # noqa: E402

HOOK = os.path.join(cb.ROOT, "data", "islands", "disk-saver", "manifest-match-v1.json")


def census(worlds, date="2026-10-29"):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": s, "asset_definitions": n} for s, n in isl]} for w, isl in worlds]}


DOC = census([("alpha", [(1, 0), (2, 7), (3, 30)]), ("beta", [(4, 0), (5, 2)]), ("gamma", [(6, 100)])])
BIG = census([("w", [(i, i) for i in range(20)])])


def simulate_memory(cards):
    """Independent perfect-memory player: never flips a known card blindly, takes known pairs at once."""
    n, matched, known, turns = len(cards), set(), {}, 0
    unseen = list(range(n))
    while len(matched) < n:
        pair = next((p for p, v in known.items() if len(v) == 2), None)
        if pair:
            matched.update(known.pop(pair))
            turns += 1
            continue
        a = unseen.pop(0)
        if cards[a][0] in known:
            matched.update((a, known.pop(cards[a][0])[0]))
            turns += 1
            continue
        b = unseen.pop(0)
        turns += 1
        if cards[a][0] == cards[b][0]:
            matched.update((a, b))
        else:
            known[cards[a][0]] = [a]
            known.setdefault(cards[b][0], []).append(b)
    return turns


class MatchTest(unittest.TestCase):
    def test_layout_pairs(self):
        cards = mm.layout(DOC, 0)
        self.assertEqual(len(cards), 12)
        for label in {c[0] for c in cards}:
            faces = sorted(f for l, f in cards if l == label)
            self.assertEqual(len(faces), 2)
            self.assertTrue(faces[0].startswith("ISLAND ") and faces[1].startswith("MANIFEST "))
        self.assertIn("MANIFEST gamma:6 %d KiB" % cb.island_cost(100)[0], [f for _, f in cards])

    def test_layout_seeded_and_capped(self):
        self.assertEqual(mm.layout(DOC, 3), mm.layout(DOC, 3))
        self.assertGreater(len({json.dumps(mm.layout(DOC, s)) for s in range(8)}), 4)
        self.assertEqual(len(mm.layout(BIG, 1)), 2 * mm.MAX_PAIRS)

    def test_par_matches_independent_player(self):
        for s in range(25):
            cards = mm.layout(DOC, s)
            self.assertEqual(mm.perfect_turns(cards)[0], simulate_memory(cards), s)

    def test_par_bounds(self):
        for s in range(20):
            for doc in (DOC, BIG):
                cards = mm.layout(doc, s)
                par = mm.perfect_turns(cards)[0]
                pairs = len(cards) // 2
                self.assertGreaterEqual(par, pairs)
                self.assertLessEqual(par, 2 * pairs - 1)

    def test_auto_is_sharp(self):
        for s in range(15):
            r = mm.play(DOC, s, auto=True)
            self.assertEqual((r["verdict"], len(r["turns"]), r["matched_pairs"]), ("sharp", r["par"], 6))

    def test_cheat_turns_count_and_verdicts(self):
        cards = mm.layout(DOC, 2)
        pos = {}
        for i, (l, _) in enumerate(cards):
            pos.setdefault(l, []).append(i + 1)
        clairvoyant = [tuple(v) for v in pos.values()]
        self.assertEqual(mm.play(DOC, 2, clairvoyant)["verdict"], "sharp")
        r = mm.play(DOC, 2, clairvoyant[:3])
        self.assertEqual((r["verdict"], r["matched_pairs"]), ("unfinished", 3))
        miss = [c for c in [(clairvoyant[0][0], clairvoyant[1][0])] * 8] + clairvoyant
        self.assertEqual(mm.play(DOC, 2, miss)["verdict"], "matched")

    def test_log_reveals_faces(self):
        cards = mm.layout(DOC, 4)
        r = mm.play(DOC, 4, [(1, 2)])
        self.assertEqual(r["turns"][0]["faces"], [cards[0][1], cards[1][1]])
        self.assertEqual(r["turns"][0]["match"], cards[0][0] == cards[1][0])

    def test_refusals(self):
        cards = mm.layout(DOC, 2)
        pos = {}
        for i, (l, _) in enumerate(cards):
            pos.setdefault(l, []).append(i + 1)
        first = tuple(next(iter(pos.values())))
        for turns in ([(1, 1)], [(0, 2)], [(1, 13)], [first, (first[0], 3 if first[0] != 3 else 4)]):
            with self.assertRaises(mm.MatchError, msg=turns):
                mm.play(DOC, 2, turns)
        with self.assertRaises(mm.MatchError):
            mm.play(DOC, 2, [tuple(v) for v in pos.values()] + [(1, 2)])
        with self.assertRaises(mm.MatchError):
            mm.play(DOC, 2)
        with self.assertRaises(mm.MatchError):
            mm.parse_turns("1to2")
        with self.assertRaises(mm.MatchError):
            mm.layout(census([("a", [])]))

    def test_parse_turns(self):
        self.assertEqual(mm.parse_turns(" 1-2, 3-4 ,"), [(1, 2), (3, 4)])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            c = os.path.join(d, "census.json")
            with open(c, "w", encoding="utf-8") as f:
                json.dump(DOC, f)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(mm.main([c, "--json"]), 0)
            r = json.loads(out.getvalue())
            self.assertEqual((r["turns"], r["verdict"]), ([], "unfinished"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(mm.main([c, "--auto"]), 0)
            self.assertTrue(out.getvalue().startswith("manifest match: sharp"))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(mm.main([c, "--turns", "1-1"]), 2)

    def test_real_census_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            fx = os.path.join("tools", "world_census", "fixtures")
            subprocess.run([sys.executable, "-B", "-m", "tools.world_census", os.path.join(fx, "alpha.json"),
                            os.path.join(fx, "beta.json"), "--snapshot-date", "2026-10-26", "--bindings",
                            os.path.join(fx, "bindings.json"), "--output-dir", os.path.join(d, "out")],
                           cwd=cb.ROOT, check=True, capture_output=True)
            with open(os.path.join(d, "out", "census.json"), encoding="utf-8-sig") as f:
                doc = json.load(f)
        r = mm.play(doc, 0, auto=True)
        self.assertEqual((r["cards"], r["par"], r["verdict"]), (6, 4, "sharp"))

    def test_hook_covers_verdicts(self):
        with open(HOOK, encoding="utf-8") as f:
            h = json.load(f)
        self.assertEqual(h["quest"], "q_manifest_match")
        self.assertEqual(h["npc"]["name"], "Wharf Clerk Godfrey")
        self.assertEqual(h["hook"]["values"], list(mm.VERDICTS))
        for v in h["hook"]["values"]:
            self.assertTrue(h["npc"]["lines"][v])


if __name__ == "__main__":
    unittest.main()
