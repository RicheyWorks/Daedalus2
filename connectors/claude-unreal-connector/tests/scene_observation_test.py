# SPDX-License-Identifier: MIT
"""Offline contract checks of the production scene commands and bridge serializer.

Each test imports its own fake Unreal module and owns separate worlds/actors. No
listener, editor, socket, asset load, or shared fake module is used.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest import mock

TESTS = Path(__file__).resolve().parent
PYTHON = TESTS.parent / "plugin" / "ClaudeUnrealBridge" / "Content" / "Python"
BRIDGE = PYTHON / "claude_unreal_bridge.py"
SCENE = PYTHON / "claude_unreal_scene.py"


def load_file(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class World:
    def __init__(self, path, identity):
        self.path, self.identity = path, identity

    def get_path_name(self):
        return self.path

    def __repr__(self):
        return "<World native=%s>" % self.identity


class Asset:
    def __init__(self, path):
        self.path = path

    def get_path_name(self):
        return self.path


class ClassValue(Asset):
    def __init__(self, name):
        super().__init__("/Script/Engine." + name)
        self.name = name

    def get_name(self):
        return self.name


class SceneObservationTests(unittest.TestCase):
    def setUp(self):
        self.fake = load_file(TESTS / "fake_unreal.py", "scene_test_fake")
        self.original_level = list(self.fake.LEVEL)
        self.original_state = dict(self.fake.STATE)
        self.fake.GAME_THREAD[0] = threading.get_ident()
        self.native_reads, self.forbidden_calls = [], []
        self.editor_world = World("/Game/Test.Map", "editor-1")
        self.game_world = World("/Game/UEDPIE_0_Test.Map", "pie-1")
        self.editor_actors, self.game_actors, self.selected = [], [], []
        self.playing = False
        fixture = self
        fake = self.fake

        class SceneActor(fake.Actor):
            def __init__(self, path, label="Twin", folder="Realm", location=(0, 0, 0)):
                super().__init__(label, "StaticMeshActor", folder, location)
                self.path = path
                self.loc, self.rotation, self.scale = list(location), [0, 0, 0], [1, 1, 1]
                self.parent, self.comps, self.bounds_error = None, [], None
                self.path_error, self.folder_error, self.path_reads = None, None, 0

            def get_path_name(self):
                self.path_reads += 1
                if self.path_error:
                    raise RuntimeError(self.path_error)
                return self.path

            def get_folder_path(self):
                if self.folder_error:
                    raise RuntimeError(self.folder_error)
                return self.folder

            def get_class(self):
                return ClassValue("StaticMeshActor")

            def get_actor_rotation(self):
                return fake.R(*self.rotation)

            def get_actor_scale3d(self):
                return fake.V(*self.scale)

            def get_actor_bounds(self, only_colliding):
                if self.bounds_error:
                    raise RuntimeError(self.bounds_error)
                return fake.V(*self.loc), fake.V(100.004, 200.005, 300.006)

            def get_attach_parent_actor(self):
                return self.parent

        class SceneMesh(fake.StaticMeshComponent):
            def __init__(self, path, mesh=None, materials=()):
                super().__init__("Mesh")
                self.path, self.mesh, self.materials = path, mesh, list(materials)

            def get_path_name(self):
                return self.path

            def get_class(self):
                return ClassValue("StaticMeshComponent")

            def get_editor_property(self, key):
                if key != "static_mesh":
                    raise AssertionError("unexpected property " + key)
                return Asset(self.mesh) if self.mesh is not None else None

            def get_materials(self):
                return [Asset(path) if path is not None else None for path in self.materials]

        class SceneComponent(fake.ActorComponent):
            def __init__(self, path):
                super().__init__("Plain")
                self.path = path

            def get_path_name(self):
                return self.path

        class ActorSubsystem:
            def get_all_level_actors(self):
                fixture.native_reads.append("editor_actors")
                return list(fixture.editor_actors)

            def get_selected_level_actors(self):
                fixture.native_reads.append("editor_selection")
                return list(fixture.selected)

            def spawn_actor_from_class(self, *args):
                fixture.forbidden("spawn")

            def destroy_actor(self, *args):
                fixture.forbidden("destroy")

        class WorldSubsystem:
            def get_editor_world(self):
                fixture.native_reads.append("editor_world")
                return fixture.editor_world

            def get_game_world(self):
                fixture.native_reads.append("game_world")
                return fixture.game_world

        class LevelSubsystem:
            def is_in_play_in_editor(self):
                fixture.native_reads.append("playing")
                return fixture.playing

            def save_current_level(self):
                fixture.forbidden("save")

            def editor_request_begin_play(self):
                fixture.forbidden("play")

            def editor_request_end_play(self):
                fixture.forbidden("stop_play")

        subsystems = {fake.EditorActorSubsystem: ActorSubsystem(),
                      fake.UnrealEditorSubsystem: WorldSubsystem(),
                      fake.LevelEditorSubsystem: LevelSubsystem()}

        def get_subsystem(cls):
            fake._game_thread_only("scene fixture")
            fixture.native_reads.append("subsystem:" + cls.__name__)
            return subsystems[cls]

        def game_actors(world, cls):
            fixture.native_reads.append("game_actors")
            if world is not fixture.game_world or cls is not fake.Actor:
                raise AssertionError("wrong Play world")
            return list(fixture.game_actors)

        self.Actor, self.Mesh, self.Component = SceneActor, SceneMesh, SceneComponent
        fake.get_editor_subsystem = get_subsystem
        fake.GameplayStatics = types.SimpleNamespace(get_all_actors_of_class=game_actors)
        fake.load_asset = lambda *args: self.forbidden("load_asset")
        fake.EditorAssetLibrary = types.SimpleNamespace(
            load_asset=lambda *args: self.forbidden("asset_load"),
            save_asset=lambda *args: self.forbidden("asset_save"))
        self.scene_module = load_file(SCENE, "scene_test_commands")
        self.modules_patch = mock.patch.dict(sys.modules, {
            "unreal": fake, "claude_unreal_scene": self.scene_module})
        self.modules_patch.start()
        self.addCleanup(self.modules_patch.stop)
        self.env_patch = mock.patch.dict(os.environ, {"CLAUDE_UNREAL_ALLOW": "READ"})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.bridge = load_file(BRIDGE, "scene_test_bridge")
        # Even accidental use of start() must fail before creating a real listener.
        self.socket_patch = mock.patch.object(self.bridge.socket, "socket", side_effect=AssertionError("no sockets"))
        self.socket_patch.start()
        self.addCleanup(self.socket_patch.stop)

    def tearDown(self):
        self.assertEqual(self.fake.LEVEL, self.original_level)
        self.assertEqual(self.fake.STATE, self.original_state)
        self.assertEqual(self.fake.CALLS, [])
        self.assertEqual(self.forbidden_calls, [])

    def forbidden(self, operation):
        self.forbidden_calls.append(operation)
        raise AssertionError("scene observation attempted " + operation)

    def actor(self, suffix, **kwargs):
        actor = self.Actor(self.editor_world.path + ":PersistentLevel." + suffix, **kwargs)
        self.editor_actors.append(actor)
        return actor

    def snapshot(self, **params):
        return self.bridge.COMMANDS["scene_snapshot"](params)

    def check(self, actor, expected, context=None, tolerance=None):
        if context is None:
            context = self.snapshot()["context"]
        params = {"schema_version": 1, "context": context,
                  "actors": [{"path": actor.path if hasattr(actor, "path") else actor,
                              "expected": expected}]}
        if tolerance is not None:
            params["tolerance"] = tolerance
        return self.bridge.COMMANDS["scene_verify"](params)

    def dispatch(self, command, params):
        box = {"done": threading.Event()}
        self.bridge._start({"id": "offline", "type": command, "params": params}, box)
        self.assertTrue(box["done"].is_set())
        return box["reply"]

    def test_precise_shared_serializer_and_legacy_keys(self):
        actor = self.actor("A", folder="", location=(0.004, 1.234, -2.345))
        actor.rotation, actor.scale = [0.004, 90.123, 0], [1.004, 1, 0]
        mesh = self.Mesh(actor.path + ".Mesh", "/Game/Mesh.Mesh", [None, "/Game/Mat.Mat"])
        actor.comps = [mesh]
        legacy = self.bridge.cmd_get_actor_info({"name": actor.path})
        self.assertEqual(set(legacy), {"label", "name", "class", "folder", "location",
                                      "rotation", "scale", "bounds", "components"})
        self.assertEqual(legacy["location"], [0.0, 1.23, -2.35])
        self.assertNotIn("path", legacy["components"][0])
        precise = self.snapshot()["actors"][0]
        self.assertEqual(precise["location"], [0.004, 1.234, -2.345])
        self.assertEqual(precise["rotation"], actor.rotation)
        self.assertEqual(precise["scale"], actor.scale)
        self.assertEqual(precise["bounds"]["extent"], [100.004, 200.005, 300.006])
        self.assertEqual(precise["class_path"], "/Script/Engine.StaticMeshActor")
        self.assertEqual(precise["components"][0]["path"], mesh.path)
        self.assertEqual(precise["components"][0]["materials"], [None, "/Game/Mat.Mat"])
        self.assertIsNone(precise["parent_path"])
        self.assertIs(precise["selected"], False)
        self.assertEqual(precise["folder"], "")
        json.dumps(self.snapshot(), allow_nan=False)

    def test_same_labels_keep_exact_paths_and_legacy_ambiguity(self):
        first, second = self.actor("A"), self.actor("B")
        self.assertEqual([a["path"] for a in self.snapshot()["actors"]], [first.path, second.path])
        self.assertIs(self.bridge._find_actor(second.path), second)
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.bridge._find_actor("Twin")
        first.label = second.path
        self.assertIs(self.bridge._find_actor(second.path), second, "exact path takes priority over another label")
        self.assertTrue(self.check(second, {"location": [0, 0, 0]})["passed"])

    def test_snapshot_folder_boundary_and_page_sequence(self):
        actors = [self.actor("D", folder="OCEANIC"), self.actor("C", folder="OCEAN/sub"),
                  self.actor("A", folder="OCEAN"), self.actor("B", folder="OCEAN/deep/nested")]
        first = self.snapshot(folder="OCEAN", offset=0, limit=2)
        last = self.snapshot(folder="OCEAN", offset=first["scope"]["next_offset"], limit=2)
        self.assertEqual(first["scope"]["total_loaded"], 4)
        self.assertEqual(first["scope"]["total_matching"], 3)
        self.assertEqual(first["scope"]["returned"], 2)
        self.assertFalse(first["scope"]["complete"])
        self.assertFalse(last["scope"]["complete"])
        self.assertIsNone(last["scope"]["next_offset"])
        paths = [a["path"] for page in (first, last) for a in page["actors"]]
        self.assertEqual(paths, sorted(a.path for a in actors[1:]))
        whole = self.snapshot(folder="OCEAN", limit=3)
        self.assertTrue(whole["scope"]["complete"])
        self.assertIs(whole["scope"]["loaded_only"], True)
        self.assertIs(whole["scope"]["atomic"], False)

    def test_snapshot_empty_complete_but_offset_page_not_complete(self):
        empty = self.snapshot(folder="Missing")
        self.assertEqual(empty["actors"], [])
        self.assertEqual(empty["scope"]["total_matching"], 0)
        self.assertTrue(empty["scope"]["complete"])
        self.actor("A")
        beyond = self.snapshot(offset=10)
        self.assertEqual(beyond["scope"]["returned"], 0)
        self.assertFalse(beyond["scope"]["complete"])
        self.assertIsNone(beyond["scope"]["next_offset"])

    def test_snapshot_pages_are_fresh_reads(self):
        self.actor("A")
        first = self.snapshot(limit=1)
        self.actor("B")
        second = self.snapshot(offset=1, limit=1)
        self.assertEqual(first["scope"]["total_loaded"], 1)
        self.assertEqual(second["scope"]["total_loaded"], 2)
        self.assertEqual(first["context"], second["context"])
        self.assertFalse(second["scope"]["atomic"])

    def test_actor_page_and_checklist_maximum(self):
        for index in range(129):
            self.actor("A%03d" % index)
        page = self.snapshot(limit=128)
        self.assertEqual(page["scope"]["returned"], 128)
        self.assertEqual(page["scope"]["next_offset"], 128)
        self.assertFalse(page["scope"]["complete"])
        params = {"schema_version": 1, "context": page["context"],
                  "actors": [{"path": a.path, "expected": {"selected": False}}
                             for a in self.editor_actors[:128]]}
        self.assertTrue(self.bridge._scene.verify(params)["passed"])
        params["actors"].append({"path": self.editor_actors[-1].path, "expected": {"selected": False}})
        self.native_reads.clear()
        with self.assertRaisesRegex(ValueError, "expected_schema"):
            self.bridge._scene.verify(params)
        self.assertEqual(self.native_reads, [])

    def test_snapshot_invalid_bounds_fail_before_native_calls(self):
        for params in ({"limit": 129}, {"limit": 0}, {"limit": True}, {"limit": 1.5},
                       {"offset": -1}, {"offset": True}, {"offset": "0"}, {"folder": False}):
            with self.subTest(params=params), self.assertRaisesRegex(ValueError, "expected_schema"):
                self.snapshot(**params)
        self.assertEqual(self.native_reads, [])

    def test_partial_serialization_failure_retains_good_actors(self):
        bad, good = self.actor("A"), self.actor("B")
        bad.bounds_error = "deleted native wrapper"
        result = self.snapshot(limit=2)
        self.assertTrue(result["available"])
        self.assertEqual([a["path"] for a in result["actors"]], [good.path])
        self.assertEqual(result["scope"]["total_matching"], 2)
        self.assertEqual(result["scope"]["matched_known"], 2)
        self.assertEqual(result["scope"]["returned"], 1)
        self.assertFalse(result["scope"]["complete"])
        self.assertIsNone(result["scope"]["next_offset"])
        self.assertEqual(result["errors"][0]["path"], bad.path)
        self.assertEqual(result["errors"][0]["code"], "ACTOR_UNAVAILABLE")
        self.assertEqual(bad.path_reads, 1, "error reporting must use the cached catalogue path")

    def test_all_serialization_failures_are_not_empty_complete(self):
        self.actor("A").bounds_error = "deleted"
        result = self.snapshot()
        self.assertEqual(result["actors"], [])
        self.assertEqual(result["scope"]["total_matching"], 1)
        self.assertEqual(result["scope"]["matched_known"], 1)
        self.assertFalse(result["scope"]["complete"])
        self.assertEqual(len(result["errors"]), 1)

    def test_broken_catalogue_getters_keep_good_actor_and_unknown_missing_status(self):
        good, broken_path, broken_folder = self.actor("A"), self.actor("B"), self.actor("C")
        broken_path.path_error, broken_folder.folder_error = "deleted path", "deleted folder"
        snapshot = self.snapshot(folder="Realm")
        self.assertEqual([a["path"] for a in snapshot["actors"]], [good.path])
        self.assertFalse(snapshot["scope"]["complete"])
        self.assertIsNone(snapshot["scope"]["total_matching"])
        self.assertEqual(snapshot["scope"]["matched_known"], 1)
        self.assertEqual({e["path"] for e in snapshot["errors"]}, {None, broken_folder.path})
        self.assertEqual(snapshot["scope"]["error_count"], 2)
        result = self.check(good, {"selected": False}, context=snapshot["context"])
        self.assertTrue(result["passed"], "unrelated unreadable actors must not block a known path")
        self.assertEqual(len(result["observation_errors"]), 2)
        unavailable = self.check(broken_path, {"selected": False}, context=snapshot["context"])
        self.assertFalse(unavailable["passed"])
        self.assertEqual(unavailable["checks"][0]["code"], "ACTOR_UNOBSERVABLE")

    def test_duplicate_native_full_paths_are_ambiguous_not_last_winner(self):
        first, second = self.actor("A"), self.actor("B", location=(99, 0, 0))
        second.path = first.path
        snapshot = self.snapshot()
        self.assertEqual(snapshot["actors"], [])
        self.assertFalse(snapshot["scope"]["complete"])
        self.assertEqual(snapshot["errors"][0]["code"], "AMBIGUOUS_ACTOR_PATH")
        result = self.check(first, {"location": [99, 0, 0]}, context=snapshot["context"])
        self.assertFalse(result["passed"])
        self.assertEqual(result["checks"][0]["status"], "unavailable")
        self.assertEqual(result["checks"][0]["code"], "AMBIGUOUS_ACTOR_PATH")

    def test_catalogue_error_output_is_bounded_and_reports_truncation(self):
        for index in range(129):
            self.actor("A%03d" % index).path_error = "deleted " + "x" * 1200
        snapshot = self.snapshot()
        self.assertEqual(len(snapshot["errors"]), 128)
        self.assertEqual(snapshot["scope"]["error_count"], 129)
        self.assertTrue(snapshot["scope"]["errors_truncated"])
        self.assertFalse(snapshot["scope"]["complete"])
        self.assertIsNone(snapshot["scope"]["total_matching"])
        self.assertTrue(all(len(e["message"]) <= 1000 for e in snapshot["errors"]))

    def test_nested_component_and_material_caps_preserve_uncapped_legacy(self):
        actor = self.actor("A")
        actor.comps = [self.Mesh(actor.path + ".M%03d" % i) for i in range(128)]
        snapshot = self.snapshot()
        self.assertEqual(len(snapshot["actors"][0]["components"]), 128)
        actor.comps.append(self.Mesh(actor.path + ".M128"))
        oversized = self.snapshot()
        self.assertEqual(oversized["actors"], [])
        self.assertEqual(oversized["errors"][0]["code"], "ACTOR_UNAVAILABLE")
        self.assertFalse(oversized["scope"]["complete"])
        self.assertEqual(len(self.bridge.cmd_get_actor_info({"name": actor.path})["components"]), 129)
        actor.comps = [self.Mesh(actor.path + ".Mesh", materials=[None] * 128)]
        self.assertEqual(len(self.snapshot()["actors"][0]["components"][0]["materials"]), 128)
        context = snapshot["context"]
        actor.comps[0].materials.append(None)
        oversized = self.snapshot()
        self.assertEqual(oversized["actors"], [])
        self.assertEqual(oversized["errors"][0]["code"], "ACTOR_UNAVAILABLE")
        self.assertFalse(self.check(actor, {"selected": False}, context=context)["passed"])
        self.assertEqual(len(self.bridge.cmd_get_actor_info({"name": actor.path})["components"][0]["materials"]), 129)

    def test_nonfinite_native_values_are_unavailable_and_strict_json_safe(self):
        actor = self.actor("A")
        context = self.snapshot()["context"]
        for field, values in (("loc", [float("nan"), 0, 0]),
                              ("rotation", [0, float("inf"), 0]),
                              ("scale", [1, 1, -float("inf")])):
            with self.subTest(field=field):
                previous = getattr(actor, field)
                setattr(actor, field, values)
                snapshot = self.snapshot()
                self.assertEqual(snapshot["actors"], [])
                self.assertEqual(snapshot["errors"][0]["code"], "ACTOR_UNAVAILABLE")
                verify = self.check(actor, {"selected": False}, context=context)
                self.assertFalse(verify["passed"])
                self.assertEqual(verify["checks"][0]["code"], "ACTOR_UNAVAILABLE")
                json.dumps(snapshot, allow_nan=False)
                json.dumps(verify, allow_nan=False)
                setattr(actor, field, previous)
        with mock.patch.object(actor, "get_actor_bounds", return_value=(self.fake.V(), self.fake.V(float("nan"), 1, 1))):
            snapshot = self.snapshot()
            verify = self.check(actor, {"selected": False}, context=context)
        self.assertEqual(snapshot["actors"], [])
        self.assertFalse(verify["passed"])
        self.assertEqual(verify["checks"][0]["code"], "ACTOR_UNAVAILABLE")
        json.dumps(snapshot, allow_nan=False)
        json.dumps(verify, allow_nan=False)

    def test_native_source_failure_is_distinct_from_missing_world(self):
        actor = self.actor("A")
        context = self.snapshot()["context"]
        with mock.patch.object(self.bridge._scene, "source", side_effect=RuntimeError("enumeration failed")):
            snapshot = self.snapshot()
            verify = self.check(actor, {"selected": False}, context=context)
        self.assertFalse(snapshot["available"])
        self.assertEqual(snapshot["code"], "OBSERVATION_UNAVAILABLE")
        self.assertFalse(verify["passed"])
        self.assertEqual(verify["code"], "OBSERVATION_UNAVAILABLE")
        self.assertEqual(verify["checks"], [])

    def test_unavailable_world_is_explicit_for_snapshot_and_verify(self):
        actor = self.actor("A")
        context = self.snapshot()["context"]
        self.editor_world = None
        snapshot = self.snapshot()
        self.assertIs(snapshot["available"], False)
        self.assertEqual(snapshot["code"], "WORLD_UNAVAILABLE")
        self.assertIsNone(snapshot["context"])
        self.assertIsNone(snapshot["scope"]["total_loaded"])
        self.assertIsNone(snapshot["scope"]["total_matching"])
        self.assertFalse(snapshot["scope"]["complete"])
        verify = self.check(actor, {"selected": False}, context=context)
        self.assertFalse(verify["passed"])
        self.assertEqual(verify["code"], "WORLD_UNAVAILABLE")
        self.assertEqual(verify["checks"], [])

    def test_pie_observation_uses_only_game_world_and_no_editor_selection(self):
        self.actor("Editor")
        game = self.Actor(self.game_world.path + ":PersistentLevel.Game", label="Game")
        self.game_actors = [game]
        self.playing = True
        snapshot = self.snapshot()
        self.assertEqual(snapshot["context"]["world_kind"], "pie")
        self.assertEqual(snapshot["context"]["world_path"], self.game_world.path)
        self.assertEqual([a["path"] for a in snapshot["actors"]], [game.path])
        self.assertIs(snapshot["actors"][0]["selected"], False)
        self.assertNotIn("editor_actors", self.native_reads)
        self.assertNotIn("editor_selection", self.native_reads)
        self.assertIn("game_actors", self.native_reads)

    def test_missing_pie_world_never_falls_back_to_editor_actors(self):
        self.actor("Editor")
        self.playing, self.game_world = True, None
        result = self.snapshot()
        self.assertFalse(result["available"])
        self.assertEqual(result["code"], "WORLD_UNAVAILABLE")
        self.assertNotIn("editor_actors", self.native_reads)
        self.assertNotIn("editor_selection", self.native_reads)

    def test_wrong_world_context_is_stale_without_serializing(self):
        actor = self.actor("A")
        context = self.snapshot()["context"]
        self.playing = True
        with mock.patch.object(self.bridge._scene, "serialize", side_effect=AssertionError("must not serialize")):
            result = self.check(actor, {"selected": False}, context=context)
        self.assertEqual(result["code"], "STALE_CONTEXT")
        self.assertFalse(result["passed"])
        self.assertEqual(result["checks"], [])

    def test_each_context_field_is_required_to_match_exactly(self):
        actor = self.actor("A")
        context = self.snapshot()["context"]
        with mock.patch.object(self.bridge._scene, "serialize", side_effect=AssertionError("must not serialize")):
            for field in context:
                wrong = dict(context, **{field: context[field] + "-stale"})
                with self.subTest(field=field):
                    result = self.check(actor, {"selected": False}, context=wrong)
                    self.assertFalse(result["passed"])
                    self.assertEqual(result.get("code"), "STALE_CONTEXT")
                    self.assertEqual(result["checks"], [])

    def test_same_path_new_native_repr_changes_epoch_and_retains_only_values(self):
        actor = self.actor("A")
        first = self.snapshot()["context"]
        self.assertEqual(first, self.snapshot()["context"])
        self.editor_world = World(self.editor_world.path, "editor-2")
        second = self.snapshot()["context"]
        self.assertEqual(first["world_path"], second["world_path"])
        self.assertNotEqual(first["world_epoch"], second["world_epoch"])
        result = self.check(actor, {"selected": False}, context=first)
        self.assertEqual(result["code"], "STALE_CONTEXT")
        self.assertTrue(all(type(value) is str for value in self.bridge._scene.world_key))
        self.assertTrue(all(type(value) is str for value in second.values()))

    def test_module_reload_invalidates_session_context(self):
        actor = self.actor("A")
        previous = self.snapshot()["context"]
        fresh_scene = load_file(SCENE, "scene_reload_commands")
        with mock.patch.dict(sys.modules, {"claude_unreal_scene": fresh_scene}):
            fresh_bridge = load_file(BRIDGE, "scene_reload_bridge")
        current = fresh_bridge._scene.snapshot({})["context"]
        self.assertNotEqual(previous["session_id"], current["session_id"])
        result = fresh_bridge._scene.verify({"schema_version": 1, "context": previous,
                    "actors": [{"path": actor.path, "expected": {"selected": False}}]})
        self.assertFalse(result["passed"])
        self.assertEqual(result["code"], "STALE_CONTEXT")
        self.assertEqual(result["checks"], [])

    def test_deleted_actor_is_unavailable_without_label_fallback(self):
        actor = self.actor("A")
        context = self.snapshot()["context"]
        self.editor_actors.remove(actor)
        replacement = self.actor("B", label=actor.label)
        result = self.check(actor, {"selected": False}, context=context)
        self.assertFalse(result["passed"])
        check = result["checks"][0]
        self.assertEqual(check["status"], "unavailable")
        self.assertEqual(check["code"], "ACTOR_NOT_LOADED")
        self.assertIsNone(check["observed"])
        self.assertEqual(check["mismatches"], [])
        self.assertNotEqual(check["path"], replacement.path)
        self.assertEqual(self.check(actor.label, {"selected": False})["checks"][0]["code"], "ACTOR_NOT_LOADED")

    def test_failed_actor_verify_is_unavailable_not_match(self):
        actor = self.actor("A")
        context = self.snapshot()["context"]
        actor.bounds_error = "unreadable"
        result = self.check(actor, {"selected": False}, context=context)
        self.assertFalse(result["passed"])
        self.assertEqual(result["checks"][0]["code"], "ACTOR_UNAVAILABLE")
        self.assertIsNone(result["checks"][0]["observed"])

    def test_parent_and_selection_predicates_preserve_null_false(self):
        actor, parent = self.actor("A"), self.actor("Parent")
        self.assertTrue(self.check(actor, {"parent_path": None, "selected": False})["passed"])
        actor.parent = parent
        self.selected = [actor]
        result = self.check(actor, {"parent_path": None, "selected": False})
        self.assertFalse(result["passed"])
        by_predicate = {m["predicate"]: m for m in result["checks"][0]["mismatches"]}
        self.assertEqual(by_predicate["parent_path"], {"predicate": "parent_path", "expected": None, "observed": parent.path})
        self.assertEqual(by_predicate["selected"], {"predicate": "selected", "expected": False, "observed": True})

    def test_component_paths_mesh_and_ordered_null_material_slots(self):
        actor = self.actor("A")
        component = self.Mesh(actor.path + ".Mesh", "/Game/Mesh.Mesh", [None, "/Game/Mat.Mat"])
        extra = self.Mesh(actor.path + ".Extra", None, [])
        actor.comps = [component, extra]
        expected = {"components": [{"path": component.path, "mesh": component.mesh,
                                   "materials": [None, "/Game/Mat.Mat"]}]}
        self.assertTrue(self.check(actor, expected)["passed"])
        component.mesh, component.materials = None, ["/Game/Mat.Mat", None]
        result = self.check(actor, expected)
        mismatches = result["checks"][0]["mismatches"]
        self.assertEqual(len(mismatches), 2)
        self.assertEqual(mismatches[0]["expected"], "/Game/Mesh.Mesh")
        self.assertIsNone(mismatches[0]["observed"])
        self.assertEqual(mismatches[1]["observed"], ["/Game/Mat.Mat", None])
        component.materials = [None, "/Game/Mat.Mat", None]
        self.assertFalse(self.check(actor, {"components": [{"path": component.path,
                                  "materials": [None, "/Game/Mat.Mat"]}]})["passed"])

    def test_missing_and_unsupported_components_are_explicit_even_for_null(self):
        actor = self.actor("A")
        missing_path = actor.path + ".Missing"
        result = self.check(actor, {"components": [{"path": missing_path, "mesh": None}]})
        mismatch = result["checks"][0]["mismatches"][0]
        self.assertFalse(result["passed"])
        self.assertEqual(mismatch["code"], "COMPONENT_NOT_LOADED")
        self.assertIsNone(mismatch["expected"])
        self.assertIsNone(mismatch["observed"])
        plain = self.Component(actor.path + ".Plain")
        actor.comps = [plain]
        result = self.check(actor, {"components": [{"path": plain.path, "mesh": None}]})
        self.assertEqual(result["checks"][0]["mismatches"][0]["code"], "UNSUPPORTED_COMPONENT_FIELD")

    def test_empty_component_material_lists_have_explicit_meaning(self):
        actor = self.actor("A")
        self.assertTrue(self.check(actor, {"components": []})["passed"])
        mesh = self.Mesh(actor.path + ".Mesh", None, [])
        actor.comps = [mesh]
        self.assertFalse(self.check(actor, {"components": []})["passed"])
        self.assertTrue(self.check(actor, {"components": [{"path": mesh.path, "mesh": None, "materials": []}]})["passed"])
        mesh.materials = [None]
        self.assertFalse(self.check(actor, {"components": [{"path": mesh.path, "materials": []}]})["passed"])

    def test_transform_tolerance_and_rotation_wrap(self):
        actor = self.actor("A", location=(1.004, 0, 0))
        actor.rotation, actor.scale = [179.9, -180.1, 360], [1.004, 1, 1]
        expected = {"location": [1, 0, 0], "rotation": [-180.1, 179.9, 0], "scale": [1, 1, 1]}
        self.assertTrue(self.check(actor, expected, tolerance={"location": .005, "rotation": 1e-10, "scale": .005})["passed"])
        result = self.check(actor, expected, tolerance={"location": .003, "rotation": 1e-10, "scale": .003})
        self.assertFalse(result["passed"])
        self.assertEqual({m["predicate"] for m in result["checks"][0]["mismatches"]}, {"location", "scale"})
        self.assertTrue(self.check(actor, {"rotation": [179.9 + 720, -180.1 - 360, 0]}, tolerance={"rotation": 1e-10})["passed"])

    def test_precise_004_drift_regression_rejects_legacy_rounding_mutant(self):
        actor = self.actor("A", location=(0.004, 0, 0))
        context = self.snapshot()["context"]
        self.assertFalse(self.check(actor, {"location": [0, 0, 0]}, context=context)["passed"])
        source = BRIDGE.read_text(encoding="utf-8")
        old = "nd = None if precise else 2"
        self.assertEqual(source.count(old), 1, "mutant must target production serializer")
        mutant = types.ModuleType("scene_rounding_mutant")
        exec(compile(source.replace(old, "nd = 2"), str(BRIDGE), "exec"), mutant.__dict__)
        mutant_context = mutant._scene.snapshot({})["context"]
        mutant_result = mutant._scene.verify({"schema_version": 1, "context": mutant_context,
            "actors": [{"path": actor.path, "expected": {"location": [0, 0, 0]}}]})
        self.assertTrue(mutant_result["passed"], "legacy rounding must be caught by drift assertion")

    def test_verify_schema_errors_precede_all_native_reads(self):
        actor = self.actor("A")
        valid = {"schema_version": 1, "context": self.snapshot()["context"],
                 "actors": [{"path": actor.path, "expected": {"location": [0, 0, 0]}}]}
        cases = []
        for value in (True, 2, None):
            cases.append(dict(valid, schema_version=value))
        cases += [dict(valid, context={}), dict(valid, actors=[]), dict(valid, actors=None)]
        cases.append(dict(valid, actors=valid["actors"] * 2))
        expected_cases = [{}, {"bounds": {}}, {"class": "StaticMeshActor"}, {"selected": 0},
                          {"parent_path": False}, {"location": [0, 0]}, {"location": [0, False, 0]},
                          {"location": [0, float("nan"), 0]}, {"scale": [1, float("inf"), 1]},
                          {"location": [0, 10 ** 1000, 0]},
                          {"rotation": [0, "0", 0]}, {"components": "mesh"},
                          {"components": [{"path": "C"}]},
                          {"components": [{"path": "C", "mesh": False}]},
                          {"components": [{"path": "C", "materials": [False]}]},
                          {"components": [{"path": "C", "materials": [None] * 129}]},
                          {"components": [{"path": "C", "mesh": None}] * 2},
                          {"components": [{"path": str(i), "mesh": None} for i in range(129)]}]
        cases += [dict(valid, actors=[{"path": actor.path, "expected": expected}]) for expected in expected_cases]
        for value in (-1, True, float("nan"), float("inf"), 10 ** 1000, "1"):
            cases.append(dict(valid, tolerance={"location": value}))
        cases += [dict(valid, tolerance={"bounds": 0}), dict(valid, tolerance=None)]
        self.native_reads.clear()
        for index, params in enumerate(cases):
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "expected_schema"):
                self.bridge._scene.verify(params)
        self.assertEqual(self.native_reads, [])

    def test_actual_dispatcher_read_policy_discovery_and_no_mutation(self):
        actor = self.actor("A")
        snapshot_reply = self.dispatch("scene_snapshot", {})
        self.assertEqual(snapshot_reply["status"], "ok")
        verify_reply = self.dispatch("scene_verify", {"schema_version": 1,
            "context": snapshot_reply["result"]["context"],
            "actors": [{"path": actor.path, "expected": {"selected": False}}]})
        self.assertEqual(verify_reply["status"], "ok")
        self.assertTrue(verify_reply["result"]["passed"])
        commands = {c["name"]: c for c in self.bridge.cmd_list_commands({})["commands"]}
        for name in ("scene_snapshot", "scene_verify"):
            self.assertEqual(commands[name]["risk"], "READ")
            self.assertTrue(commands[name]["description"])
        for command in ("execute_python", "save", "play"):
            self.assertEqual(self.dispatch(command, {})["code"], "REFUSED")
        before = list(self.native_reads)
        self.bridge.POLICY["READ"] = False
        self.assertEqual(self.dispatch("scene_snapshot", {})["code"], "REFUSED")
        self.assertEqual(self.native_reads, before)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SceneObservationTests))
    print("%d/%d" % (result.testsRun - len(result.failures) - len(result.errors), result.testsRun))
    raise SystemExit(0 if result.wasSuccessful() else 1)
