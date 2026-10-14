# SPDX-License-Identifier: MIT
"""Offline doctor readback contracts; no sockets, editor or settings writes.

Run: python -B -m unittest tools.unreal_mcp.test_doctor
"""
import copy
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tools.unreal_mcp import doctor


GET = "GetSectionPropertyValues"
SET = "SetSectionProperties"


def wanted_sections():
    sections = {}
    for (section, prop), (value, _reason) in doctor.WANT.items():
        sections.setdefault(section, {})[prop] = copy.deepcopy(value)
    return sections


class FakeMcp:
    """In-memory settings and exact native-call records, with scripted failures."""

    def __init__(self, values=None, *, as_json=True, reads=None, setter=None,
                 set_response=True):
        self.values = copy.deepcopy(values if values is not None else wanted_sections())
        self.as_json = as_json
        self.reads = {section: list(results) for section, results in (reads or {}).items()}
        self.setter = setter
        self.set_response = set_response
        self.calls = []

    def call(self, toolset, tool, **args):
        self.calls.append((toolset, tool, copy.deepcopy(args)))
        if toolset != doctor.TS or tool not in (GET, SET):
            raise AssertionError("doctor used an unexpected tool")
        if args.get("containerName") != "Editor" or args.get("categoryName") != "General":
            raise AssertionError("doctor used an unexpected settings target")
        section = args["sectionName"]
        if tool == GET:
            if self.reads.get(section):
                result = self.reads[section].pop(0)
                if isinstance(result, BaseException):
                    raise result
                return copy.deepcopy(result)
            result = {prop: copy.deepcopy(self.values[section][prop])
                      for prop in args["propertyNames"] if prop in self.values[section]}
            return json.dumps(result) if self.as_json else result
        properties = json.loads(args["propertiesJson"])
        if self.setter is not None:
            return self.setter(self, section, properties)
        self.values[section].update(properties)
        return self.set_response

    def get_calls(self):
        return [args for _toolset, tool, args in self.calls if tool == GET]

    def set_calls(self):
        return [args for _toolset, tool, args in self.calls if tool == SET]


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.original_want = copy.deepcopy(doctor.WANT)
        self.sections = wanted_sections()
        self.section_names = list(self.sections)
        self.first, self.second = self.section_names
        self.bool_prop = "bThrottleCPUWhenNotForeground"
        self.int_prop = "autoSaveTimeMinutes"

    def tearDown(self):
        self.assertEqual(doctor.WANT, self.original_want, "doctor mutated its wanted settings")
        self.assertEqual(repr(doctor.WANT), repr(self.original_want),
                         "doctor changed a wanted setting's exact type")

    def run_main(self, fake=None, argv=(), *, ready=True, factory_error=None):
        fake = fake if fake is not None else FakeMcp()
        output = io.StringIO()
        # Both entry points are patched before main: no real client can be initialized.
        with patch.object(doctor, "ready", return_value=ready) as readiness, \
                patch.object(doctor, "Mcp", return_value=fake, side_effect=factory_error) as factory, \
                redirect_stdout(output):
            result = doctor.main(list(argv))
        self.assertIs(type(result), int)
        return result, output.getvalue(), readiness, factory

    def assert_failed(self, result, output):
        self.assertEqual(result, 1)
        self.assertNotIn("MCP READY", output)

    def assert_read_passes(self, fake, count):
        expected = [{"containerName": "Editor", "categoryName": "General",
                     "sectionName": section, "propertyNames": list(props)}
                    for section, props in self.sections.items()]
        self.assertEqual(fake.get_calls(), expected * count)

    def changed_both_sections(self):
        values = copy.deepcopy(self.sections)
        values[self.first][self.bool_prop] = True
        values[self.second][self.int_prop] = 10
        return values

    def test_existing_wanted_settings_policy_is_preserved(self):
        expected = {
            ("EditorPerformanceSettings", "bThrottleCPUWhenNotForeground"): False,
            ("EditorPerformanceSettings", "bAllowSlateThrottling"): False,
            ("LoadingSaving", "bMonitorContentDirectories"): False,
            ("LoadingSaving", "bPromptBeforeAutoImporting"): False,
            ("LoadingSaving", "bAutoDeleteAssets"): False,
            ("LoadingSaving", "bDetectChangesOnStartup"): False,
            ("LoadingSaving", "autoSaveTimeMinutes"): 30,
            ("LoadingSaving", "autoSaveWarningInSeconds"): 0,
            ("LoadingSaving", "bPromptForCheckoutOnAssetModification"): False,
            ("LoadingSaving", "restoreOpenAssetTabsOnRestart"): "NeverRestore",
            ("EditorPerformanceSettings", "bEnableNotifications"): False,
            ("EditorPerformanceSettings", "bMonitorEditorPerformance"): False,
            ("EditorPerformanceSettings", "bEnableScalabilityWarningIndicator"): False,
        }
        self.assertEqual(set(doctor.WANT), set(expected))
        for target, wanted in expected.items():
            with self.subTest(target=target):
                actual, reason = doctor.WANT[target]
                self.assertIs(type(actual), type(wanted))
                self.assertEqual(actual, wanted)
                self.assertTrue(reason)

    def test_default_reads_every_target_and_reports_ready_for_verified_json(self):
        fake = FakeMcp()
        result, output, readiness, factory = self.run_main(fake)
        self.assertEqual(result, 0)
        self.assertIn("MCP READY", output)
        readiness.assert_called_once_with()
        factory.assert_called_once_with(timeout=30)
        self.assert_read_passes(fake, 1)
        self.assertEqual(fake.set_calls(), [])

    def test_default_accepts_an_object_response_without_decoding_it_again(self):
        fake = FakeMcp(as_json=False)
        result, output, _ready, _factory = self.run_main(fake)
        self.assertEqual(result, 0)
        self.assertIn("MCP READY", output)
        self.assert_read_passes(fake, 1)
        self.assertEqual(fake.set_calls(), [])

    def test_default_is_read_only_when_existing_values_are_wrong(self):
        fake = FakeMcp(self.changed_both_sections())
        result, output, _ready, _factory = self.run_main(fake)
        self.assert_failed(result, output)
        self.assert_read_passes(fake, 1)
        self.assertEqual(fake.set_calls(), [])

    def test_equality_requires_the_exact_wanted_type(self):
        wrong_values = [(self.first, self.bool_prop, 0),
                        (self.first, self.bool_prop, 0.0),
                        (self.second, self.int_prop, 30.0),
                        (self.second, "autoSaveWarningInSeconds", False),
                        (self.second, "autoSaveWarningInSeconds", 0.0)]
        for section, prop, value in wrong_values:
            with self.subTest(section=section, prop=prop, value=value):
                values = copy.deepcopy(self.sections)
                values[section][prop] = value
                fake = FakeMcp(values)
                result, output, _ready, _factory = self.run_main(fake)
                self.assert_failed(result, output)
                self.assertEqual(fake.set_calls(), [])

    def test_missing_property_is_wrong_in_read_only_mode(self):
        values = copy.deepcopy(self.sections)
        del values[self.first][self.bool_prop]
        fake = FakeMcp(values)
        result, output, _ready, _factory = self.run_main(fake)
        self.assert_failed(result, output)
        self.assert_read_passes(fake, 1)
        self.assertEqual(fake.set_calls(), [])

    def test_fix_writes_only_known_wrong_properties_once_per_section_then_reads_all(self):
        fake = FakeMcp(self.changed_both_sections())
        result, output, _ready, _factory = self.run_main(fake, ["--fix"])
        self.assertEqual(result, 0)
        self.assertIn("MCP READY", output)
        self.assert_read_passes(fake, 2)
        self.assertEqual([tool for _ts, tool, _args in fake.calls],
                         [GET, GET, SET, SET, GET, GET])
        self.assertEqual([(args["sectionName"], json.loads(args["propertiesJson"]))
                          for args in fake.set_calls()],
                         [(self.first, {self.bool_prop: False}),
                          (self.second, {self.int_prop: 30})])

    def test_fix_groups_multiple_wrong_values_in_a_single_section_write(self):
        values = copy.deepcopy(self.sections)
        values[self.first][self.bool_prop] = True
        values[self.first]["bAllowSlateThrottling"] = True
        fake = FakeMcp(values)
        result, output, _ready, _factory = self.run_main(fake, ["--fix"])
        self.assertEqual(result, 0)
        self.assertIn("MCP READY", output)
        self.assert_read_passes(fake, 2)
        self.assertEqual(len(fake.set_calls()), 1)
        self.assertEqual(json.loads(fake.set_calls()[0]["propertiesJson"]),
                         {self.bool_prop: False, "bAllowSlateThrottling": False})

    def test_fix_replaces_equal_but_wrong_types(self):
        values = copy.deepcopy(self.sections)
        values[self.first][self.bool_prop] = 0
        values[self.second][self.int_prop] = 30.0
        fake = FakeMcp(values)
        result, output, _ready, _factory = self.run_main(fake, ["--fix"])
        self.assertEqual(result, 0)
        self.assertIn("MCP READY", output)
        self.assert_read_passes(fake, 2)
        self.assertEqual(len(fake.set_calls()), 2)
        self.assertIs(type(fake.values[self.first][self.bool_prop]), bool)
        self.assertIs(type(fake.values[self.second][self.int_prop]), int)

    def test_initial_missing_property_prevents_every_write(self):
        values = self.changed_both_sections()
        del values[self.first][self.bool_prop]
        fake = FakeMcp(values)
        result, output, _ready, _factory = self.run_main(fake, ["--fix"])
        self.assert_failed(result, output)
        self.assert_read_passes(fake, 1)
        self.assertEqual(fake.set_calls(), [])
        self.assertNotIn(self.bool_prop, fake.values[self.first])

    def test_missing_only_fix_fails_without_sending_a_setter(self):
        values = copy.deepcopy(self.sections)
        del values[self.second][self.int_prop]
        fake = FakeMcp(values)
        result, output, _ready, _factory = self.run_main(fake, ["--fix"])
        self.assert_failed(result, output)
        self.assert_read_passes(fake, 1)
        self.assertEqual(fake.set_calls(), [])

    def test_fix_uses_complete_initial_read_when_no_writes_are_needed(self):
        fake = FakeMcp()
        result, output, _ready, _factory = self.run_main(fake, ["--fix"])
        self.assertEqual(result, 0)
        self.assertIn("MCP READY", output)
        self.assert_read_passes(fake, 1)
        self.assertEqual(fake.set_calls(), [])

    def test_fix_noop_response_true_or_false_cannot_claim_success(self):
        for response in (True, False):
            with self.subTest(response=response):
                fake = FakeMcp(self.changed_both_sections(),
                               setter=lambda _fake, _section, _props: response)
                result, output, _ready, _factory = self.run_main(fake, ["--fix"])
                self.assert_failed(result, output)
                self.assert_read_passes(fake, 2)
                self.assertEqual(len(fake.set_calls()), 2 if response is True else 1)

    def test_setter_requires_boolean_true_even_when_in_memory_readback_is_correct(self):
        # UE can apply the value in memory and then fail to save/notify the section.
        # Integers equal to True and other truthy responses are not its boolean contract.
        for response in (False, None, 1, 0, 1.0, 0.0, "true", "saved", {}, {"success": True}, []):
            with self.subTest(response=response):
                values = copy.deepcopy(self.sections)
                values[self.first][self.bool_prop] = True
                fake = FakeMcp(values, set_response=response)
                result, output, _ready, _factory = self.run_main(fake, ["--fix"])
                self.assert_failed(result, output)
                self.assert_read_passes(fake, 2)
                self.assertEqual(fake.values, self.sections)
                self.assertEqual(len(fake.set_calls()), 1)
                self.assertEqual([tool for _ts, tool, _args in fake.calls],
                                 [GET, GET, SET, GET, GET])

    def test_save_failure_after_in_memory_change_stops_later_writes_without_retry(self):
        def apply_then_save_fails(fake, section, props):
            fake.values[section].update(props)
            return False

        fake = FakeMcp(self.changed_both_sections(), setter=apply_then_save_fails)
        result, output, _ready, _factory = self.run_main(fake, ["--fix"])
        self.assert_failed(result, output)
        self.assert_read_passes(fake, 2)
        self.assertEqual(fake.values[self.first], self.sections[self.first])
        self.assertEqual(fake.values[self.second][self.int_prop], 10)
        self.assertEqual(len(fake.set_calls()), 1)
        self.assertEqual(fake.set_calls()[0]["sectionName"], self.first)
        self.assertEqual([tool for _ts, tool, _args in fake.calls],
                         [GET, GET, SET, GET, GET])

    def test_partial_fix_still_fails_final_verification(self):
        def partial(fake, section, props):
            if section == self.first:
                fake.values[section].update(props)
            return True

        fake = FakeMcp(self.changed_both_sections(), setter=partial)
        result, output, _ready, _factory = self.run_main(fake, ["--fix"])
        self.assert_failed(result, output)
        self.assert_read_passes(fake, 2)
        self.assertEqual(len(fake.set_calls()), 2)

    def test_setter_exception_stops_remaining_writes_and_still_reads_all_sections(self):
        def failing(_fake, _section, _props):
            raise TimeoutError("synthetic write timeout")

        fake = FakeMcp(self.changed_both_sections(), setter=failing)
        result, output, _ready, _factory = self.run_main(fake, ["--fix"])
        self.assert_failed(result, output)
        self.assert_read_passes(fake, 2)
        self.assertEqual(len(fake.set_calls()), 1)
        self.assertEqual([tool for _ts, tool, _args in fake.calls], [GET, GET, SET, GET, GET])

    def test_applied_write_followed_by_exception_remains_unknown_without_retry(self):
        values = copy.deepcopy(self.sections)
        values[self.first][self.bool_prop] = True

        def applied_then_failed(fake, section, props):
            fake.values[section].update(props)
            raise TimeoutError("synthetic response was lost")

        fake = FakeMcp(values, setter=applied_then_failed)
        result, output, _ready, _factory = self.run_main(fake, ["--fix"])
        self.assert_failed(result, output)
        self.assert_read_passes(fake, 2)
        self.assertEqual(fake.values, self.sections)
        self.assertEqual(len(fake.set_calls()), 1)

    def test_second_write_exception_keeps_prior_fix_but_cannot_report_ready(self):
        def second_fails(fake, section, props):
            fake.values[section].update(props)
            if section == self.second:
                raise OSError("synthetic disconnect after applying")
            return True

        fake = FakeMcp(self.changed_both_sections(), setter=second_fails)
        result, output, _ready, _factory = self.run_main(fake, ["--fix"])
        self.assert_failed(result, output)
        self.assert_read_passes(fake, 2)
        self.assertEqual(fake.values, self.sections)
        self.assertEqual(len(fake.set_calls()), 2)

    def test_initial_malformed_or_nonobject_response_prevents_every_write(self):
        invalid_results = ["{broken", "[]", "null", "true", "30", "\"string\"",
                           [], None, True, 30]
        for invalid in invalid_results:
            for section in self.section_names:
                with self.subTest(invalid=invalid, section=section):
                    fake = FakeMcp(self.changed_both_sections(), reads={section: [invalid]})
                    result, output, _ready, _factory = self.run_main(fake, ["--fix"])
                    self.assert_failed(result, output)
                    self.assert_read_passes(fake, 1)
                    self.assertEqual(fake.set_calls(), [])

    def test_initial_getter_exception_prevents_writes_but_reads_other_section(self):
        for section in self.section_names:
            with self.subTest(section=section):
                fake = FakeMcp(self.changed_both_sections(), reads={
                    section: [TimeoutError("synthetic read timeout")]})
                result, output, _ready, _factory = self.run_main(fake, ["--fix"])
                self.assert_failed(result, output)
                self.assert_read_passes(fake, 1)
                self.assertEqual(fake.set_calls(), [])

    def test_final_read_error_fails_closed_after_writes_and_checks_other_section(self):
        for invalid in ("{broken", [], None, TimeoutError("synthetic final read timeout")):
            for section in self.section_names:
                with self.subTest(invalid=invalid, section=section):
                    values = self.changed_both_sections()
                    fake = FakeMcp(values, reads={section: [json.dumps(values[section]), invalid]})
                    result, output, _ready, _factory = self.run_main(fake, ["--fix"])
                    self.assert_failed(result, output)
                    self.assert_read_passes(fake, 2)
                    self.assertEqual(len(fake.set_calls()), 2)

    def test_final_read_detects_an_initially_correct_setting_becoming_wrong(self):
        values = copy.deepcopy(self.sections)
        values[self.second][self.int_prop] = 10
        wrong_final = copy.deepcopy(values[self.first])
        wrong_final[self.bool_prop] = True
        fake = FakeMcp(values, reads={self.first: [json.dumps(values[self.first]),
                                                json.dumps(wrong_final)]})
        result, output, _ready, _factory = self.run_main(fake, ["--fix"])
        self.assert_failed(result, output)
        self.assert_read_passes(fake, 2)
        self.assertEqual(len(fake.set_calls()), 1)

    def test_final_read_rejects_missing_and_wrong_type_values(self):
        for final_value in (None, 30.0):
            with self.subTest(final_value=final_value):
                values = self.changed_both_sections()
                final_section = copy.deepcopy(self.sections[self.second])
                if final_value is None:
                    del final_section[self.int_prop]
                else:
                    final_section[self.int_prop] = final_value
                fake = FakeMcp(values, reads={self.second: [json.dumps(values[self.second]),
                                                         json.dumps(final_section)]})
                result, output, _ready, _factory = self.run_main(fake, ["--fix"])
                self.assert_failed(result, output)
                self.assert_read_passes(fake, 2)
                self.assertEqual(len(fake.set_calls()), 2)

    def test_readiness_false_does_not_initialize_a_client(self):
        fake = FakeMcp()
        result, output, readiness, factory = self.run_main(fake, ["--fix"], ready=False)
        self.assert_failed(result, output)
        readiness.assert_called_once_with()
        factory.assert_not_called()
        self.assertEqual(fake.calls, [])

    def test_client_initialization_error_is_a_failure_without_calls(self):
        fake = FakeMcp()
        result, output, readiness, factory = self.run_main(
            fake, ["--fix"], factory_error=TimeoutError("synthetic initialize timeout"))
        self.assert_failed(result, output)
        readiness.assert_called_once_with()
        factory.assert_called_once_with(timeout=30)
        self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()
