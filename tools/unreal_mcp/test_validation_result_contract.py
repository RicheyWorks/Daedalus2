# SPDX-License-Identifier: MIT
"""Synthetic native-member snapshots; no Unreal imports or native execution."""
import unittest

from tools.unreal_mcp.automation_result_contract import ContractViolation
from tools.unreal_mcp.validation_result_contract import evaluate_native_validation


ASSET = "/Game/Acceptance/SM_One.SM_One"


def snapshot():
    return {"NumRequested": 1, "NumExternalObjects": 0, "NumChecked": 1,
            "NumValid": 1, "NumInvalid": 0, "NumSkipped": 0, "NumWarnings": 0,
            "NumUnableToValidate": 0, "bAssetLimitReached": False,
            "AssetsDetails": {ASSET: {"PackageName": "/Game/Acceptance/SM_One",
                                      "AssetName": "SM_One", "Result": "Valid",
                                      "ValidationErrors": [], "ValidationWarnings": [],
                                      "ValidationMessages": [], "ExternalObjects": []}},
            "ValidatorMessages": []}


def settings():
    return {"bLoadAssetsForValidation": True, "bLoadExternalObjectsForValidation": False,
            "bCollectPerAssetDetails": True, "bCaptureAssetLoadLogs": True,
            "bCaptureLogsDuringValidation": True, "MaxAssetsToValidate": 2}


class ValidationResultContractTests(unittest.TestCase):
    def evaluate(self, value=None, native_return=0, options=None):
        return evaluate_native_validation([ASSET], native_return,
                                          snapshot() if value is None else value,
                                          settings() if options is None else options)

    def test_complete_exact_native_snapshot_does_not_claim_callable_or_runtime(self):
        result = self.evaluate()
        self.assertTrue(result["accepted"])
        self.assertFalse(result["native_runtime_qualified"])
        self.assertFalse(result["official_mcp_callable_verified"])

    def test_return_is_invalid_plus_warnings_including_double_count(self):
        value = snapshot()
        value.update(NumValid=0, NumInvalid=1, NumWarnings=1)
        self.assertFalse(self.evaluate(value, native_return=2)["accepted"])
        for wrong in (True, 1):
            with self.subTest(value=wrong), self.assertRaises(ContractViolation):
                self.evaluate(value, native_return=wrong)

    def test_valid_asset_can_still_have_warning_and_is_not_accepted(self):
        value = snapshot()
        value["NumWarnings"] = 1
        result = self.evaluate(value, native_return=1)
        self.assertIn("NumWarnings", result["problems"])
        self.assertFalse(result["accepted"])

    def test_skipped_unable_and_missing_requested_assets_never_pass(self):
        for changes in ({"NumChecked": 0, "NumValid": 0, "NumSkipped": 1},
                        {"NumValid": 0, "NumUnableToValidate": 1},
                        {"NumRequested": 2}):
            value = snapshot()
            value.update(changes)
            with self.subTest(changes=changes):
                self.assertFalse(self.evaluate(value)["accepted"])

    def test_limit_flag_or_exact_cap_is_not_accepted(self):
        value = snapshot()
        value["bAssetLimitReached"] = True
        self.assertFalse(self.evaluate(value)["accepted"])
        options = settings()
        options["MaxAssetsToValidate"] = 1
        self.assertFalse(self.evaluate(options=options)["accepted"])

    def test_absent_or_wrong_identity_and_external_objects_are_not_accepted(self):
        for changes in ({"AssetsDetails": {}},
                        {"AssetsDetails": {"/Game/Other.Other": {}}},
                        {"NumExternalObjects": 1}, {"ValidatorMessages": ["review native message"]}):
            value = snapshot()
            value.update(changes)
            with self.subTest(changes=changes):
                self.assertFalse(self.evaluate(value)["accepted"])

    def test_nonreflected_messages_must_be_explicitly_captured(self):
        value = snapshot()
        del value["ValidatorMessages"]
        with self.assertRaises(ContractViolation):
            self.evaluate(value)

    def test_detail_identity_result_and_diagnostics_must_agree(self):
        for field, bad in (("PackageName", "/Game/Other"), ("AssetName", "Other"),
                           ("Result", "Invalid"), ("ValidationErrors", ["failure"]),
                           ("ValidationWarnings", ["warning"]), ("ValidationMessages", ["message"]),
                           ("ExternalObjects", ["external"])):
            value = snapshot()
            value["AssetsDetails"][ASSET][field] = bad
            with self.subTest(field=field):
                self.assertFalse(self.evaluate(value)["accepted"])
        for bad in ({}, None):
            value = snapshot()
            value["AssetsDetails"][ASSET] = bad
            with self.subTest(detail=bad):
                self.assertFalse(self.evaluate(value)["accepted"])

    def test_subobject_and_noncanonical_paths_are_not_standalone_assets(self):
        for path in (ASSET + ":Subobject", "/Game/Acceptance/../SM_One.SM_One", ASSET + ".Extra"):
            with self.subTest(path=path), self.assertRaises(ContractViolation):
                evaluate_native_validation([path], 0, snapshot(), settings())

    def test_loading_details_and_capture_settings_are_material(self):
        for key in ("bLoadAssetsForValidation", "bCollectPerAssetDetails",
                    "bCaptureAssetLoadLogs", "bCaptureLogsDuringValidation"):
            options = settings()
            options[key] = False
            with self.subTest(key=key):
                self.assertFalse(self.evaluate(options=options)["accepted"])

    def test_accumulated_or_boolean_counts_are_rejected(self):
        for changes in ({"NumChecked": 2, "NumValid": 2}, {"NumValid": True}):
            value = snapshot()
            value.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ContractViolation):
                self.evaluate(value)


if __name__ == "__main__":
    unittest.main()
