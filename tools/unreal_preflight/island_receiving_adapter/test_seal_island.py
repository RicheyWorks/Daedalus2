# SPDX-License-Identifier: MIT
"""Tests for seal_island: real files in a temp dir, real sha256 re-hash, no editor. Synthetic data only."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import contract as c
import seal_island as s
import test_contract as fx


class SealIsland(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.req = fx.request(mode="native")
        # materialise every pin on disk and bind its real sha256 into the request
        for key, pin in (("source", self.req["item"]["source"]), ("sidecar", self.req["item"]["sidecar"]),
                         ("manifest", self.req["protected_manifest"]), ("recipe", self.req["recipe_pins"][0])):
            p = root / (key + ".bin")
            p.write_bytes(("payload-" + key).encode())
            pin["path"] = str(p)
            pin["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        self.receipt = fx.r27_receipt(self.req)
        self.pre = fx.preflight(self.req)
        self.before, self.after = fx.live("2030-01-02T12:04:00+00:00"), fx.live("2030-01-02T12:06:00+00:00")
        self.root = root

    def tearDown(self):
        self.tmp.cleanup()

    def _files(self):
        names = {"request": self.req, "entry": fx.queue_entry(self.req), "preflight": self.pre, "receipt": self.receipt,
                 "before": self.before, "after": self.after}
        paths = {}
        for k, v in names.items():
            p = self.root / (k + ".json")
            p.write_text(json.dumps(v), encoding="utf-8")
            paths[k] = str(p)
        return paths

    def _argv(self, paths, out="sealed.json", pid=fx.PID):
        return ["--request", paths["request"], "--queue-entry", paths["entry"], "--preflight", paths["preflight"],
                "--receipt", paths["receipt"], "--live-before", paths["before"], "--live-after", paths["after"],
                "--editor-pid", str(pid), "--out", str(self.root / out)]

    def test_seals_admitted_island_from_disk(self):
        rc = s.main(self._argv(self._files()))
        self.assertEqual(rc, 0)
        out = json.loads((self.root / "sealed.json").read_text())
        self.assertTrue(out["candidate"]["native_admission"])
        self.assertEqual(out["sealed"]["custodian"], c.RUNTIME_CUSTODIAN)
        self.assertEqual(out["sealed"]["result_sha256"], c.canonical_sha256(self.receipt))
        self.assertEqual(len(out["sealed"]["rehashed_pins"]), 4)
        # exclusive create: never overwrites a sealed receipt
        with self.assertRaises(FileExistsError):
            s.main(self._argv(self._files()))

    def test_changed_pin_on_disk_is_refused(self):
        Path(self.req["recipe_pins"][0]["path"]).write_bytes(b"tampered")
        rc = s.main(self._argv(self._files(), out="x.json"))
        self.assertEqual(rc, 2)
        self.assertFalse((self.root / "x.json").exists())

    def test_held_island_writes_nothing(self):
        self.receipt = fx.r27_receipt(self.req, admitted=False)
        rc = s.main(self._argv(self._files(), out="h.json"))
        self.assertEqual(rc, 2)
        self.assertFalse((self.root / "h.json").exists())

    def test_wrong_editor_pid_refused(self):
        self.assertEqual(s.main(self._argv(self._files(), out="p.json", pid=999)), 2)

    def test_floor_breach_refused(self):
        self.pre["resources"]["free_disk_bytes"] = 1
        self.assertEqual(s.main(self._argv(self._files(), out="f.json")), 2)

    def test_mock_request_refused(self):
        self.req["execution_mode"] = "mock"
        self.req["receiving_owner"] = "mock-owner-1"
        self.req["expected_world"] = "/Synthetic/World"
        self.assertEqual(s.main(self._argv(self._files(), out="m.json")), 2)

    def test_bad_json_is_input_error(self):
        paths = self._files()
        Path(paths["receipt"]).write_text("{not json", encoding="utf-8")
        self.assertEqual(s.main(self._argv(paths, out="b.json")), 1)

    def test_seal_tool_imports_no_editor_or_broker(self):
        import ast
        tree = ast.parse(Path(s.__file__).read_text(encoding="utf-8"))
        names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                 for a in (n.names if isinstance(n, ast.Import) else [type("m", (), {"name": n.module or ""})])}
        self.assertFalse(names & {"unreal", "subprocess", "socket", "urllib", "asset_pipeline", "shutil"})


if __name__ == "__main__":
    unittest.main()
