# SPDX-License-Identifier: MIT
"""Injected-fake diagnostic regressions; no Unreal import or native execution.

Source-only preparation. These cases have not been executed by their author.
"""
from contextlib import contextmanager
import copy
import json
from types import SimpleNamespace
import unittest

from tools.unreal_mcp import blueprint_cdo_diagnostics as diagnostic


PROJECT = "C:/owned/DisposableMCPR6.uproject"
VALUES = '{"AuditValue":37}'


class NamedObject:
    def __init__(self, path):
        self.path = path

    def get_path_name(self):
        return self.path

    def set_editor_property(self, *_args, **_kwargs):
        raise AssertionError("diagnostic wrapper must not write native properties")

    def modify(self, *_args, **_kwargs):
        raise AssertionError("diagnostic wrapper must not modify native objects")


class FakeBlueprint(NamedObject):
    def __init__(self, path, generated):
        super().__init__(path)
        self.generated = generated

    def generated_class(self):
        return self.generated


class FakeActor(NamedObject):
    def __init__(self, path, generated):
        super().__init__(path)
        self.generated = generated
        self.world = None

    def get_class(self):
        return self.generated

    def get_world(self):
        return self.world


class LevelSubsystem:
    def __init__(self):
        self.pie = False
        self.level = NamedObject("/Temp/DiagnosticLevel.DiagnosticLevel:PersistentLevel")

    def is_in_play_in_editor(self):
        return self.pie

    def get_current_level(self):
        return self.level


class EditorSubsystem:
    def __init__(self):
        self.game_world = None

    def get_game_world(self):
        return self.game_world


class RaisingExceptions:
    """Model the official scoped setting, including an initially enabled state."""

    def __init__(self, enabled=False):
        self.enabled = enabled
        self.entered = 0
        self.exited = 0

    @contextmanager
    def __call__(self):
        previous = self.enabled
        self.enabled = True
        self.entered += 1
        try:
            yield
        finally:
            self.enabled = previous
            self.exited += 1


class Fixture:
    """Only the getters and stock methods used by the diagnostic are exposed."""

    def __init__(self, *, raising_enabled=False):
        self.generated = NamedObject(diagnostic.GENERATED_CLASS)
        self.blueprint = FakeBlueprint(diagnostic.OBJECT_PATH, self.generated)
        self.cdo = FakeActor(diagnostic.CDO_PATH, self.generated)
        self.level_subsystem = LevelSubsystem()
        self.editor_subsystem = EditorSubsystem()
        self.actual_project = PROJECT
        self.default = 0
        self.property_flags = {diagnostic.VARIABLE: {"Edit", "BlueprintVisible", "DisableEditOnInstance"}}
        self.original_flags = copy.deepcopy(self.property_flags)
        self.get_calls = []
        self.set_calls = []
        self.get_error = None
        self.set_error = None
        self.set_result = True
        self.partial_write = False
        self.raw_properties = None
        self.raise_if_level_missing = False
        self.raising = RaisingExceptions(raising_enabled)
        self.level_token = object()
        self.editor_token = object()
        self.api = SimpleNamespace(
            Blueprint=FakeBlueprint,
            Actor=FakeActor,
            Paths=SimpleNamespace(
                get_project_file_path=lambda: self.actual_project,
                convert_relative_path_to_full=lambda path: path,
            ),
            LevelEditorSubsystem=self.level_token,
            UnrealEditorSubsystem=self.editor_token,
            get_editor_subsystem=self.get_subsystem,
            get_default_object=self.get_default_object,
        )
        self.object_tools = SimpleNamespace(get_properties=self.get_properties,
                                            set_properties=self.set_properties)

    def get_subsystem(self, subsystem_type):
        if subsystem_type is self.level_token:
            return self.level_subsystem
        if subsystem_type is self.editor_token:
            return self.editor_subsystem
        raise AssertionError("unexpected subsystem lookup")

    def get_default_object(self, generated):
        if generated is not self.generated:
            raise AssertionError("CDO lookup must use the observed generated class")
        return self.cdo

    def get_properties(self, blueprint, properties):
        if not self.raising.enabled:
            raise AssertionError("stock getter requires raising-exceptions scope")
        self.get_calls.append((blueprint, list(properties)))
        if self.get_error is not None:
            raise self.get_error
        if self.raw_properties is not None:
            return self.raw_properties
        return json.dumps({diagnostic.VARIABLE: self.default})

    def set_properties(self, blueprint, values):
        if not self.raising.enabled:
            raise AssertionError("stock setter requires raising-exceptions scope")
        self.set_calls.append((blueprint, values))
        if self.partial_write:
            self.default = 37
        if self.raise_if_level_missing and self.level_subsystem is None:
            raise AssertionError()
        if self.set_error is not None:
            raise self.set_error
        if self.set_result is True:
            self.default = 37
        return self.set_result

    def inspect(self, *, blueprint=None, project=PROJECT):
        return diagnostic.inspect_context(
            self.blueprint if blueprint is None else blueprint,
            project, unreal_api=self.api, object_tools=self.object_tools,
            raising_exceptions=self.raising)

    def set(self, values=VALUES, *, blueprint=None, project=PROJECT):
        return diagnostic.set_properties(
            self.blueprint if blueprint is None else blueprint,
            values, project, unreal_api=self.api, object_tools=self.object_tools,
            raising_exceptions=self.raising)


