# SPDX-License-Identifier: MIT
"""Tests for native_validation_snapshot_consumer.py (stdlib unittest, no editor, no network).

    python -m unittest tools/unreal_mcp/test_native_validation_snapshot_consumer.py
"""
import copy
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import native_validation_snapshot_consumer as nv  # noqa: E402

P = "/Game/Isolated/SM_Crate.SM_Crate"
# Byte-for-byte what Serialize(MakePassing()) emits in test_native_validation_result_snapshot.cpp
# at PR #187 head 77e2e0e8 (key order, ", " / ": " separators, default unknowns).
CPP_MAKE_PASSING = (
    '{"snapshot_kind": "explicit_native_members_not_mcp_schema", '
    '"requested_assets": ["/Game/Isolated/SM_Crate.SM_Crate"], "native_return": 0, '
    '"results": {"NumRequested": 1, "NumExternalObjects": 0, "NumChecked": 1, "NumValid": 1, '
    '"NumInvalid": 0, "NumSkipped": 0, "NumWarnings": 0, "NumUnableToValidate": 0, '
    '"bAssetLimitReached": false, "AssetsDetails": {"/Game/Isolated/SM_Crate.SM_Crate": '
    '{"PackageName": "/Game/Isolated/SM_Crate", "AssetName": "SM_Crate", "Result": "Valid", '
    '"ValidationErrors": [], "ValidationWarnings": [], "ValidationMessages": [], "ExternalObjects": []}}, '
    '"ValidatorMessages": []}, '
    '"settings": {"bSkipExcludedDirectories": true, "bShowIfNoFailures": true, "bCollectPerAssetDetails": true, '
    '"ValidationUsecase": "None", "bLoadAssetsForValidation": true, "bUnloadAssetsLoadedForValidation": false, '
    '"bLoadExternalObjectsForValidation": true, "bCaptureAssetLoadLogs": true, "bCaptureLogsDuringValidation": true, '
    '"bCaptureWarningsDuringValidationAsErrors": false, "MaxAssetsToValidate": 2, '
    '"bValidateReferencersOfDeletedAssets": true, "bSilent": false}, '
    '"provenance": {"fresh_out_results": "unknown", "native_invocation": "unknown", "captured_at_utc": "unknown"}, '
    '"native_runtime_qualified": false, '
    '"unknowns": ["fresh_out_results_unproven", "native_invocation_unproven", "native_runtime_unqualified", '
    '"official_mcp_callable_unverified", "tokenized_message_tokens_projected_to_text_only", '
    '"validator_statistics_not_captured", "settings_message_log_fields_not_captured"]}'
)


def base():
    return json.loads(CPP_MAKE_PASSING)


def run(doc, caps=nv.OutputCaps()):
    return nv.consume(json.dumps(doc), caps)


class ValidSnapshots(unittest.TestCase):
    def test_cpp_fixture_accepted(self):
        res = nv.consume(CPP_MAKE_PASSING)
        self.assertTrue(res.accepted, res.to_dict())
        s = res.snapshot
        self.assertEqual(s.requested_assets, (P,))
        self.assertEqual(s.results.details[0].result, "Valid")
        self.assertEqual(s.settings.max_assets_to_validate, 2)
        self.assertFalse(s.native_runtime_qualified)
        self.assertIn("native_runtime_unqualified", s.unknowns)
        self.assertEqual(res.pinned_head, nv.PINNED_PR187_HEAD)

    def test_bytes_and_escapes(self):
        d = base()
        d["results"]["ValidatorMessages"] = [{"Severity": "Info", "Text": "q\"b\\n\nt\tc\u0001A\u0000B"}]
        res = nv.consume(json.dumps(d).encode("utf-8"))
        self.assertTrue(res.accepted, res.to_dict())
        self.assertEqual(res.snapshot.results.validator_messages[0].text, "q\"b\\n\nt\tc\x01A\x00B")

    def test_to_dict_is_json(self):
        json.dumps(nv.consume(CPP_MAKE_PASSING).to_dict())

    def test_problems_not_clamped(self):
        d = base()
        d["results"]["NumChecked"] = -1
        d["native_return"] = 4294967296
        d["settings"]["MaxAssetsToValidate"] = 0
        p = run(d).problems
        for want in ("negative_count", "native_return_out_of_int32", "native_return_nonzero",
                     "asset_limit_reached_or_insufficient_headroom"):
            self.assertIn(want, p)

    def test_failing_detail_and_limit(self):
        d = base()
        d["results"]["AssetsDetails"][P]["Result"] = "Invalid"
        d["results"]["bAssetLimitReached"] = True
        p = run(d).problems
        self.assertIn("detail_not_valid:" + P, p)
        self.assertIn("asset_limit_reached_or_insufficient_headroom", p)

    def test_exact_equality_limit_rejected(self):
        d = base()
        d["settings"]["MaxAssetsToValidate"] = 1
        self.assertIn("asset_limit_reached_or_insufficient_headroom", run(d).problems)


