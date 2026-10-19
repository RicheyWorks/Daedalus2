# SPDX-License-Identifier: MIT
"""Small offline context refusals using only injected getter fakes.

Source preparation only; the author has not executed these tests.
"""
import copy
from types import SimpleNamespace
import unittest

from tools.unreal_mcp import blueprint_editor_context as context


PROJECT = "C:/owned/DisposableMCPR9.uproject"


class NamedObject:
    def __init__(self, path):
        self.path = path

    def get_path_name(self):
        return self.path


class Fixture:
    """Expose only getters: mutation, asset and module APIs are unavailable."""

    def __init__(self):
        self.calls = []
        self.project = PROJECT
        self.version = context.SUPPORTED_ENGINE_VERSION
        self.is_editor = True
        self.pie = False
        self.level = None
        self.editor_world = None
        self.game_world = None
        self.level_error = None
        self.level_token = object()
        self.editor_token = object()
        self.les = SimpleNamespace(is_in_play_in_editor=lambda: self.pie, get_current_level=self.get_level)
        self.editor = SimpleNamespace(get_editor_world=lambda: self.editor_world,
                                      get_game_world=lambda: self.game_world)
        self.api = SimpleNamespace(
            is_editor=lambda: self.is_editor,
            SystemLibrary=SimpleNamespace(get_engine_version=lambda: self.version),
            Paths=SimpleNamespace(get_project_file_path=lambda: self.project,
                                  convert_relative_path_to_full=lambda value: value),
            LevelEditorSubsystem=self.level_token,
            UnrealEditorSubsystem=self.editor_token,
            get_editor_subsystem=self.get_subsystem,
        )

    def get_subsystem(self, token):
        self.calls.append(token)
        if token is self.level_token:
            return self.les
        if token is self.editor_token:
            return self.editor
        raise AssertionError("unexpected subsystem")

    def get_level(self):
        if self.level_error is not None:
            raise self.level_error
        return self.level

    def collect(self):
        return context.collect_context(unreal_api=self.api)


