# SPDX-License-Identifier: MIT
"""Waystone placement on the real Prismheart world map (G10, disk-saver). No browser, no art needed.

    python -m unittest tools/rpg_demo/waystone_place_test.py
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import waystones  # noqa: E402


def load():
    with open(os.path.join(REPO, "data", "rpg", "worldmap-tiles.json"), encoding="utf-8") as f:
        wm = json.load(f)
    with open(os.path.join(REPO, "data", "rpg", "prism-waystones.json"), encoding="utf-8") as f:
        ws = json.load(f)
    world = wm["demo_maps"]["prism"]
    walk = {t["tile"]: t["walkable"] for t in wm["tiles"] if t["realm"] == "prism"}
    marks = {t["tile"] for t in wm["tiles"] if t["realm"] == "prism" and t.get("kind") == "landmark"}
    return world, walk, marks, ws


class PlaceTest(unittest.TestCase):
    def test_real_map_places_every_waystone_on_reachable_ground(self):
        world, walk, marks, ws = load()
        out = waystones.place(world, walk, ws["waystones"], marks)
        reach = waystones.foot_reach(world, walk)
        self.assertEqual([w["id"] for w in out], [e["id"] for e in ws["waystones"]])
        self.assertEqual(len({(w["x"], w["y"]) for w in out}), len(out))
        for w in out:
            self.assertIn((w["x"], w["y"]), reach, w)
            self.assertTrue(walk[world[w["y"]][w["x"]]], w)
            self.assertNotIn(world[w["y"]][w["x"]], marks, w)
            lm = waystones.find(world, w["near"])
            self.assertLessEqual(abs(w["x"] - lm[0]) + abs(w["y"] - lm[1] - 1), 3, w)   # within a few steps of the exit

    def test_deterministic(self):
        world, walk, marks, ws = load()
        self.assertEqual(waystones.place(world, walk, ws["waystones"], marks), waystones.place(world, walk, ws["waystones"], marks))

    def test_bits_are_permanent_slots(self):
        _, _, _, ws = load()
        bits = [e["bit"] for e in ws["waystones"]]
        self.assertEqual(len(bits), len(set(bits)))
        self.assertTrue(all(0 <= b <= waystones.MAX_BIT for b in bits))

    def test_tiny_map_rules(self):
        G = [["Grass", "Grass", "Grass"], ["Grass", "Town", "Grass"], ["Grass", "Grass", "Water"]]
        walk = {"Grass": True, "Town": False, "Water": False}
        out = waystones.place(G, walk, [{"id": "a", "bit": 0, "name": "A", "near": "Town"}], {"Town"})
        self.assertEqual((out[0]["x"], out[0]["y"]), (0, 2))     # exit (1,2); east is water, so west
        out = waystones.place(G, walk, [{"id": "a", "bit": 0, "name": "A", "near": "Town"}, {"id": "b", "bit": 1, "name": "B", "near": "Town"}], {"Town"})
        self.assertNotEqual((out[0]["x"], out[0]["y"]), (out[1]["x"], out[1]["y"]))

    def test_avoids_other_world_triggers(self):
        G = [["Grass", "Grass", "Grass"], ["Grass", "Town", "Grass"], ["Grass", "Grass", "Water"]]
        walk = {"Grass": True, "Town": False, "Water": False}
        out = waystones.place(G, walk, [{"id": "a", "bit": 0, "name": "A", "near": "Town"}], {"Town"}, avoid=[(0, 2)])
        self.assertNotIn((out[0]["x"], out[0]["y"]), [(0, 2), (1, 2)])

    def test_refusals(self):
        G = [["Grass", "Town"], ["Water", "Water"]]
        walk = {"Grass": True, "Town": False, "Water": False}
        cases = [
            ([{"id": "a", "bit": 0, "name": "A", "near": "Castle"}], "not on the world map"),
            ([{"id": "a", "bit": 0, "name": "A", "near": "Town"}], "no exit reachable"),
            ([{"id": "A!", "bit": 0, "name": "A", "near": "Town"}], "bad id"),
            ([{"id": "a", "bit": 31, "name": "A", "near": "Town"}], "bad bit"),
            ([{"id": "a", "bit": True, "name": "A", "near": "Town"}], "bad bit"),
            ([{"id": "a", "bit": 0, "name": "A", "near": "Town"}, {"id": "a", "bit": 1, "name": "A", "near": "Town"}], "duplicate id"),
            ([{"id": "a", "bit": 0, "name": "A", "near": "Town"}, {"id": "b", "bit": 0, "name": "B", "near": "Town"}], "duplicate bit"),
            ([{"id": "a", "bit": 0, "name": "", "near": "Town"}], "no name"),
        ]
        for entries, why in cases:
            with self.assertRaises(ValueError) as cm:
                waystones.place(G, walk, entries, {"Town"})
            self.assertIn(why, str(cm.exception))


if __name__ == "__main__":
    unittest.main()
