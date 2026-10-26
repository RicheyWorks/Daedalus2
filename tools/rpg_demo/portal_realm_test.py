# SPDX-License-Identifier: MIT
"""Focused offline tests for the canonical Portal projection; no browser or art needed."""
import json
from copy import deepcopy
from pathlib import Path
import unittest

import portal_realm


REPO = Path(__file__).resolve().parents[2]


class PortalProjectionTest(unittest.TestCase):
    def setUp(self):
        self.inputs = {}

    def read(self, name):
        if name not in self.inputs:
            self.inputs[name] = json.loads((REPO / "data/rpg" / name).read_text(encoding="utf-8"))
        return self.inputs[name]

    def test_identity_party_family_and_existing_encounters(self):
        data = portal_realm.project(self.read)
        self.assertEqual("portal", data["realm_key"])
        self.assertEqual("Portal Realm", data["name"])
        self.assertEqual([256, 224], data["screen"])
        self.assertEqual("portal.save.v1", data["runtime"]["save_key"])
        self.assertEqual(1, data["runtime"]["start_level"])
        self.assertEqual(self.read("portal-encounters.json")["zones"], data["encounters"])
        self.assertEqual(self.read("portal-bestiary.json"), data["bestiary"])
        self.assertTrue(all(item["key"].startswith("portal_") for item in data["bestiary"]["types"]))
        self.assertEqual([], data["fish"])
        self.assertEqual([], data["sky_loot"])

    def test_deterministic_and_canonical_inputs_unchanged(self):
        first = portal_realm.project(self.read)
        canonical_before = deepcopy(self.inputs)
        second = portal_realm.project(self.read)
        self.assertEqual(first, second)
        first["world"][0][0] = "not a canonical tile"
        first["town"]["npcs"].clear()
        first["bestiary"]["types"].clear()
        self.assertEqual(canonical_before, self.inputs)
        self.assertNotEqual(first, portal_realm.project(self.read))

    def test_terminal_unexported_stair_closed_only_in_projection(self):
        data = portal_realm.project(self.read)
        dungeon = data["dungeons"][0]
        source = next(d for d in self.read("dungeons.json")["dungeons"]["portal"] if d["name"] == "Old Mine")
        self.assertEqual(3, len(dungeon["floors"]))
        for index, floor in enumerate(dungeon["floors"][:-1]):
            self.assertEqual(source["floors"][index], floor)
        old_stair = source["floors"][-1]["stairs_down"]
        self.assertEqual("floor 4", old_stair["to"])
        self.assertIsNone(dungeon["floors"][-1]["stairs_down"])
        self.assertEqual("Floor", dungeon["floors"][-1]["grid"][old_stair["y"]][old_stair["x"]])
        self.assertEqual("StairsDown", source["floors"][-1]["grid"][old_stair["y"]][old_stair["x"]])
        self.assertIsNone(dungeon["boss_data"])
        self.assertFalse(dungeon["final"])

    def test_village_reuses_template_without_aliasing_town(self):
        data = portal_realm.project(self.read)
        self.assertEqual(data["town"]["grid"], data["village"]["grid"])
        self.assertEqual("Village", data["village"]["landmark"])
        data["village"]["grid"][0][0] = "changed"
        self.assertNotEqual(data["town"]["grid"], data["village"]["grid"])

    def test_malformed_grid_and_spawn_rejected(self):
        for grid in (None, [], [[]], [["Floor"], ["Floor", "Floor"]], [[None]], [[""]], [["Floor"]] * 129):
            with self.subTest(grid=repr(grid)[:40]):
                with self.assertRaises(ValueError):
                    portal_realm.grid_cells(grid)
        with self.assertRaises(ValueError):
            portal_realm.reachable([["Wall"]], {"Floor"}, (0, 0))

    def test_missing_unreachable_landmark_rejected(self):
        self.read("worldmap-tiles.json")
        world = self.inputs["worldmap-tiles.json"]["demo_maps"]["portal"]
        for row in world:
            for x, tile in enumerate(row):
                if tile == "Cave":
                    row[x] = "Mountain"
        with self.assertRaisesRegex(ValueError, "missing world landmark"):
            portal_realm.project(self.read)

    def test_malformed_stair_not_silently_adapted(self):
        original = deepcopy(self.read("dungeons.json"))
        for value in (-1, 9999, True, "7"):
            with self.subTest(value=value):
                changed = deepcopy(original)
                next(d for d in changed["dungeons"]["portal"] if d["name"] == "Old Mine")["floors"][0]["stairs_up"]["x"] = value
                self.inputs["dungeons.json"] = changed
                with self.assertRaises(ValueError):
                    portal_realm.project(self.read)
        changed = deepcopy(original)
        next(d for d in changed["dungeons"]["portal"] if d["name"] == "Old Mine")["floors"][-1]["stairs_down"]["to"] = "floor 999"
        self.inputs["dungeons.json"] = changed
        with self.assertRaisesRegex(ValueError, "unexpected Portal stair"):
            portal_realm.project(self.read)


if __name__ == "__main__":
    unittest.main()