class EditorContextTests(unittest.TestCase):
    def test_asset_only_context_allows_null_editor_world_and_level(self):
        fixture = Fixture()
        facts = fixture.collect()
        before = copy.deepcopy(facts)
        result = context.qualify(facts, "c:\\OWNED\\DisposableMCPR9.uproject")
        self.assertTrue(result["qualified"])
        self.assertEqual(result["qualification_scope"], "EDITOR_CONTEXT_ONLY")
        self.assertIsNone(result["editor_world"])
        self.assertIsNone(result["current_level"])
        self.assertEqual(facts, before)
        self.assertEqual(fixture.calls, [fixture.level_token, fixture.editor_token])

    def test_nonnull_editor_world_and_level_are_also_valid(self):
        fixture = Fixture()
        fixture.editor_world = NamedObject("/Temp/Untitled.Untitled")
        fixture.level = NamedObject("/Temp/Untitled.Untitled:PersistentLevel")
        self.assertTrue(context.qualify(fixture.collect(), PROJECT)["qualified"])

    def test_missing_level_editor_is_actionable_hold_before_blueprint_work(self):
        fixture = Fixture()
        fixture.les = None
        facts = fixture.collect()
        self.assertFalse(facts["current_level_checked"])
        with self.assertRaises(context.ContextHold) as caught:
            context.qualify(facts, PROJECT)
        self.assertEqual(caught.exception.stage, "qualify.LevelEditorSubsystem")
        self.assertIn("do not bypass", str(caught.exception))
        self.assertEqual(facts["native_mutation_calls"], 0)

    def test_missing_unreal_editor_does_not_treat_unqueried_game_world_as_safe(self):
        fixture = Fixture()
        fixture.editor = None
        facts = fixture.collect()
        self.assertIsNone(facts["game_world"])
        self.assertFalse(facts["pie_world_checked"])
        with self.assertRaises(context.ContextHold) as caught:
            context.qualify(facts, PROJECT)
        self.assertEqual(caught.exception.stage, "qualify.UnrealEditorSubsystem")

    def test_exact_engine_build_is_required(self):
        facts = Fixture().collect()
        for version in (None, "5.8.3", "5.8.4-58210709+++UE5+Release-5.8",
                        "5.8.3-58210710+++UE5+Release-5.8", "5.8.3-58210709++UE5+Release-5.8"):
            with self.subTest(version=version):
                with self.assertRaises(context.ContextHold):
                    context.qualify({**facts, "engine_version": version}, PROJECT)

    def test_wrong_or_relative_project_identity_is_refused(self):
        facts = Fixture().collect()
        for expected in ("C:/other/DisposableMCPR9.uproject", "DisposableMCPR9.uproject", "C:/owned/other.txt",
                         "C:DisposableMCPR9.uproject", "\\owned\\DisposableMCPR9.uproject"):
            with self.subTest(expected=expected):
                with self.assertRaises(context.ContextHold):
                    context.qualify(facts, expected)
        with self.assertRaises(context.ContextHold):
            context.qualify({**facts, "project_file": "DisposableMCPR9.uproject"}, PROJECT)

    def test_pie_and_nontyped_false_are_refused(self):
        facts = Fixture().collect()
        for pie in (True, None, 0, "false"):
            with self.subTest(pie=pie):
                with self.assertRaises(context.ContextHold):
                    context.qualify({**facts, "level_editor_in_pie": pie}, PROJECT)

    def test_game_world_is_refused_even_when_pie_flag_is_false(self):
        fixture = Fixture()
        fixture.game_world = NamedObject("/Temp/UEDPIE_0_World.World")
        with self.assertRaises(context.ContextHold) as caught:
            context.qualify(fixture.collect(), PROJECT)
        self.assertEqual(caught.exception.stage, "qualify.game_world")

    def test_noneditor_probe_does_not_dereference_editor_subsystems(self):
        fixture = Fixture()
        fixture.is_editor = False
        facts = fixture.collect()
        self.assertEqual(fixture.calls, [])
        with self.assertRaises(context.ContextHold) as caught:
            context.qualify(facts, PROJECT)
        self.assertEqual(caught.exception.stage, "qualify.is_editor")

    def test_empty_getter_exception_retains_type_and_stage_without_retry(self):
        fixture = Fixture()
        fixture.level_error = AssertionError()
        with self.assertRaises(context.ContextHold) as caught:
            fixture.collect()
        self.assertEqual(caught.exception.stage, "collect.current_level")
        self.assertEqual(caught.exception.observed_type, "AssertionError")
        self.assertIn("<empty exception message>", str(caught.exception))
        self.assertEqual(fixture.calls, [fixture.level_token])

    def test_missing_public_api_is_an_actionable_hold(self):
        fixture = Fixture()
        del fixture.api.SystemLibrary
        with self.assertRaises(context.ContextHold) as caught:
            fixture.collect()
        self.assertEqual(caught.exception.stage, "collect.engine_version")
        self.assertEqual(caught.exception.observed_type, "AttributeError")
        self.assertEqual(fixture.calls, [])

    def test_unknown_observations_and_wrong_scope_never_qualify(self):
        facts = Fixture().collect()
        for changes in ({"level_editor_subsystem_truthy": 1}, {"pie_world_checked": False},
                        {"current_level_checked": False}, {"editor_world": ""},
                        {"native_mutation_calls": True}, {"caller_native_admission_required": False}):
            with self.subTest(changes=changes):
                with self.assertRaises(context.ContextHold):
                    context.qualify({**facts, **changes}, PROJECT)
        missing = dict(facts)
        del missing["game_world"]
        with self.assertRaises(context.ContextHold):
            context.qualify(missing, PROJECT)


if __name__ == "__main__":
    unittest.main()
