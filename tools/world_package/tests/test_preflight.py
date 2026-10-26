# SPDX-License-Identifier: MIT

import builtins
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import socket
import struct
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

from tools.world_package import PlanError, build_plan
from tools.world_package.__main__ import main
from tools.world_package import reader_adapter
from tools.world_package.reader_adapter import strict_json
from tools.world_package.replay_plan import validate_receipt
from tools.world_package.tests.fixtures import MANIFEST, glb, package, receipt


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.zip = package(self.root / "fixture.zip")

    def variant(self, **changes):
        manifest = copy.deepcopy(MANIFEST)
        for key, value in changes.items():
            manifest[key] = value
        return package(self.root / "variant.zip", manifest)

    def test_deterministic_plan_binds_bytes_raw_identity_and_local_paths(self):
        before = self.zip.read_bytes()
        result = build_plan(self.zip)
        self.assertEqual(result, build_plan(self.zip))
        self.assertEqual("plan_new", result["action"])
        self.assertEqual("world-zero", result["world"]["id"])
        self.assertEqual(hashlib.sha256(before).hexdigest(), result["source"]["package_sha256"])
        self.assertEqual(len(before), result["source"]["package_bytes"])
        for key in ("level", "materials", "geometry"):
            self.assertTrue(result["destination"][key].startswith(result["destination"]["root"] + "/"))
        self.assertFalse(result["policy"]["replace_existing"])
        self.assertFalse(result["policy"]["delete_existing"])
        self.assertFalse(result["policy"]["use_shared_materials"])
        self.assertFalse(result["native_acceptance"])
        self.assertEqual(before, self.zip.read_bytes())
        self.assertEqual([self.zip.name], [path.name for path in self.root.iterdir()])

    def test_exact_accepted_replay_no_op_preserves_receipt(self):
        prior = receipt(build_plan(self.zip))
        original = copy.deepcopy(prior)
        result = build_plan(self.zip, prior)
        self.assertEqual("no_op", result["action"])
        self.assertEqual(prior["destination_root"], result["destination"]["root"])
        self.assertEqual(original, prior)

    def test_same_revision_changed_bytes_refuses(self):
        prior = receipt(build_plan(self.zip))
        changed = self.variant(generator="another-byte-stream")
        before = {path: path.read_bytes() for path in (self.zip, changed)}
        with self.assertRaisesRegex(PlanError, "conflicting package bytes"):
            build_plan(changed, prior)
        for path, data in before.items():
            self.assertEqual(data, path.read_bytes())

    def test_new_revision_gets_new_level_and_materials(self):
        first = build_plan(self.zip)
        world = dict(MANIFEST["world"], revision=13)
        result = build_plan(self.variant(world=world), receipt(first))
        self.assertEqual("plan_new", result["action"])
        self.assertEqual(first["destination"]["root"], result["previous_destination_root"])
        for key in first["destination"]:
            self.assertNotEqual(first["destination"][key], result["destination"][key])

    def test_old_revision_and_different_world_receipts_refuse(self):
        prior = receipt(build_plan(self.zip))
        for world in (dict(MANIFEST["world"], revision=11), dict(MANIFEST["world"], id="other")):
            with self.subTest(world=world), self.assertRaises(PlanError):
                build_plan(self.variant(world=world), prior)

    def test_sanitized_and_case_colliding_worlds_are_disjoint(self):
        roots = set()
        for world_id in ("a-b", "a_b", "A_B", "é", "e\u0301", "../../world", "世界"):
            result = build_plan(self.variant(world=dict(MANIFEST["world"], id=world_id)))
            self.assertEqual(world_id, result["world"]["id"])
            roots.add(result["destination"]["root"].casefold())
        self.assertEqual(7, len(roots))

    def test_asset_raw_identity_preserved_in_owned_subtree(self):
        assets = [{"name": "ark-red", "file": "assets/ark.glb", "use": "mount"},
                  {"name": "ark_red", "file": "assets/other.glb", "use": "display"}]
        source = package(self.root / "assets.zip", dict(MANIFEST, assets=assets),
                         extra=[(item["file"], glb()) for item in assets])
        result = build_plan(source)
        self.assertEqual(assets, [{key: value for key, value in item.items() if key != "destination"}
                                  for item in result["assets"]])
        self.assertNotEqual(result["assets"][0]["destination"], result["assets"][1]["destination"])
        for item in result["assets"]:
            self.assertTrue(item["destination"].startswith(result["destination"]["root"] + "/Assets/"))
            self.assertLess(len(item["destination"]), 256)

    def test_malformed_manifest_fields_refuse(self):
        variants = [{"format": "other"}, {"version": 2}, {"version": True}, {"world": []},
                    {"world": dict(MANIFEST["world"], id="")},
                    {"world": dict(MANIFEST["world"], id="bad\nworld")},
                    {"world": dict(MANIFEST["world"], revision=True)},
                    {"world": dict(MANIFEST["world"], revision=-1)},
                    {"world": dict(MANIFEST["world"], revision=2 ** 63)},
                    {"geometry": dict(MANIFEST["geometry"], chunks=2)},
                    {"geometry": dict(MANIFEST["geometry"], chunks=True)},
                    {"geometry": dict(MANIFEST["geometry"], file="elsewhere.glb")},
                    {"geometry": dict(MANIFEST["geometry"], triangles=-1)},
                    {"assets": {}}, {"assets": [1]},
                    {"assets": [{"name": "ark", "file": "missing", "use": "mount"}]}]
        for changes in variants:
            with self.subTest(changes=changes), self.assertRaises(PlanError):
                build_plan(self.variant(**changes))

    def test_incompatible_and_forged_receipts_refuse(self):
        prior = receipt(build_plan(self.zip))
        changes = [{"format": "other"}, {"version": True}, {"version": 2}, {"status": "planned"},
                   {"revision": True}, {"revision": -1}, {"world_id": ""},
                   {"package_sha256": "a" * 63}, {"package_sha256": "A" * 64},
                   {"destination_root": "/Game/Daedalus/world_zero"}, {"acceptance_reference": ""},
                   {"unknown": "field"}]
        for changed in changes:
            with self.subTest(changed=changed), self.assertRaises(PlanError):
                build_plan(self.zip, dict(prior, **changed))
        for key in prior:
            value = dict(prior)
            del value[key]
            with self.subTest(missing=key), self.assertRaises(PlanError):
                validate_receipt(value)

    def test_existing_reader_still_checks_glb(self):
        for data in (b"bad", glb({"asset": {"version": "1.0"}, "nodes": [{}]}),
                     glb({"asset": {"version": "2.0"}, "nodes": []}),
                     glb({"asset": {"version": "2.0"}, "nodes": {"a": 1}})):
            with self.subTest(data=data), self.assertRaises(PlanError):
                build_plan(package(self.root / "bad-glb.zip", glb_data=data))
        data = bytearray(glb())
        struct.pack_into("<I", data, 12, len(data) + 4)
        with self.assertRaisesRegex(PlanError, "JSON chunk length"):
            build_plan(package(self.root / "oversize-json.zip", glb_data=data))

    def test_empty_world_remains_valid(self):
        manifest = dict(MANIFEST, geometry={"file": "world.glb", "chunks": 0, "triangles": 0})
        source = package(self.root / "empty.zip", manifest, glb({"asset": {"version": "2.0"}, "nodes": []}))
        self.assertEqual(0, build_plan(source)["geometry"]["chunks"])

    def test_actual_archive_json_and_asset_aliases_refuse(self):
        duplicate = self.root / "duplicate-json.zip"
        with zipfile.ZipFile(duplicate, "w") as archive:
            archive.writestr("manifest.json", '{"format":"x","format":"daedalus-world-package"}')
            archive.writestr("world.glb", glb())
        with self.assertRaisesRegex(PlanError, "duplicate JSON key"):
            build_plan(duplicate)
        for assets in ([{"name": "ark", "file": "assets/a.glb", "use": "mount"},
                        {"name": "ARK", "file": "assets/b.glb", "use": "mount"}],
                       [{"name": "ark", "file": "assets/a.glb", "use": "mount"},
                        {"name": "other", "file": "assets/a.glb", "use": "mount"}]):
            source = package(self.root / "asset-alias.zip", dict(MANIFEST, assets=assets),
                             extra=[("assets/a.glb", glb()), ("assets/b.glb", glb())])
            with self.subTest(assets=assets), self.assertRaisesRegex(PlanError, "asset identity"):
                build_plan(source)

    def test_zip_traversal_aliases_links_and_budgets_refuse(self):
        bad_names = ("../x", "/x", "C:/x", "a/./x", "a//x", "NUL.txt", "a. /x", "assets/a?.glb",
                     "assets/a*.glb", "assets/a<.glb", 'assets/a".glb', "assets/a|.glb",
                     "MANIFEST.JSON", "manifest.json", "directory/")
        for name in bad_names:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                source = package(self.root / "unsafe.zip", extra=[(name, b"x")])
            with self.subTest(name=name), self.assertRaises(PlanError):
                build_plan(source)
        symlink = zipfile.ZipInfo("assets/link.glb")
        symlink.create_system = 3
        symlink.external_attr = 0o120777 << 16
        with self.assertRaisesRegex(PlanError, "member type"):
            build_plan(package(self.root / "link.zip", extra=[(symlink, b"target")]))
        for original, changed in ((b"asset-x", b"asset\x00x"), (b"a/x", b"a\\x")):
            source = package(self.root / "raw-name.zip", extra=[(original.decode(), b"x")])
            source.write_bytes(source.read_bytes().replace(original, changed))
            with self.subTest(changed=changed), self.assertRaises(PlanError):
                build_plan(source)
        with self.assertRaisesRegex(PlanError, "prefix collision"):
            build_plan(package(self.root / "prefix.zip", extra=[("Assets", b"file"), ("assets/ark.glb", glb())]))
        with patch.object(reader_adapter, "MAX_PACKAGE_BYTES", 1), self.assertRaises(PlanError):
            build_plan(self.zip)
        with patch.object(reader_adapter, "MAX_EXPANDED_BYTES", 1), self.assertRaises(PlanError):
            build_plan(self.zip)
        with patch.object(reader_adapter, "MAX_MEMBERS", 1), self.assertRaises(PlanError):
            build_plan(self.zip)

    def test_ambiguous_json_and_nonfinite_numbers_refuse(self):
        for data in ('{"a":1,"a":2}', '{"x":[NaN]}', '{"x":Infinity}', '{"x":1e999}', '{"x":-1e999}'):
            with self.subTest(data=data), self.assertRaises(PlanError):
                strict_json(data)
        for data in ('{"x":' + '9' * 1000 + '}', '{"x":0.' + '1' * 200 + '}'):
            with self.subTest(oversized_number=len(data)), self.assertRaises(PlanError):
                strict_json(data)

    def test_no_unreal_import_no_network_no_existing_top_level_execution(self):
        original_import = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name == "unreal":
                raise AssertionError("must not try importing Unreal")
            return original_import(name, *args, **kwargs)
        source = reader_adapter.IMPORTER.read_text(encoding="utf-8")
        poison = self.root / "poison.py"
        poison.write_text(source.replace("import json", "raise RuntimeError('top-level executed')\nimport json", 1))
        with patch.object(reader_adapter, "IMPORTER", poison), patch("builtins.__import__", side_effect=guarded), patch.object(socket, "socket", side_effect=AssertionError("network attempted")):
            self.assertEqual("plan_new", build_plan(self.zip)["action"])

    def test_changed_reader_signatures_fail_closed(self):
        source = reader_adapter.IMPORTER.read_text(encoding="utf-8")
        for replacement in ("def read_package(zip_path=print('bad')):", "@print('bad')\ndef read_package(zip_path):",
                            "def read_package(zip_path: print('bad')):"):
            changed = self.root / "changed-reader.py"
            changed.write_text(source.replace("def read_package(zip_path):", replacement))
            with patch.object(reader_adapter, "IMPORTER", changed), self.assertRaises(PlanError):
                build_plan(self.zip)

    def test_cli_prints_json_only_and_refuses_without_mutation(self):
        before = {path.name: path.read_bytes() for path in self.root.iterdir()}
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(0, main([str(self.zip)]))
        self.assertEqual("plan_new", json.loads(stdout.getvalue())["action"])
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.root.iterdir()})
        prior = self.root / "prior.json"
        prior.write_text(json.dumps(receipt(build_plan(self.zip))))
        prior_before = prior.read_bytes()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(0, main([str(self.zip), "--prior-receipt", str(prior)]))
        self.assertEqual("no_op", json.loads(stdout.getvalue())["action"])
        self.assertEqual(prior_before, prior.read_bytes())
        for args in (["https://example.invalid/package"], [str(self.root / "missing.zip")],
                     [str(self.zip), "--prior-receipt", str(self.root / "missing.json")]):
            stderr = io.StringIO()
            with self.subTest(args=args), contextlib.redirect_stderr(stderr):
                self.assertEqual(1, main(args))
                self.assertIn("refused", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
