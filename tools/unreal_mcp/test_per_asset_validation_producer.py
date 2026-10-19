# SPDX-License-Identifier: MIT
"""Portable injected native-output fixtures; no Unreal import or execution."""
from contextlib import nullcontext
from enum import Enum
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from tools.unreal_mcp import per_asset_validation_producer as producer


PROJECT = "C:/owned/DisposableMCPR8.uproject"  # A literal guard fixture, never opened.


class Result(Enum):
    INVALID = 0
    VALID = 1
    NOT_VALIDATED = 2


class Text:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


class Object:
    def __init__(self, path=producer.FIXTURE_OBJECT_PATH):
        self.path = path

    def get_path_name(self):
        return self.path


class Fixture:
    def __init__(self, result=Result.VALID, errors=(), warnings=()):
        self.asset = Object()
        self.subsystem = SimpleNamespace(
            get_class=lambda: Object("/Script/DataValidation.EditorValidatorSubsystem"),
            is_object_valid=Mock(return_value=(result, list(errors), list(warnings))))
        self.editor = SimpleNamespace(get_game_world=Mock(return_value=None))
        self.editor_type, self.validator_type = object(), object()
        self.api = SimpleNamespace(
            Object=Object, Array=list, Text=Text, DataValidationResult=Result,
            DataValidationUsecase=SimpleNamespace(SCRIPT=object()),
            UnrealEditorSubsystem=self.editor_type, EditorValidatorSubsystem=self.validator_type,
            Paths=SimpleNamespace(get_project_file_path=lambda: PROJECT,
                                  convert_relative_path_to_full=lambda value: value),
            get_editor_subsystem=self.get_subsystem)

    def get_subsystem(self, kind):
        return self.editor if kind is self.editor_type else self.subsystem

    def call(self, project=PROJECT, usecase="Script"):
        return json.loads(producer.validate_object(self.asset, project, usecase,
            unreal_api=self.api, raising_exceptions=nullcontext))


class PerAssetValidationProducerTests(unittest.TestCase):
    def test_one_real_api_shape_retains_valid_result_without_native_qualification(self):
        fixture = Fixture()
        report = fixture.call()
        fixture.subsystem.is_object_valid.assert_called_once_with(fixture.asset, fixture.api.DataValidationUsecase.SCRIPT)
        self.assertTrue(report["accepted"])
        self.assertEqual(report["result"], "Valid")
        self.assertEqual(report["counts"]["valid"], 1)
        self.assertIn("producer-derived", report["counts_origin"])
        self.assertFalse(report["native_runtime_qualified"])
        self.assertFalse(report["native_aggregate_results_captured"])

    def test_invalid_retains_exact_errors_not_boolean_coercion(self):
        report = Fixture(Result.INVALID, [Text("native invalid: α"), "second issue"]).call()
        self.assertFalse(report["accepted"])
        self.assertEqual(report["errors"], ["native invalid: α", "second issue"])
        self.assertEqual(report["counts"]["invalid"], 1)
        self.assertEqual(report["counts"]["error_messages"], 2)

    def test_valid_with_warning_or_error_never_passes(self):
        for errors, warnings in (([], [Text("native warning")]), (["error despite enum"], [])):
            with self.subTest(errors=errors, warnings=warnings):
                report = Fixture(Result.VALID, errors, warnings).call()
                self.assertFalse(report["accepted"])
                self.assertEqual(report["counts"]["valid"], 1)

    def test_not_validated_is_explicit_nonpass_even_without_messages(self):
        report = Fixture(Result.NOT_VALIDATED).call()
        self.assertFalse(report["accepted"])
        self.assertEqual(report["result"], "NotValidated")
        self.assertEqual(report["counts"]["not_validated"], 1)

    def test_tuple_output_order_is_result_then_errors_then_warnings(self):
        report = Fixture(Result.INVALID, ["error-first"], ["warning-second"]).call()
        self.assertEqual(report["errors"], ["error-first"])
        self.assertEqual(report["warnings"], ["warning-second"])

    def test_foreign_main_relative_project_and_wrong_usecase_reject_before_validation(self):
        for project, usecase in (("C:/main/Main.uproject", "Script"),
                                  ("DisposableMCPR8.uproject", "Script"),
                                  ("C:/other/DisposableMCPR8.uproject", "Script"), (PROJECT, "Save")):
            fixture = Fixture()
            with self.subTest(project=project, usecase=usecase), self.assertRaises(producer.ValidationProducerError):
                fixture.call(project, usecase)
            fixture.subsystem.is_object_valid.assert_not_called()

    def test_foreign_asset_or_pie_rejects_before_validation(self):
        for foreign, pie in ((True, False), (False, True)):
            fixture = Fixture()
            if foreign:
                fixture.asset.path = "/Game/Production/Foreign.Foreign"
            if pie:
                fixture.editor.get_game_world.return_value = object()
            with self.subTest(foreign=foreign, pie=pie), self.assertRaises(producer.ValidationProducerError):
                fixture.call()
            fixture.subsystem.is_object_valid.assert_not_called()

    def test_unavailable_or_custom_subsystem_rejects_before_validation(self):
        for custom in (False, True):
            fixture = Fixture()
            original = fixture.subsystem
            if custom:
                original.get_class = lambda: Object("/Script/Other.CustomValidationSubsystem")
            else:
                fixture.subsystem = None
            with self.subTest(custom=custom), self.assertRaises(producer.ValidationProducerError):
                fixture.call()
            original.is_object_valid.assert_not_called()

    def test_unknown_binding_shape_enum_or_issue_member_never_passes_or_retries(self):
        variants = (None, Result.VALID, (Result.VALID, []),
                    (True, [], []), (Result.VALID, "not-an-array", []),
                    (Result.VALID, [object()], []))
        for value in variants:
            fixture = Fixture()
            fixture.subsystem.is_object_valid.return_value = value
            with self.subTest(value=value), self.assertRaises(producer.ValidationProducerError) as raised:
                fixture.call()
            self.assertEqual(raised.exception.effects, "UNKNOWN")
            fixture.subsystem.is_object_valid.assert_called_once()

    def test_empty_native_exception_is_nonempty_unknown_effects_and_no_retry(self):
        fixture = Fixture()
        fixture.subsystem.is_object_valid.side_effect = TimeoutError()
        with self.assertRaises(producer.ValidationProducerError) as raised:
            fixture.call()
        self.assertEqual(raised.exception.effects, "UNKNOWN")
        self.assertIn("TimeoutError", str(raised.exception))
        self.assertIn("<empty exception message>", str(raised.exception))
        fixture.subsystem.is_object_valid.assert_called_once()

    def test_asset_identity_change_after_validation_cannot_pass(self):
        fixture = Fixture()
        def changed(_asset, _usecase):
            fixture.asset.path = "/Game/Elsewhere.Elsewhere"
            return Result.VALID, [], []
        fixture.subsystem.is_object_valid.side_effect = changed
        with self.assertRaises(producer.ValidationProducerError) as raised:
            fixture.call()
        self.assertEqual(raised.exception.effects, "UNKNOWN")
        fixture.subsystem.is_object_valid.assert_called_once()


if __name__ == "__main__":
    unittest.main()
