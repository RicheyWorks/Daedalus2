"""Tests for tools/minigames/prism_shard.py (Shardring Resonance)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import catalog_validate as cv  # noqa: E402
import prism_shard as ps  # noqa: E402


def play(seed, diff, policy=ps.greedy_move):
    g = ps.start(seed, diff)
    moves = 0
    while not g.over:
        g.place(policy(g))
        moves += 1
    return g, moves


class Shardring(unittest.TestCase):
    def test_start_state(self):
        g = ps.start(7)
        self.assertEqual(g.difficulty, "normal")
        self.assertEqual(g.score, 0)
        self.assertFalse(g.over)
        self.assertEqual(g.ring, [None] * 10)
        self.assertIn(g.current, g.hues)
        self.assertIn(g.next, g.hues)

    def test_difficulty_table(self):
        for d, cfg in ps.DIFFICULTY.items():
            g = ps.start(1, d)
            self.assertEqual(len(g.ring), cfg["facets"])
            self.assertEqual(len(g.hues), cfg["hues"])
            self.assertEqual(g.pouch, cfg["shards"])
        self.assertLess(ps.DIFFICULTY["hard"]["facets"], ps.DIFFICULTY["easy"]["facets"])
        with self.assertRaises(ValueError):
            ps.start(1, "nightmare")

    def test_resonance_scores_and_clears(self):
        g = ps.start(3)
        g.ring = [None] * 10
        g.ring[0] = g.ring[1] = "ember"
        g.current = "ember"
        self.assertEqual(g.place(9), 9)  # wraps the ring: 9,0,1
        self.assertEqual(g.score, 9)
        self.assertEqual(g.ring, [None] * 10)
        self.assertEqual(g.resonance["ember"], 1)

    def test_chain_and_spirit(self):
        g = ps.start(3)
        total = 0
        for k in range(3):
            g.ring = [None] * 10
            g.ring[0] = g.ring[1] = "tide"
            g.ring[5] = "ember"
            g.current = "tide"
            total += g.place(2)
        self.assertEqual(total, 9 * 1 + 9 * 2 + 9 * 3 + ps.SPIRIT_BONUS)
        self.assertEqual(g.spirits, ["Mere Sprite"])
        self.assertIsNone(g.ring[5])  # the spirit cleared the stray facet

    def test_no_match_resets_chain(self):
        g = ps.start(3)
        g.chain = 2
        g.ring = [None] * 10
        g.current = "ember"
        self.assertEqual(g.place(4), 0)
        self.assertEqual(g.chain, 0)

    def test_game_over_when_ring_fills(self):
        g = ps.start(5, "hard")
        hues = list(g.hues)
        g.ring = [hues[i % 2] for i in range(7)] + [None]
        g.current = hues[2]
        g.place(7)
        self.assertTrue(g.over)
        self.assertFalse(g.won)
        with self.assertRaises(RuntimeError):
            g.place(0)

    def test_win_when_pouch_empty(self):
        g = ps.start(5)
        g.pouch = 1
        g.place(0)
        self.assertTrue(g.over)
        self.assertTrue(g.won)

    def test_illegal_facet(self):
        g = ps.start(2)
        g.place(0) if g.ring[0] is None else None
        g.ring[1] = "ember"
        with self.assertRaises(ValueError):
            g.place(1)
        with self.assertRaises(ValueError):
            g.place(99)

    def test_deterministic_per_seed(self):
        for d in ps.DIFFICULTY:
            a, ma = play(42, d)
            b, mb = play(42, d)
            self.assertEqual((a.status(), ma), (b.status(), mb))
        self.assertNotEqual([ps.start(1)._draw() for _ in range(20)],
                            [ps.start(2)._draw() for _ in range(20)])

    def test_full_games_end_and_score(self):
        for seed in range(20):
            for d in ps.DIFFICULTY:
                g, moves = play(seed, d)
                self.assertTrue(g.over)
                self.assertLessEqual(moves, ps.DIFFICULTY[d]["shards"])
                self.assertGreaterEqual(g.score, 0)

    def test_original_name(self):
        for text in (ps.TITLE, ps.HOW_TO_PLAY, ps.GAME_ID):
            self.assertEqual(cv.trademark_hits(text), [])


if __name__ == "__main__":
    unittest.main()
