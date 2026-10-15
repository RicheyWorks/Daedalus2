# SPDX-License-Identifier: MIT
"""Headless geometry and editor-ownership checks. Run: python test_daedalus_base_layer.py"""
import copy
import itertools
from pathlib import Path
import re
import sys
import types
import unittest
from unittest.mock import patch

import daedalus_base_layer as B
import daedalus_land_grid as G
import daedalus_realm_ground as R


def cube_box(spec):
    """Bounds from the actual 100 cm engine cube, independently of route metadata."""
    x, y, z = spec["location_cm"]
    sx, sy, sz = spec["scale"]
    return (x - sx * 50, y - sy * 50, x + sx * 50, y + sy * 50, z + sz * 50)


def contains(box, point, margin=50.0):
    return (box[0] + margin <= point[0] <= box[2] - margin
            and box[1] + margin <= point[1] <= box[3] - margin)


def connected(boxes, start):
    """Require a metre of shared width on both axes; a corner touch is not a route."""
    seen = {start}
    pending = [start]
    while pending:
        a = boxes[pending.pop()]
        for i, b in enumerate(boxes):
            if i not in seen and (min(a[2], b[2]) - max(a[0], b[0]) >= 100
                                  and min(a[3], b[3]) - max(a[1], b[1]) >= 100
                                  and abs(a[4] - b[4]) <= 20):
                seen.add(i)
                pending.append(i)
    return seen


def snapshot(actor):
    state = dict(actor.__dict__)
    if "static_mesh_component" in state:
        state["static_mesh_component"] = dict(actor.static_mesh_component.__dict__)
    return copy.deepcopy(state)


class FakeComponent:
    def __init__(self):
        self.mesh = self.profile = self.collision = None
        self.materials = {}

    def set_static_mesh(self, mesh):
        self.mesh = mesh

    def set_collision_profile_name(self, profile):
        self.profile = profile

    def set_collision_enabled(self, collision):
        self.collision = collision

    def set_material(self, index, material):
        self.materials[index] = material


class FakeActor:
    def __init__(self, location=(0, 0, 0), rotation=(0, 0, 0)):
        self.location, self.rotation = location, rotation
        self.scale, self.label, self.folder, self.tags = (1, 1, 1), "", "", []
        self.properties, self.property_order, self.operations = {}, [], []

    def get_actor_label(self):
        return self.label

    def set_actor_label(self, value):
        self.label = value

    def set_folder_path(self, value):
        self.folder = value

    def set_actor_location(self, value, *args):
        self.operations.append("location")
        self.location = value

    def set_actor_rotation(self, value, *args):
        self.operations.append("rotation")
        self.rotation = value

    def set_actor_scale3d(self, value):
        self.operations.append("scale")
        self.scale = value

    def set_editor_property(self, name, value):
        self.operations.append(name)
        self.properties[name] = value
        self.property_order.append(name)


class FakeMeshActor(FakeActor):
    def __init__(self, *args):
        super().__init__(*args)
        self.static_mesh_component = FakeComponent()


class FakeMarker(FakeActor):
    pass


class FakeTerrain(FakeActor):
    pass


class FakeEditor:
    def __init__(self, actors=()):
        self.actors = list(actors)
        self.spawned = []

    def get_all_level_actors(self):
        return self.actors[:]

    def spawn_actor_from_class(self, cls, location, rotation):
        actor = cls(location, rotation)
        self.actors.append(actor)
        self.spawned.append(actor)
        return actor

    def unreal(self, missing=()):
        module = types.ModuleType("unreal")
        module.EditorActorSubsystem = object()
        module.get_editor_subsystem = lambda cls: self
        module.StaticMeshActor, module.TargetPoint = FakeMeshActor, FakeMarker
        module.DaedalusExplorationTerrain = FakeTerrain
        module.Vector = module.Vector2D = module.Rotator = lambda *args: tuple(args)
        module.Name = str
        module.CollisionEnabled = types.SimpleNamespace(QUERY_AND_PHYSICS="solid", NO_COLLISION="none")
        module.load_asset = lambda path: None if path in missing else path
        return module


