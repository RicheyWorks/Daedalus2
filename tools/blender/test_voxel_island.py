# SPDX-License-Identifier: MIT
"""Planner tests that run without Blender:  python -m unittest tools/blender/test_voxel_island.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voxel_island as V  # noqa: E402


class PlanTests(unittest.TestCase):
    def test_every_colour_key_is_in_the_biome_palette(self):
        for seed in range(240, 252):
            plan, pal = V.plan(seed), V.palette(seed)
            for layer, voxels in plan.items():
                for x, y, z, c in voxels:
                    self.assertIn(c, pal, "%s %s %s" % (seed, layer, c))

    def test_walk_surface_is_at_the_pivot(self):
        plan = V.plan(240)
        tops = [z for x, y, z, c in plan["island"] if c in ("grass", "grass2")]
        self.assertEqual(min(tops), 0)          # the plateau is z=0 (deed top)
        self.assertLessEqual(max(tops), 4)      # the hill is at most 4 m

    def test_biomes_cycle_and_differ(self):
        self.assertEqual([V.biome_of(s) for s in range(6)], list(V.BIOME_NAMES))
        self.assertNotEqual(V.palette(0)["grass"], V.palette(2)["grass"])

    def test_greedy_quads_cover_exactly_the_outer_faces(self):
        plan = V.plan(402)
        body = [v for k in V.GROUPS["body"] for v in plan[k]]
        occ = {(x, y, z) for x, y, z, _ in body}
        naive = sum(1 for (x, y, z) in occ for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)) if (x + d[0], y + d[1], z + d[2]) not in occ)
        quads = V.greedy_quads(body)
        self.assertEqual(sum(w * h for *_, w, h, c in quads), naive)
        self.assertLess(len(quads), naive / 3)   # the merge must pay for itself

    def test_walk_rects_cover_every_top_cell(self):
        plan = V.plan(504)
        rects = V.walk_rects(plan["island"])
        covered = {(x0 + i, y0 + j) for x0, y0, w, h, zt in rects for i in range(w) for j in range(h)}
        cells = {(x, y) for x, y, z, c in plan["island"]}
        self.assertEqual(covered, cells)

    def test_seed_is_deterministic(self):
        self.assertEqual(V.plan(333), V.plan(333))
        self.assertNotEqual(V.plan(333)["island"][:50], V.plan(334)["island"][:50])


if __name__ == "__main__":
    unittest.main()
