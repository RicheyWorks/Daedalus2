# SPDX-License-Identifier: MIT
"""Offline orchestration contracts using injected stock-tool and Unreal fakes.

Only context collection/qualification are mocked: the context helper has its
own tests. This file never imports Unreal or performs editor/network work.
The author prepared these tests without executing them.
"""
import copy
from contextlib import contextmanager
import json
from types import SimpleNamespace
import unittest
from unittest.mock import call, patch

from tools.unreal_mcp import blueprint_acceptance as acceptance


PROJECT = "C:/owned/BlueprintAcceptance.uproject"
UP_TO_DATE = "BS_UP_TO_DATE"
COMPILE_ERROR = "BS_ERROR"
OTHER_CONTENT = "/Game/OtherTeam/KeepMyUnsavedAsset"
OTHER_MAP = "/Game/OtherTeam/KeepMyUnsavedMap"
ACTOR_UCLASS = object()


class NamedObject:
    def __init__(self, path):
        self.path = path

    def get_path_name(self):
        return self.path


class FakeActor(NamedObject):
    @staticmethod
    def static_class():
        return ACTOR_UCLASS

    def get_world(self):
        return None


class FakeBlueprint(NamedObject):
    def __init__(self):
        super().__init__(acceptance.OBJECT)
        self.value = 0
        self.status = "BS_DIRTY"
        self.generated = NamedObject(acceptance.OBJECT + "_C")

    def generated_class(self):
        return self.generated

    def get_editor_property(self, name):
        if name != "status":
            raise AssertionError("unexpected Blueprint property: " + name)
        return self.status


class Fixture:
    """Small stateful tool surface; unsupported APIs are deliberately absent."""

    def __init__(self):
        self.bp = FakeBlueprint()
        self.cdo = FakeActor(acceptance.OBJECT + "_C:Default__BP_CompileReceipt_C")
        self.context = {"qualified_test_context": True}
        self.events = []
        self.records = []
        self.exists = False
        self.dirty_content = []
        self.dirty_maps = []
        self.active_exception_scope = 0
        self.compile_calls = []
        self.compile_effects = {}
        self.compile_errors = {}
        self.setter_calls = 0
        self.setter_result = True
        self.setter_error = None
        self.setter_changes_before_error = False
        self.save_calls = 0
        self.save_result = True
        self.save_error = None
        self.leave_owned_dirty = False
        self.after_save_values = {}
        self.after_save_dirty_content = []
        self.after_save_dirty_maps = []
        self.load_error = None
        self.property_response = None
        self.api = SimpleNamespace(
            Blueprint=FakeBlueprint,
            Actor=FakeActor,
            BlueprintStatus=SimpleNamespace(BS_UP_TO_DATE=UP_TO_DATE),
            get_default_object=self.get_default_object,
            find_object=self.find_object,
            EditorAssetLibrary=SimpleNamespace(
                does_asset_exist=self.does_asset_exist,
                save_loaded_asset=self.save_loaded_asset,
                load_asset=self.load_asset,
            ),
            EditorLoadingAndSavingUtils=SimpleNamespace(
                get_dirty_content_packages=lambda: list(self.dirty_content),
                get_dirty_map_packages=lambda: list(self.dirty_maps),
            ),
        )
        self.blueprints = SimpleNamespace(
            create=self.create,
            add_variable=self.add_variable,
            compile_blueprint=self.compile_blueprint,
        )
        self.objects = SimpleNamespace(
            get_properties=self.get_properties,
            set_properties=self.set_properties,
        )

    @contextmanager
    def raising_exceptions(self):
        self.active_exception_scope += 1
        try:
            yield
        finally:
            self.active_exception_scope -= 1

    def require_exception_scope(self):
        if self.active_exception_scope != 1:
            raise AssertionError("stock operation must use the strict exception scope")

    def record(self, stage, payload):
        self.records.append((stage, copy.deepcopy(payload)))

    def does_asset_exist(self, package):
        self.events.append(("exists", package))
        return self.exists

    def create(self, folder, name, parent):
        self.require_exception_scope()
        if parent is not ACTOR_UCLASS:
            raise TypeError("factory requires the reflected Actor UClass, not its Python type")
        self.events.append(("create", folder, name, parent))
        self.exists = True
        self.dirty_content = [NamedObject(acceptance.PACKAGE)]
        return self.bp

    def add_variable(self, bp, variable, kind):
        self.require_exception_scope()
        self.events.append(("add_variable", bp, variable, kind))
        self.bp.value = 0
        self.bp.status = "BS_DIRTY"

    def compile_blueprint(self, bp, *, warnings_as_errors):
        self.require_exception_scope()
        self.events.append(("compile", bp, warnings_as_errors))
        self.compile_calls.append((bp, warnings_as_errors))
        error = self.compile_errors.get(len(self.compile_calls))
        if error is not None:
            raise error
        self.bp.status = UP_TO_DATE
        for name, value in self.compile_effects.get(len(self.compile_calls), {}).items():
            setattr(self.bp, name, value)

    def get_default_object(self, generated):
        if generated is not self.bp.generated:
            raise AssertionError("unexpected generated class")
        return self.cdo

    def get_properties(self, bp, properties):
        self.require_exception_scope()
        self.events.append(("get_properties", bp, tuple(properties)))
        if self.property_response is not None:
            return self.property_response
        return json.dumps({acceptance.VARIABLE: self.bp.value})

    def set_properties(self, bp, payload):
        self.require_exception_scope()
        values = json.loads(payload)
        self.events.append(("set_properties", bp, values))
        self.setter_calls += 1
        if self.setter_error is not None:
            if self.setter_changes_before_error:
                self.bp.value = values[acceptance.VARIABLE]
            raise self.setter_error
        self.bp.value = values[acceptance.VARIABLE]
        self.bp.status = "BS_DIRTY"
        return self.setter_result

    def find_object(self, outer, path):
        self.events.append(("find", outer, path))
        return self.bp

    def save_loaded_asset(self, bp, *, only_if_is_dirty):
        self.require_exception_scope()
        self.events.append(("save", bp, only_if_is_dirty))
        self.save_calls += 1
        if self.save_error is not None:
            raise self.save_error
        if not self.leave_owned_dirty:
            self.dirty_content = [p for p in self.dirty_content
                                  if p.get_path_name() != acceptance.PACKAGE]
        self.dirty_content.extend(NamedObject(p) for p in self.after_save_dirty_content)
        self.dirty_maps.extend(NamedObject(p) for p in self.after_save_dirty_maps)
        for name, value in self.after_save_values.items():
            setattr(self.bp, name, value)
        return self.save_result

    def load_asset(self, path):
        self.require_exception_scope()
        self.events.append(("load", path))
        if self.load_error is not None:
            raise self.load_error
        return self.bp

    def admit(self, *, value=37, status=UP_TO_DATE, dirty=True):
        self.exists = True
        self.bp.value = value
        self.bp.status = status
        self.dirty_content = [NamedObject(acceptance.PACKAGE)] if dirty else []

    def operation_names(self):
        return [event[0] for event in self.events]

    def record_names(self):
        return [stage for stage, _ in self.records]


class BlueprintAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        collect = patch.object(
            acceptance, "collect_context", side_effect=lambda **kwargs: self.fx.context)
        qualify = patch.object(
            acceptance, "qualify", side_effect=lambda context, project: context)
        self.collect = collect.start()
        self.qualify = qualify.start()
        self.addCleanup(collect.stop)
        self.addCleanup(qualify.stop)

    def create(self):
        return acceptance.create_edit_compile(
            unreal_api=self.fx.api,
            blueprint_tools=self.fx.blueprints,
            object_tools=self.fx.objects,
            raising_exceptions=self.fx.raising_exceptions,
            expected_project_file=PROJECT,
            record=self.fx.record,
        )

    def save(self):
        return acceptance.save_exact(
            unreal_api=self.fx.api,
            object_tools=self.fx.objects,
            raising_exceptions=self.fx.raising_exceptions,
            expected_project_file=PROJECT,
            record=self.fx.record,
        )

    def readback(self):
        return acceptance.fresh_readback(
            unreal_api=self.fx.api,
            object_tools=self.fx.objects,
            raising_exceptions=self.fx.raising_exceptions,
            expected_project_file=PROJECT,
            record=self.fx.record,
        )

    def assert_hold(self, operation, stage, effects="UNKNOWN"):
        with self.assertRaises(acceptance.AcceptanceHold) as caught:
            operation()
        self.assertEqual(caught.exception.stage, stage)
        self.assertEqual(caught.exception.effects, effects)
        self.assertEqual(self.fx.active_exception_scope, 0)
        return caught.exception

    def test_existing_destination_refuses_before_create_or_any_save(self):
        self.fx.exists = True
        self.assert_hold(self.create, "pre_create", "NONE")
        self.assertEqual(self.fx.operation_names(), ["exists"])
        self.assertEqual(self.fx.records, [])
        self.assertEqual(self.fx.setter_calls, 0)
        self.assertEqual(self.fx.save_calls, 0)
        self.collect.assert_called_once_with(unreal_api=self.fx.api)
        self.qualify.assert_called_once_with(self.fx.context, PROJECT)

    def test_dirty_work_refuses_before_create(self):
        for which in ("content", "map"):
            with self.subTest(which=which):
                self.fx = Fixture()
                if which == "content":
                    self.fx.dirty_content = [NamedObject(OTHER_CONTENT)]
                else:
                    self.fx.dirty_maps = [NamedObject(OTHER_MAP)]
                self.assert_hold(self.create, "pre_create", "NONE")
                self.assertEqual(self.fx.operation_names(), ["exists"])
                self.assertEqual(self.fx.save_calls, 0)

    def test_success_uses_stock_zero_to_target_sequence_with_strict_compiles_and_no_save(self):
        result = self.create()
        self.assertEqual(self.fx.operation_names(), [
            "exists", "create", "add_variable", "compile", "get_properties",
            "set_properties", "compile", "get_properties",
        ])
        self.assertEqual(self.fx.events[1],
                         ("create", acceptance.FOLDER, acceptance.NAME, ACTOR_UCLASS))
        self.assertEqual(self.fx.events[2],
                         ("add_variable", self.fx.bp, acceptance.VARIABLE, "int"))
        self.assertEqual(self.fx.compile_calls, [(self.fx.bp, True), (self.fx.bp, True)])
        self.assertEqual(self.fx.events[5],
                         ("set_properties", self.fx.bp, {acceptance.VARIABLE: 37}))
        self.assertEqual(self.fx.record_names(), [
            "context_qualified_before_create", "created_unsaved", "compiled_zero",
            "stock_setter_dispatch", "compiled_target_unsaved",
        ])
        self.assertEqual(self.fx.records[2][1]["value"], 0)
        self.assertEqual(self.fx.records[4][1]["value"], 37)
        self.assertEqual(result["value"], 37)
        self.assertIs(result["up_to_date"], True)
        self.assertEqual(result["object"], acceptance.OBJECT)
        self.assertEqual(self.fx.setter_calls, 1)
        self.assertEqual(self.fx.save_calls, 0)
        self.assertEqual([p.get_path_name() for p in self.fx.dirty_content],
                         [acceptance.PACKAGE])
        self.assertEqual(self.collect.call_args_list,
                         [call(unreal_api=self.fx.api), call(unreal_api=self.fx.api)])
        self.assertEqual(self.qualify.call_args_list,
                         [call(self.fx.context, PROJECT), call(self.fx.context, PROJECT)])

    def test_create_passes_reflected_actor_uclass_and_factory_rejects_python_type(self):
        self.assertIs(FakeActor.static_class(), ACTOR_UCLASS)
        self.assertIsNot(ACTOR_UCLASS, FakeActor)
        with self.fx.raising_exceptions():
            with self.assertRaisesRegex(TypeError, "reflected Actor UClass"):
                self.fx.create(acceptance.FOLDER, acceptance.NAME, FakeActor)
        self.assertFalse(self.fx.exists)
        self.assertEqual(self.fx.events, [])
        self.assertEqual(self.fx.dirty_content, [])

        self.create()
        creates = [event for event in self.fx.events if event[0] == "create"]
        self.assertEqual(len(creates), 1)
        self.assertIs(creates[0][3], ACTOR_UCLASS)
        self.assertEqual(self.fx.save_calls, 0)

    def test_nonzero_initial_compilation_refuses_before_stock_setter(self):
        self.fx.compile_effects[1] = {"value": 1}
        self.assert_hold(self.create, "compiled_zero")
        self.assertEqual(len(self.fx.compile_calls), 1)
        self.assertEqual(self.fx.setter_calls, 0)
        self.assertEqual(self.fx.save_calls, 0)

    def test_bad_initial_compile_status_refuses_before_stock_setter(self):
        self.fx.compile_effects[1] = {"status": COMPILE_ERROR}
        self.assert_hold(self.create, "compiled_zero")
        self.assertEqual(self.fx.setter_calls, 0)
        self.assertEqual(self.fx.save_calls, 0)

    def test_strict_compile_exception_stops_without_retry_or_save(self):
        for number, stage in ((1, "compile_zero"), (2, "compile_target")):
            with self.subTest(compile_number=number):
                self.fx = Fixture()
                error = RuntimeError("strict compiler rejected warning or error")
                self.fx.compile_errors[number] = error
                hold = self.assert_hold(self.create, stage)
                self.assertIs(hold.__cause__, error)
                self.assertEqual(len(self.fx.compile_calls), number)
                self.assertTrue(all(strict is True for _, strict in self.fx.compile_calls))
                self.assertEqual(self.fx.setter_calls, number - 1)
                self.assertEqual(self.fx.save_calls, 0)

    def test_stock_setter_exception_is_unknown_even_if_it_partially_changed_the_value(self):
        for changed in (False, True):
            with self.subTest(partial_change=changed):
                self.fx = Fixture()
                self.fx.setter_error = RuntimeError("stock editability guard rejected property")
                self.fx.setter_changes_before_error = changed
                hold = self.assert_hold(self.create, "stock_setter")
                self.assertIs(hold.__cause__, self.fx.setter_error)
                self.assertEqual(self.fx.setter_calls, 1)
                self.assertEqual(len(self.fx.compile_calls), 1)
                self.assertEqual(self.fx.save_calls, 0)
                self.assertEqual(self.fx.bp.value, 37 if changed else 0)
                self.assertEqual(self.fx.record_names()[-1], "stock_setter_dispatch")
                self.assertEqual([p.get_path_name() for p in self.fx.dirty_content],
                                 [acceptance.PACKAGE])

    def test_stock_setter_requires_literal_true_without_retry_or_save(self):
        for value in (False, None, 0, 1, "true"):
            with self.subTest(returned=value):
                self.fx = Fixture()
                self.fx.setter_result = value
                self.assert_hold(self.create, "stock_setter")
                self.assertEqual(self.fx.setter_calls, 1)
                self.assertEqual(len(self.fx.compile_calls), 1)
                self.assertEqual(self.fx.save_calls, 0)

    def test_wrong_target_compiled_value_refuses_unsaved(self):
        self.fx.compile_effects[2] = {"value": 36}
        self.assert_hold(self.create, "compiled_target")
        self.assertEqual(self.fx.setter_calls, 1)
        self.assertEqual(len(self.fx.compile_calls), 2)
        self.assertEqual(self.fx.save_calls, 0)

    def test_wrong_target_compile_status_refuses_unsaved(self):
        self.fx.compile_effects[2] = {"status": COMPILE_ERROR}
        self.assert_hold(self.create, "compiled_target")
        self.assertEqual(self.fx.setter_calls, 1)
        self.assertEqual(self.fx.save_calls, 0)

    def test_property_readback_rejects_boolean_instead_of_integer(self):
        self.fx.property_response = json.dumps({acceptance.VARIABLE: True})
        self.assert_hold(self.create, "read_default")
        self.assertEqual(self.fx.setter_calls, 0)
        self.assertEqual(self.fx.save_calls, 0)

    def test_exact_save_refuses_unrelated_content_or_map(self):
        for which in ("content", "map"):
            with self.subTest(which=which):
                self.fx = Fixture()
                self.fx.admit()
                if which == "content":
                    self.fx.dirty_content.append(NamedObject(OTHER_CONTENT))
                else:
                    self.fx.dirty_maps.append(NamedObject(OTHER_MAP))
                self.assert_hold(self.save, "pre_save")
                self.assertEqual(self.fx.save_calls, 0)
                self.assertNotIn("exact_save_dispatch", self.fx.record_names())

    def test_exact_save_requires_compiled_target_before_dispatch(self):
        for value, status in ((0, UP_TO_DATE), (37, COMPILE_ERROR)):
            with self.subTest(value=value, status=status):
                self.fx = Fixture()
                self.fx.admit(value=value, status=status)
                self.assert_hold(self.save, "pre_save")
                self.assertEqual(self.fx.save_calls, 0)

    def test_exact_save_returns_literal_true_and_verified_readback_without_fresh_process_claim(self):
        self.fx.admit()
        result = self.save()
        self.assertEqual(self.fx.operation_names(),
                         ["find", "get_properties", "save", "get_properties"])
        self.assertEqual(self.fx.events[2], ("save", self.fx.bp, True))
        self.assertEqual(self.fx.save_calls, 1)
        self.assertIs(result["saved"], True)
        self.assertEqual(result["value"], 37)
        self.assertIs(result["up_to_date"], True)
        self.assertEqual(result["dirty_after"], [])
        self.assertIs(result["fresh_process_reopen"], False)
        self.assertIs(result["property_flags_changed"], False)
        self.assertEqual(self.fx.record_names(),
                         ["exact_save_dispatch", "post_save_observation", "exact_saved_readback"])
        self.assertEqual(self.fx.setter_calls, 0)
        self.assertEqual(self.fx.compile_calls, [])

    def test_exact_save_rejects_nonliteral_true_without_retry(self):
        for value in (False, None, 0, 1, "true"):
            with self.subTest(returned=value):
                self.fx = Fixture()
                self.fx.admit()
                self.fx.save_result = value
                self.assert_hold(self.save, "exact_save")
                self.assertEqual(self.fx.save_calls, 1)
                self.assertEqual(self.fx.record_names(), ["exact_save_dispatch"])

    def test_exact_save_exception_preserves_unknown_and_does_not_retry(self):
        self.fx.admit()
        self.fx.save_error = RuntimeError("save response unavailable")
        hold = self.assert_hold(self.save, "exact_save")
        self.assertIs(hold.__cause__, self.fx.save_error)
        self.assertEqual(self.fx.save_calls, 1)
        self.assertEqual(self.fx.record_names(), ["exact_save_dispatch"])

    def test_exact_save_rejects_value_drift_after_successful_save(self):
        self.fx.admit()
        self.fx.after_save_values = {"value": 36}
        self.assert_hold(self.save, "post_save")
        self.assertEqual(self.fx.save_calls, 1)
        self.assertEqual(self.fx.record_names(), ["exact_save_dispatch", "post_save_observation"])

    def test_exact_save_rejects_compile_status_drift_after_successful_save(self):
        self.fx.admit()
        self.fx.after_save_values = {"status": COMPILE_ERROR}
        self.assert_hold(self.save, "post_save")
        self.assertEqual(self.fx.save_calls, 1)
        self.assertEqual(self.fx.record_names(), ["exact_save_dispatch", "post_save_observation"])

    def test_exact_save_rejects_owned_package_remaining_dirty(self):
        self.fx.admit()
        self.fx.leave_owned_dirty = True
        self.assert_hold(self.save, "post_save")
        self.assertEqual(self.fx.save_calls, 1)
        self.assertEqual(self.fx.record_names(), ["exact_save_dispatch", "post_save_observation"])

    def test_exact_save_rejects_new_dirty_content_or_map_after_save(self):
        for which in ("content", "map"):
            with self.subTest(which=which):
                self.fx = Fixture()
                self.fx.admit()
                if which == "content":
                    self.fx.after_save_dirty_content = [OTHER_CONTENT]
                else:
                    self.fx.after_save_dirty_maps = [OTHER_MAP]
                self.assert_hold(self.save, "post_save")
                self.assertEqual(self.fx.save_calls, 1)
                self.assertEqual(self.fx.record_names(),
                                 ["exact_save_dispatch", "post_save_observation"])

    def test_fresh_readback_requires_saved_compiled_target_and_defers_process_proof_to_caller(self):
        self.fx.admit(dirty=False)
        result = self.readback()
        self.assertEqual(self.fx.operation_names(), ["load", "get_properties"])
        self.assertEqual(self.fx.events[0], ("load", acceptance.OBJECT))
        self.assertEqual(result["value"], 37)
        self.assertIs(result["up_to_date"], True)
        self.assertIs(result["fresh_process_identity_requires_caller_proof"], True)
        self.assertEqual(self.fx.record_names(), ["saved_asset_readback"])
        self.assertEqual(self.fx.setter_calls, 0)
        self.assertEqual(self.fx.save_calls, 0)

    def test_fresh_readback_refuses_wrong_value_or_status(self):
        for value, status in ((0, UP_TO_DATE), (37, COMPILE_ERROR)):
            with self.subTest(value=value, status=status):
                self.fx = Fixture()
                self.fx.admit(value=value, status=status, dirty=False)
                self.assert_hold(self.readback, "fresh_readback", "READ_ONLY")
                self.assertEqual(self.fx.records, [])
                self.assertEqual(self.fx.save_calls, 0)

    def test_fresh_readback_requires_clean_content_and_maps(self):
        for which in ("content", "map"):
            with self.subTest(which=which):
                self.fx = Fixture()
                self.fx.admit(dirty=False)
                if which == "content":
                    self.fx.dirty_content = [NamedObject(OTHER_CONTENT)]
                else:
                    self.fx.dirty_maps = [NamedObject(OTHER_MAP)]
                self.assert_hold(self.readback, "fresh_readback", "READ_ONLY")
                self.assertEqual(self.fx.records, [])
                self.assertEqual(self.fx.save_calls, 0)

    def test_fresh_load_failure_is_read_only_and_never_creates_or_saves(self):
        self.fx.admit(dirty=False)
        self.fx.load_error = RuntimeError("asset unavailable")
        hold = self.assert_hold(self.readback, "load_owned_saved", "READ_ONLY")
        self.assertIs(hold.__cause__, self.fx.load_error)
        self.assertEqual(self.fx.operation_names(), ["load"])
        self.assertEqual(self.fx.records, [])
        self.assertEqual(self.fx.save_calls, 0)


if __name__ == "__main__":
    unittest.main()
