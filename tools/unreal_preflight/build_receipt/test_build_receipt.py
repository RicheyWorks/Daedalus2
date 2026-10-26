# SPDX-License-Identifier: MIT
"""Engine-free tests for build_receipt.py: temp git repo, temp live plugin, fake DLL and UBT logs."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_receipt as br  # noqa: E402

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false",
       "-c", "init.defaultBranch=main", "-c", "core.autocrlf=false"]


def run(cwd, *args):
    subprocess.run(GIT + list(args), cwd=cwd, check=True, capture_output=True)


def put(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


class ReceiptTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = os.path.join(self.tmp, "repo")
        rp = os.path.join(self.repo, "engines", "unreal", "DaedalusLink")
        put(os.path.join(rp, "Source", "A.cpp"), b"int a;\n")
        put(os.path.join(rp, "Source", "Pub", "A.h"), b"#pragma once\n")
        put(os.path.join(rp, "DaedalusLink.uplugin"), b"{}\n")
        run(self.tmp, "init", "-q", self.repo)
        run(self.repo, "add", "-A")
        run(self.repo, "commit", "-q", "-m", "base")
        self.base = subprocess.run(["git", "-C", self.repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        run(self.repo, "checkout", "-q", "-b", "feature")
        put(os.path.join(rp, "Source", "B.cpp"), b"int b;\n")
        run(self.repo, "add", "-A")
        run(self.repo, "commit", "-q", "-m", "add b")
        run(self.repo, "checkout", "-q", "main")
        run(self.repo, "merge", "-q", "--no-ff", "feature", "-m", "Merge pull request #42 from me/feature")
        self.plugin = os.path.join(self.tmp, "live", "DaedalusLink")
        shutil.copytree(rp, self.plugin)
        put(os.path.join(self.plugin, "Source", "Untracked.h"), b"// local only\n")
        self.dll = os.path.join(self.plugin, "Binaries", "UnrealEditor-DaedalusLink.dll")
        put(self.dll, b"MZ new")
        self.old = os.path.join(self.tmp, "backup.dll")
        put(self.old, b"MZ old")
        self.log = os.path.join(self.tmp, "ubt2.log")
        put(self.log, "Building...\r\n[4/5] Link [x64] UnrealEditor-DaedalusLink.dll\r\nResult: Succeeded\r\n".encode("utf-16"))
        self.out = os.path.join(self.tmp, "build-receipt.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def call(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = br.main(list(argv))
        return code, buf.getvalue()

    def write(self, log=None):
        return self.call("write", "--repo", self.repo, "--plugin", self.plugin, "--dll", self.dll, "--ubt-log",
                         log or self.log, "--backup-dll", self.old, "--base", self.base, "--out", self.out)

    def test_write_records_everything(self):
        code, _ = self.write()
        self.assertEqual(code, 0)
        r = br.load_receipt(self.out)
        paths = [f["path"] for f in r["files"]]
        self.assertEqual(paths, ["DaedalusLink.uplugin", "Source/A.cpp", "Source/B.cpp", "Source/Pub/A.h", "Source/Untracked.h"])
        self.assertEqual(r["summary"]["not_in_head"], ["Source/Untracked.h"])
        self.assertEqual(r["summary"]["differs_from_head"], [])
        self.assertEqual([p["pr"] for p in r["repo"]["merged_prs"]], [42])
        self.assertEqual(r["repo"]["branch"], "main")
        self.assertEqual(r["ubt_log"]["success"], {"line": 3, "text": "Result: Succeeded"})
        self.assertEqual(r["dll"]["sha256"], br.sha256_file(self.dll))
        self.assertEqual(r["old_dll"]["sha256"], br.sha256_file(self.old))
        blob = subprocess.run(["git", "-C", self.repo, "hash-object", os.path.join(self.plugin, "Source", "A.cpp")],
                              capture_output=True, text=True).stdout.strip()
        self.assertEqual(next(f for f in r["files"] if f["path"] == "Source/A.cpp")["git_blob"], blob)

    def test_failed_build_is_refused(self):
        bad = os.path.join(self.tmp, "ubt.log")
        put(bad, b"error C4458: declaration of 'Owner' hides class member\nResult: Failed (OtherCompilationError)\n")
        code, out = self.write(bad)
        self.assertEqual(code, 2)
        self.assertIn("REFUSED", out)
        self.assertFalse(os.path.exists(self.out))

    def test_verify_clean_then_drift(self):
        self.write()
        self.assertEqual(self.call("verify", "--receipt", self.out)[0], 0)
        put(os.path.join(self.plugin, "Source", "A.cpp"), b"int a2;\n")
        put(os.path.join(self.plugin, "Source", "New.cpp"), b"x\n")
        os.remove(os.path.join(self.plugin, "Source", "B.cpp"))
        put(self.dll, b"MZ rebuilt")
        code, out = self.call("verify", "--receipt", self.out)
        d = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual((d["changed"], d["added"], d["missing"]), (["Source/A.cpp"], ["Source/New.cpp"], ["Source/B.cpp"]))
        self.assertIsNotNone(d["dll"])

    def test_tampered_receipt_is_rejected(self):
        self.write()
        with open(self.out, "ab") as fh:
            fh.write(b" ")
        self.assertEqual(self.call("verify", "--receipt", self.out)[0], 3)

    def test_pins_diff(self):
        self.write()
        pins = os.path.join(self.tmp, "protected-files.json")
        good = br.sha256_file(os.path.join(self.plugin, "Source", "A.cpp"))
        rows = [{"path": os.path.join(self.plugin, "Source", "A.cpp"), "sha256": good},
                {"path": os.path.join(self.plugin, "Source", "B.cpp"), "sha256": "0" * 64},
                {"path": self.dll, "sha256": "1" * 64},
                {"path": os.path.join(self.plugin, "Source", "Gone.h"), "sha256": "2" * 64},
                {"path": os.path.join(self.tmp, "elsewhere.txt"), "sha256": "3" * 64}]
        with open(pins, "w", encoding="utf-8") as fh:
            json.dump(rows, fh)
        code, out = self.call("pins-diff", "--receipt", self.out, "--pins", pins)
        d = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(d["checked"], 3)
        self.assertEqual(sorted(os.path.basename(m["path"]) for m in d["mismatched"]), ["B.cpp", "UnrealEditor-DaedalusLink.dll"])
        self.assertEqual([os.path.basename(p) for p in d["not_in_receipt"]], ["Gone.h"])
        self.assertEqual(d["outside_plugin"], 1)

    def test_parity_pass_dict_rows(self):
        p = os.path.join(self.tmp, "parity-pass.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump({"source_manifest": {"files": [{"path": "a", "sha256": "1"}]}, "binary": {"path": "b", "sha256": "2"},
                       "canonical_header": {"path": "c", "sha256": "3"}, "utc": "x"}, fh)
        self.assertEqual([r["path"] for r in br.load_rows(p)], ["a", "b", "c"])

    def test_success_line_in_utf8_and_last_wins(self):
        log = os.path.join(self.tmp, "u8.log")
        put(log, b"Result: Succeeded\nmore\n  Result: Succeeded\n")
        self.assertEqual(br.success_line(log), {"line": 3, "text": "Result: Succeeded"})


if __name__ == "__main__":
    unittest.main()