class CapViolations(unittest.TestCase):
    def test_requested_cap(self):
        d = base()
        d["requested_assets"] = ["/Game/A%d.A" % i for i in range(5)]
        res = run(d, nv.OutputCaps(max_requested_assets=4))
        self.assertFalse(res.accepted)
        self.assertTrue(any(v.startswith("requested_assets") for v in res.cap_violations))

    def test_string_cap(self):
        d = base()
        d["results"]["ValidatorMessages"] = [{"Severity": "Info", "Text": "x" * 100}]
        res = run(d, nv.OutputCaps(max_string_chars=50))
        self.assertTrue(any(v.startswith("string length") for v in res.cap_violations))

    def test_messages_per_list_and_total(self):
        d = base()
        d["results"]["AssetsDetails"][P]["ValidationMessages"] = [{"Severity": "Info", "Text": "m"}] * 3
        d["results"]["ValidatorMessages"] = [{"Severity": "Info", "Text": "m"}] * 3
        res = run(d, nv.OutputCaps(max_messages_per_list=2, max_total_messages=5))
        self.assertEqual(sum(v.startswith(P) or v.startswith("ValidatorMessages") for v in res.cap_violations), 2)
        self.assertTrue(any(v.startswith("total messages") for v in res.cap_violations))

    def test_details_cap(self):
        res = nv.consume(CPP_MAKE_PASSING, nv.OutputCaps(max_details=0))
        self.assertTrue(any(v.startswith("details") for v in res.cap_violations))

    def test_byte_cap_rejects_before_parse(self):
        with self.assertRaises(nv.SnapshotError):
            nv.consume(CPP_MAKE_PASSING, nv.OutputCaps(max_bytes=100))


class MalformedInput(unittest.TestCase):
    def bad(self, doc_or_text):
        text = doc_or_text if isinstance(doc_or_text, (str, bytes)) else json.dumps(doc_or_text)
        with self.assertRaises(nv.SnapshotError):
            nv.consume(text)

    def test_not_json(self):
        self.bad("{not json")
        self.bad(b"\xff\xfe")
        self.bad('{"native_return": NaN}')

    def test_wrong_root_and_kind(self):
        self.bad("[]")
        d = base(); d["snapshot_kind"] = "mcp_schema"; self.bad(d)

    def test_missing_and_wrong_types(self):
        for mutate in (
            lambda d: d.pop("results"),
            lambda d: d["results"].pop("NumValid"),
            lambda d: d.__setitem__("native_return", True),
            lambda d: d.__setitem__("native_return", 0.0),
            lambda d: d["results"].__setitem__("bAssetLimitReached", 0),
            lambda d: d["settings"].__setitem__("bSilent", "false"),
            lambda d: d["results"]["AssetsDetails"][P].__setitem__("Result", "Maybe"),
            lambda d: d["results"]["AssetsDetails"][P].__setitem__("ValidationErrors", "e"),
            lambda d: d["results"].__setitem__("ValidatorMessages", [{"Severity": "Info"}]),
            lambda d: d["requested_assets"].append(7),
            lambda d: d.pop("provenance"),
        ):
            d = copy.deepcopy(base())
            mutate(d)
            self.bad(d)


if __name__ == "__main__":
    unittest.main()