class BlueprintCDODiagnosticTests(unittest.TestCase):
    def assert_failure(self, callback, *, stage=None, effects="NONE", observed_type=None):
        with self.assertRaises(diagnostic.DiagnosticError) as raised:
            callback()
        error = raised.exception
        self.assertTrue(str(error).strip())
        self.assertEqual(effects, error.effects)
        if stage is not None:
            self.assertEqual(stage, error.stage)
        if observed_type is not None:
            self.assertEqual(observed_type, error.observed_type)
        return error

    def assert_no_setter(self, fixture):
        self.assertEqual([], fixture.set_calls)
        self.assertEqual(fixture.original_flags, fixture.property_flags)

    def test_inspection_returns_owned_context_without_mutation_or_flag_claim(self):
        fixture = Fixture()
        facts = json.loads(fixture.inspect())
        self.assertEqual("codex.blueprint-cdo-diagnostic-context.v1", facts["schema"])
        self.assertEqual(diagnostic.OBJECT_PATH, facts["blueprint"])
        self.assertEqual(diagnostic.GENERATED_CLASS, facts["generated_class"])
        self.assertEqual(diagnostic.CDO_PATH, facts["cdo"])
        self.assertEqual({diagnostic.VARIABLE: 0}, facts["properties"])
        self.assertIsNone(facts["cdo_world"])
        self.assertTrue(facts["level_editor_subsystem_truthy"])
        self.assertTrue(facts["pie_world_checked"])
        self.assertFalse(facts["runtime_qualified"])
        self.assertFalse(facts["runtime_property_flags_observed"])
        self.assertFalse(facts["property_flags_changed"])
        self.assertEqual(0, facts["native_mutation_calls"])
        self.assertEqual([(fixture.blueprint, [diagnostic.VARIABLE])], fixture.get_calls)
        self.assert_no_setter(fixture)

    def test_inspection_accepts_observed_integer_defaults_without_target_assumption(self):
        for value in (0, 37, -9):
            fixture = Fixture()
            fixture.default = value
            with self.subTest(value=value):
                self.assertEqual({diagnostic.VARIABLE: value}, json.loads(fixture.inspect())["properties"])
                self.assert_no_setter(fixture)

    def test_stock_true_is_returned_once_with_unchanged_original_arguments(self):
        fixture = Fixture()
        values = ' { "AuditValue" : 37 } '
        self.assertIs(fixture.set(values), True)
        self.assertEqual([(fixture.blueprint, values)], fixture.set_calls)
        self.assertIs(fixture.set_calls[0][0], fixture.blueprint)
        self.assertIs(fixture.set_calls[0][1], values)
        self.assertEqual(37, fixture.default)
        self.assertEqual(fixture.original_flags, fixture.property_flags)

    def test_bare_stock_assertion_has_nonempty_stage_type_and_unknown_effects(self):
        fixture = Fixture()
        fixture.set_error = AssertionError()
        self.assertEqual("", str(fixture.set_error))
        error = self.assert_failure(fixture.set, stage="stock.ObjectTools.set_properties",
                                    observed_type="AssertionError", effects="UNKNOWN")
        self.assertIn("empty exception message", str(error))
        self.assertIn("reconcile", str(error))
        self.assertIs(error.__cause__, fixture.set_error)
        self.assertEqual(1, len(fixture.set_calls))
        self.assertEqual(1, len(fixture.get_calls))

    def test_nonempty_stock_exception_detail_and_type_survive(self):
        fixture = Fixture()
        fixture.set_error = RuntimeError("stock permission rejected AuditValue")
        error = self.assert_failure(fixture.set, stage="stock.ObjectTools.set_properties",
                                    observed_type="RuntimeError", effects="UNKNOWN")
        self.assertIn("stock permission rejected AuditValue", str(error))
        self.assertEqual(1, len(fixture.set_calls))

    def test_native_wrapped_exception_reports_the_observed_runtime_error_type(self):
        fixture = Fixture()
        fixture.set_error = RuntimeError("AssertionError: ")
        error = self.assert_failure(fixture.set, stage="stock.ObjectTools.set_properties",
                                    observed_type="RuntimeError", effects="UNKNOWN")
        self.assertIn("AssertionError: ", str(error))
        self.assertEqual(1, len(fixture.set_calls))

    def test_false_and_nonboolean_stock_returns_require_reconciliation(self):
        for result in (False, None, 0, 1, "true"):
            fixture = Fixture()
            fixture.set_result = result
            with self.subTest(result=result):
                self.assert_failure(fixture.set, stage="stock.ObjectTools.set_properties.return",
                                    observed_type=type(result).__name__, effects="UNKNOWN")
                self.assertEqual(1, len(fixture.set_calls))
                self.assertEqual(0, fixture.default)
                self.assertEqual(fixture.original_flags, fixture.property_flags)

    def test_false_return_after_partial_write_is_not_treated_as_no_effects(self):
        fixture = Fixture()
        fixture.partial_write = True
        fixture.set_result = False
        self.assert_failure(fixture.set, stage="stock.ObjectTools.set_properties.return",
                            observed_type="bool", effects="UNKNOWN")
        self.assertEqual(37, fixture.default)
        self.assertEqual(1, len(fixture.set_calls))
        self.assertEqual(1, len(fixture.get_calls))
        self.assertEqual(fixture.original_flags, fixture.property_flags)

    def test_partial_write_is_unknown_and_is_neither_rolled_back_nor_retried(self):
        fixture = Fixture()
        fixture.partial_write = True
        fixture.set_error = AssertionError()
        self.assert_failure(fixture.set, stage="stock.ObjectTools.set_properties", effects="UNKNOWN")
        self.assertEqual(37, fixture.default)
        self.assertEqual(1, len(fixture.set_calls))
        self.assertEqual(1, len(fixture.get_calls))
        self.assertEqual(fixture.original_flags, fixture.property_flags)

    def test_scoped_exception_setting_is_restored_on_success_and_failure(self):
        for initial in (False, True):
            for failure in (False, True):
                fixture = Fixture(raising_enabled=initial)
                if failure:
                    fixture.set_error = AssertionError()
                with self.subTest(initial=initial, failure=failure):
                    if failure:
                        self.assert_failure(fixture.set, effects="UNKNOWN")
                    else:
                        self.assertIs(fixture.set(), True)
                    self.assertIs(fixture.raising.enabled, initial)
                    self.assertGreater(fixture.raising.entered, 0)
                    self.assertEqual(fixture.raising.entered, fixture.raising.exited)

    def test_read_failure_has_no_mutation_effects_and_restores_exception_scope(self):
        fixture = Fixture()
        fixture.get_error = AssertionError()
        self.assert_failure(fixture.set, stage="stock.ObjectTools.get_properties",
                            observed_type="AssertionError")
        self.assertFalse(fixture.raising.enabled)
        self.assertEqual(fixture.raising.entered, fixture.raising.exited)
        self.assert_no_setter(fixture)

    def test_missing_level_subsystem_is_reported_without_claiming_prior_cause(self):
        fixture = Fixture()
        fixture.level_subsystem = None
        facts = json.loads(fixture.inspect())
        self.assertFalse(facts["level_editor_subsystem_truthy"])
        self.assertIsNone(facts["level_editor_in_pie"])
        self.assertIsNone(facts["current_level"])
        self.assert_no_setter(fixture)

    def test_missing_level_subsystem_does_not_bypass_stock_assertion(self):
        fixture = Fixture()
        fixture.level_subsystem = None
        fixture.raise_if_level_missing = True
        self.assert_failure(fixture.set, stage="stock.ObjectTools.set_properties",
                            observed_type="AssertionError", effects="UNKNOWN")
        self.assertEqual(1, len(fixture.set_calls))
        self.assertEqual(fixture.original_flags, fixture.property_flags)

    def test_truthy_level_subsystem_with_missing_required_pie_method_stops(self):
        fixture = Fixture()
        fixture.level_subsystem = SimpleNamespace(get_current_level=lambda: None)
        self.assert_failure(fixture.set, observed_type="AttributeError")
        self.assert_no_setter(fixture)

    def test_missing_editor_subsystem_reports_unknown_pie_and_blocks_setter(self):
        fixture = Fixture()
        fixture.editor_subsystem = None
        facts = json.loads(fixture.inspect())
        self.assertFalse(facts["unreal_editor_subsystem_truthy"])
        self.assertFalse(facts["pie_world_checked"])
        self.assertIsNone(facts["game_world"])
        self.assert_failure(fixture.set, stage="guard.pie")
        self.assert_no_setter(fixture)

    def test_world_bound_cdo_is_visible_to_inspection_but_cannot_be_written(self):
        fixture = Fixture()
        fixture.cdo.world = NamedObject("/Temp/ForeignWorld.ForeignWorld")
        facts = json.loads(fixture.inspect())
        self.assertEqual("/Temp/ForeignWorld.ForeignWorld", facts["cdo_world"])
        self.assert_failure(fixture.set, stage="guard.cdo_world")
        self.assert_no_setter(fixture)

    def test_either_pie_observation_blocks_before_stock_dispatch(self):
        for mode in ("level", "world"):
            fixture = Fixture()
            if mode == "level":
                fixture.level_subsystem.pie = True
            else:
                fixture.editor_subsystem.game_world = NamedObject("/Temp/PIEWorld.PIEWorld")
            with self.subTest(mode=mode):
                self.assert_failure(fixture.set, stage="guard.pie")
                self.assert_no_setter(fixture)

    def test_truthy_level_subsystem_requires_an_explicit_boolean_pie_observation(self):
        for observation in (None, 0, 1, "False"):
            fixture = Fixture()
            fixture.level_subsystem.pie = observation
            with self.subTest(observation=observation):
                self.assert_failure(fixture.set, stage="guard.pie")
                self.assert_no_setter(fixture)

    def test_changed_current_default_blocks_replay_without_mutation(self):
        for value in (37, -1):
            fixture = Fixture()
            fixture.default = value
            with self.subTest(value=value):
                self.assert_failure(fixture.set, stage="guard.current_default")
                self.assert_no_setter(fixture)

    def test_exact_project_comparison_normalizes_case_and_separators(self):
        fixture = Fixture()
        facts = json.loads(fixture.inspect(project="c:\\OWNED\\DisposableMCPR6.uproject"))
        self.assertTrue(facts["project_matches_external_expected"])
        self.assertEqual("DisposableMCPR6.uproject", facts["project_basename"])
        self.assert_no_setter(fixture)

    def test_foreign_relative_or_nondisposable_project_never_reaches_stock(self):
        for expected, actual in (("C:/other/DisposableMCPR6.uproject", PROJECT),
                                 ("DisposableMCPR6.uproject", PROJECT),
                                 ("C:/owned/Main.uproject", "C:/owned/Main.uproject")):
            fixture = Fixture()
            fixture.actual_project = actual
            with self.subTest(expected=expected, actual=actual):
                self.assert_failure(lambda: fixture.set(project=expected), stage="guard.project")
                self.assertEqual([], fixture.get_calls)
                self.assert_no_setter(fixture)

    def test_foreign_blueprint_or_path_spoof_never_reaches_stock(self):
        for wrong in (NamedObject(diagnostic.OBJECT_PATH),
                      FakeBlueprint("/Game/Other.BP_CompileReceipt", NamedObject(diagnostic.GENERATED_CLASS))):
            fixture = Fixture()
            with self.subTest(blueprint_type=type(wrong).__name__):
                self.assert_failure(lambda: fixture.set(blueprint=wrong), stage="guard.blueprint")
                self.assertEqual([], fixture.get_calls)
                self.assert_no_setter(fixture)

    def test_wrong_or_missing_generated_class_stops_before_stock(self):
        for generated in (None, NamedObject("/Game/Other.Other_C")):
            fixture = Fixture()
            fixture.blueprint.generated = generated
            with self.subTest(generated=generated):
                self.assert_failure(fixture.set, stage="guard.generated_class")
                self.assertEqual([], fixture.get_calls)
                self.assert_no_setter(fixture)

    def test_cdo_requires_actor_exact_path_and_exact_generated_class(self):
        for mode in ("not_actor", "wrong_path", "wrong_class"):
            fixture = Fixture()
            if mode == "not_actor":
                fixture.cdo = NamedObject(diagnostic.CDO_PATH)
            elif mode == "wrong_path":
                fixture.cdo.path = "/Game/Other.Default__Other_C"
            else:
                fixture.cdo.generated = NamedObject("/Game/Other.Other_C")
            with self.subTest(mode=mode):
                self.assert_failure(fixture.set, stage="guard.cdo")
                self.assertEqual([], fixture.get_calls)
                self.assert_no_setter(fixture)

    def test_proposed_properties_require_unique_exact_integer_target_before_reads(self):
        for values in ('{"AuditValue":true}', '{"AuditValue":0}', '{"Other":37}',
                       '{"AuditValue":37,"Other":1}', '{"AuditValue":37,"AuditValue":37}',
                       '[37]', '{"AuditValue":NaN}', "not JSON", {"AuditValue": 37}):
            fixture = Fixture()
            with self.subTest(values=values):
                self.assert_failure(lambda: fixture.set(values))
                self.assertEqual([], fixture.get_calls)
                self.assert_no_setter(fixture)

    def test_stock_property_result_requires_exact_unique_integer_member(self):
        for raw in ('{"AuditValue":true}', '{"Other":0}', '{"AuditValue":0,"Other":1}',
                    '{"AuditValue":0,"AuditValue":37}', '[0]', '{"AuditValue":NaN}'):
            fixture = Fixture()
            fixture.raw_properties = raw
            with self.subTest(raw=raw):
                self.assert_failure(fixture.set)
                self.assert_no_setter(fixture)


if __name__ == "__main__":
    unittest.main()