class BaseLayerTests(unittest.TestCase):
    def test_seven_canonical_origins_and_separated_full_grids(self):
        self.assertEqual(B.REALMS, ("WORLD-ZERO", "GALLERY-CITY", "PARCELS", "BRICKS",
                                   "LABYRINTH", "PORTAL", "OCEAN"))
        expected = {"WORLD-ZERO": (14850.0, -9500.0), "GALLERY-CITY": (4014850.0, -9500.0),
                    "PARCELS": (-3985150.0, -9500.0), "BRICKS": (14850.0, 3990500.0),
                    "LABYRINTH": (14850.0, -4009500.0), "PORTAL": (4014850.0, 3990500.0),
                    "OCEAN": (4014850.0, -4009500.0)}
        self.assertEqual(B.ORIGINS, expected)
        cell_corners = ((0 - G.HUB - 0.5) * G.PITCH_M * 100,
                        (G.SIDE - 1 - G.HUB + 0.5) * G.PITCH_M * 100)
        self.assertEqual(cell_corners, (-1292800, 1267200))
        plans = [B.plan(realm) for realm in B.REALMS]
        for plan in plans:
            x, y = expected[plan["realm"]]
            self.assertEqual(plan["bounds_cm"], (x - 1292800, y - 1292800, x + 1267200, y + 1267200))
        for a, b in itertools.combinations(plans, 2):
            ax0, ay0, ax1, ay1 = a["bounds_cm"]
            bx0, by0, bx1, by1 = b["bounds_cm"]
            self.assertTrue(ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0, (a["realm"], b["realm"]))

    def test_native_patch_covers_every_land_cell_with_bounded_work(self):
        for realm, cells in itertools.product(B.REALMS[1:], (1, 16, 32)):
            with self.subTest(realm=realm, cells=cells):
                plan = B.plan(realm, cells)
                terrain, = [a for a in plan["actors"] if a["kind"] == "terrain"]
                x, y, z = terrain["location_cm"]
                sx, sy, sz = terrain["scale"]
                length = cells * terrain["spacing_metres"] * 100
                self.assertEqual((x, y, x + sx * length, y + sy * length), plan["bounds_cm"])
                sample_x, sample_y = terrain["sample_origin_metres"]
                for actual, expected in zip((x - sample_x * 100 * sx, y - sample_y * 100 * sy), plan["origin_cm"]):
                    self.assertAlmostEqual(actual, expected)
                self.assertEqual(sz, 1.0)
                self.assertEqual(plan["terrain_vertices"], (cells + 1) ** 2)
                self.assertLessEqual(plan["terrain_vertices"], 1089)
                self.assertLessEqual(len(plan["actors"]), 20)
                if realm != "OCEAN":
                    self.assertFalse(terrain["ocean"])
                    self.assertLessEqual(z + 360, R.GROUND_Z)

    def test_native_spacing_is_accepted_by_runtime_and_editor_metadata(self):
        source = Path(__file__).resolve().parents[2] / "Source" / "DaedalusLink"
        header = (source / "Public" / "DaedalusExplorationTerrain.h").read_text()
        cpp = (source / "Private" / "DaedalusExplorationTerrain.cpp").read_text()
        runtime_limit = re.search(r"SpacingMetres\s*>\s*([\d.eE+\-]+)", cpp)
        editor_limit = re.search(r'ClampMax="([\d.]+)"\)\) double SpacingMetres', header)
        self.assertIsNotNone(runtime_limit)
        self.assertIsNotNone(editor_limit)
        for realm in B.REALMS[1:]:
            terrain, = [a for a in B.plan(realm)["actors"] if a["kind"] == "terrain"]
            self.assertLessEqual(terrain["spacing_metres"], float(runtime_limit.group(1)))
            self.assertLessEqual(terrain["spacing_metres"], float(editor_limit.group(1)))

    def test_marker_approaches_are_supported_and_form_one_walkable_component(self):
        for realm in B.REALMS:
            with self.subTest(realm=realm):
                plan = B.plan(realm, world_zero_routes=realm == "WORLD-ZERO")
                if realm != "WORLD-ZERO":
                    self.assertEqual(plan["markers"], R.markers(B.ORIGINS[realm]))
                marker_actors = [a for a in plan["actors"] if a["kind"] == "marker"]
                self.assertEqual({a["marker"] for a in marker_actors}, set(plan["markers"]))
                for actor in marker_actors:
                    self.assertIn(actor["marker"], actor["tags"])
                    self.assertEqual(actor["location_cm"], plan["markers"][actor["marker"]][:3])
                    self.assertEqual(actor["yaw"], plan["markers"][actor["marker"]][3])
                boxes = [cube_box(a) for a in plan["actors"] if a["kind"] == "cube" and a["collision"]]
                spawn_support = [i for i, box in enumerate(boxes) if contains(box, plan["markers"]["Spawn"])]
                self.assertTrue(spawn_support)
                reachable = connected(boxes, spawn_support[0])
                self.assertEqual(reachable, set(range(len(boxes))))
                for name, marker in plan["markers"].items():
                    support = [i for i in reachable if contains(boxes[i], marker) and abs(marker[2] - boxes[i][4] - 100) < 1e-6]
                    self.assertTrue(support, name)
                xmin, ymin, xmax, ymax = plan["bounds_cm"]
                self.assertTrue(all(xmin <= b[0] < b[2] <= xmax and ymin <= b[1] < b[3] <= ymax for b in boxes))

    def test_modern_cross_reaches_exact_grid_edges(self):
        for realm in B.REALMS[1:-1]:
            plan = B.plan(realm)
            ew, = [a for a in plan["actors"] if a["label"] == "BaseRoadEW_" + realm]
            ns, = [a for a in plan["actors"] if a["label"] == "BaseRoadNS_" + realm]
            self.assertEqual((cube_box(ew)[0], cube_box(ew)[2]), (plan["bounds_cm"][0], plan["bounds_cm"][2]))
            self.assertEqual((cube_box(ns)[1], cube_box(ns)[3]), (plan["bounds_cm"][1], plan["bounds_cm"][3]))

    def test_ocean_water_is_nonblocking_and_harbor_preserves_open_water(self):
        plan = B.plan("OCEAN")
        water, = [a for a in plan["actors"] if a.get("role") == "water"]
        seabed, = [a for a in plan["actors"] if a.get("role") == "seabed"]
        self.assertEqual(water["kind"], "plane")
        self.assertFalse(water["collision"])
        self.assertTrue(seabed["ocean"])
        self.assertEqual(seabed["scale"][2], 1)
        self.assertEqual(seabed["location_cm"][2], water["location_cm"][2])
        x, y, _ = water["location_cm"]
        sx, sy, _ = water["scale"]
        self.assertEqual((x - sx * 50, y - sy * 50, x + sx * 50, y + sy * 50), plan["bounds_cm"])
        harbor, = [a for a in plan["actors"] if a.get("role") == "harbor"]
        self.assertLess(max(harbor["scale"][:2]) * 100, R.hub_half_cm() * 2)
        dry_area = sum(a["scale"][0] * a["scale"][1] * 10000 for a in plan["actors"] if a["kind"] == "cube")
        self.assertLess(dry_area, (R.hub_half_cm() * 2) ** 2)

    def test_world_zero_default_adds_no_blanket_ground(self):
        plan = B.plan("WORLD-ZERO")
        self.assertTrue(plan["uses_existing_ground"])
        self.assertEqual(plan["terrain_vertices"], 0)
        self.assertEqual(len(plan["actors"]), 5)
        self.assertTrue(all(a["kind"] == "marker" for a in plan["actors"]))
        routes = B.plan("WORLD-ZERO", world_zero_routes=True)
        x, y = routes["origin_cm"]
        self.assertTrue(all(x - 21600 <= b[0] <= b[2] <= x + 21600 and y - 21600 <= b[1] <= b[3] <= y + 21600
                            for b in map(cube_box, (a for a in routes["actors"] if a["kind"] == "cube"))))

    def test_invalid_requests_fail_and_plans_are_fresh(self):
        for cells in (0, -1, 33, 10000, True, 16.0, "16", None):
            with self.subTest(cells=cells), self.assertRaises(ValueError):
                B.plan("OCEAN", cells)
        with self.assertRaises(ValueError):
            B.plan("UNKNOWN")
        first = B.plan("PORTAL")
        self.assertEqual(first, B.plan("PORTAL"))
        first["actors"].clear()
        self.assertTrue(B.plan("PORTAL")["actors"])
        for realm in B.REALMS:
            actors = B.plan(realm)["actors"]
            self.assertEqual(len({a["label"] for a in actors}), len(actors))
            self.assertTrue(all(B.OWNER_TAG in a["tags"] for a in actors))

    def test_ownership_requires_the_exact_owner_tag(self):
        self.assertEqual(B.disposition(), "create")
        for tags in ([], ["Realm:OCEAN"], [B.OWNER_TAG + "Other"], ["Hub", "Kit"]):
            self.assertEqual(B.disposition(tags), "preserve")
        self.assertEqual(B.disposition(["Realm:OCEAN", B.OWNER_TAG]), "update")

    def test_apply_preserves_existing_work_and_repeating_adds_no_duplicates(self):
        artist = FakeMeshActor((1, 2, 3))
        artist.label, artist.tags = "BaseHarbor_OCEAN", ["Artist:Harbor"]
        arrival = FakeMarker((7, 8, 9))
        arrival.label, arrival.tags = "Spawn_OCEAN", ["Spawn", "Realm:OCEAN"]
        before = [snapshot(a) for a in (artist, arrival)]
        editor = FakeEditor((artist, arrival))
        with patch.dict(sys.modules, unreal=editor.unreal()):
            first = B.apply("OCEAN")
            count = len(editor.actors)
            identities = editor.actors[:]
            water, = [a for a in editor.actors if a.label == "BaseWater_OCEAN"]
            water.location, water.scale = (1, 2, 3), (2, 2, 2)
            second = B.apply("OCEAN")
        self.assertEqual(first["preserved"], ["BaseHarbor_OCEAN", "Spawn_OCEAN"])
        self.assertEqual(second["preserved"], first["preserved"])
        self.assertEqual([snapshot(a) for a in (artist, arrival)], before)
        self.assertEqual(len(editor.actors), count)
        self.assertEqual(editor.actors, identities)
        self.assertEqual(second["created"], [])
        self.assertEqual(second["updated"], first["created"])
        self.assertFalse(first["saved"] or second["saved"])
        water_spec, = [a for a in B.plan("OCEAN")["actors"] if a["label"] == water.label]
        self.assertEqual((water.location, water.scale), (water_spec["location_cm"], water_spec["scale"]))
        self.assertEqual((water.static_mesh_component.profile, water.static_mesh_component.collision), ("NoCollision", "none"))
        terrain, = [a for a in editor.actors if isinstance(a, FakeTerrain)]
        self.assertEqual(terrain.property_order[0], "cells")
        self.assertEqual(terrain.properties["cells"], 16)
        self.assertTrue(terrain.properties["ocean"])

    def test_existing_large_native_patch_is_bounded_before_transform_updates(self):
        terrain = FakeTerrain()
        terrain.label, terrain.tags = "BaseSurface_PORTAL", [B.OWNER_TAG]
        terrain.properties["cells"] = 256
        editor = FakeEditor((terrain,))
        with patch.dict(sys.modules, unreal=editor.unreal()):
            result = B.apply("PORTAL", cells=32)
        self.assertIn(terrain.label, result["updated"])
        self.assertEqual(terrain.properties["cells"], 32)
        self.assertEqual(terrain.operations[0], "cells")
        for operation in ("location", "rotation", "scale", "spacing_metres", "sample_origin_metres", "ocean"):
            self.assertLess(terrain.operations.index("cells"), terrain.operations.index(operation))

    def test_duplicate_and_wrong_class_labels_are_reported_without_overwrite(self):
        one, two = FakeMarker(), FakeMarker()
        one.label = two.label = "Gate_PORTAL"
        wrong = FakeMarker((5, 6, 7))
        wrong.label, wrong.tags = "BaseSurface_PORTAL", [B.OWNER_TAG]
        before = [snapshot(a) for a in (one, two, wrong)]
        editor = FakeEditor((one, two, wrong))
        with patch.dict(sys.modules, unreal=editor.unreal()):
            preview = B.apply("PORTAL", dry_run=True)
            self.assertFalse(editor.spawned)
            result = B.apply("PORTAL")
        self.assertEqual(set(result["conflicts"]), {"Gate_PORTAL: duplicate label", "BaseSurface_PORTAL: owned actor has wrong class"})
        self.assertEqual(preview["conflicts"], result["conflicts"])
        self.assertEqual([snapshot(a) for a in (one, two, wrong)], before)

    def test_preflight_and_dry_run_mutate_nothing(self):
        for missing in ((B.CUBE,), (B.PLANE,), (B.WATER_MATERIAL,), "native-class"):
            with self.subTest(missing=missing):
                owned = FakeMeshActor((8, 9, 10))
                owned.label, owned.tags = "BaseHarbor_OCEAN", [B.OWNER_TAG]
                before = snapshot(owned)
                editor = FakeEditor((owned,))
                unreal = editor.unreal(missing=() if missing == "native-class" else missing)
                if missing == "native-class":
                    del unreal.DaedalusExplorationTerrain
                with patch.dict(sys.modules, unreal=unreal):
                    dry = B.apply("OCEAN", dry_run=True)
                    self.assertEqual(dry["created"], [a["label"] for a in B.plan("OCEAN")["actors"] if a["label"] != owned.label])
                    self.assertEqual(dry["updated"], [owned.label])
                    self.assertFalse(editor.spawned)
                    self.assertEqual(snapshot(owned), before)
                    with self.assertRaises(RuntimeError):
                        B.apply("OCEAN")
                self.assertEqual(editor.actors, [owned])
                self.assertEqual(snapshot(owned), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
