"""Tests for tools/minigames/shard_parity.py (Shardring native-port fixtures)."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import prism_shard as ps  # noqa: E402
import shard_parity as sp  # noqa: E402


class Parity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(sp.OUT.read_text(encoding="utf-8"))

    def test_file_is_current(self):
        self.assertEqual(sp.OUT.read_text(encoding="utf-8").replace("\r\n", "\n"), sp.build())
        self.assertEqual(sp.main(["--check"]), 0)

    def test_covers_every_difficulty_and_seed(self):
        got = {(c["difficulty"], c["seed"]) for c in self.data["cases"]}
        self.assertEqual(got, {(d, s) for d in ps.DIFFICULTY for s in sp.SEEDS})
        self.assertEqual(self.data["rules"]["difficulty"], ps.DIFFICULTY)

    def test_cases_replay_exactly(self):
        for c in self.data["cases"]:
            g = ps.start(c["seed"], c["difficulty"])
            self.assertEqual([g.current, g.next], c["sequence"][:2])
            for m in c["moves"]:
                self.assertEqual(g.ring, m["ring_before"])
                self.assertEqual(g.current, m["shard"])
                self.assertEqual(g.place(m["facet"]), m["gained"])
                self.assertEqual((g.score, g.chain, g.ring, g.pouch), (m["score"], m["chain"], m["ring_after"], m["pouch"]))
            self.assertEqual(g.status(), c["final"])
            self.assertEqual(c["result"], "won" if g.won else "lost")

    def test_snapshots_resume(self):
        n = 0
        for c in self.data["cases"]:
            for snap in c["snapshots"]:
                g = ps.ShardringGame.from_state(snap["state"])
                for m in c["moves"][snap["after_move"]:]:
                    self.assertEqual(g.place(m["facet"]), m["gained"])
                self.assertEqual(g.status(), c["final"])
                n += 1
        self.assertGreater(n, 0)

    def test_fixture_exercises_the_rules(self):
        moves = [m for c in self.data["cases"] for m in c["moves"]]
        self.assertTrue(any(m["resonated"] for m in moves))
        self.assertTrue(any(m["chain"] >= 2 for m in moves))
        self.assertTrue(any(m["spirit"] for m in moves))
        self.assertTrue(any(c["result"] == "lost" for c in self.data["cases"]))

    def test_stale_file_fails_check(self):
        orig = sp.OUT
        try:
            sp.OUT = orig.with_name("does-not-exist.json")
            self.assertEqual(sp.main(["--check"]), 1)
        finally:
            sp.OUT = orig


if __name__ == "__main__":
    unittest.main()
