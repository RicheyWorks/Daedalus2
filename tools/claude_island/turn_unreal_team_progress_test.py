# SPDX-License-Identifier: MIT
"""Fake-client regressions; no shell child, bridge, editor, Play or team message is sent."""
import contextlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import turn_unreal_team as T


class Fake:
    def __init__(self, fail_command=None, fail_call=None, build_id="build-1013-073247",
                 wait_id=None, build_status="BUILD OK"):
        self.fail_command = fail_command
        self.fail_call = fail_call
        self.build_id = build_id
        self.wait_id = wait_id or build_id
        self.build_status = build_status
        self.commands = []
        self.calls = []

    def run(self, command, **kwargs):
        self.commands.append(command)
        if self.fail_command and any(self.fail_command in str(p) for p in command):
            return subprocess.CompletedProcess(command, 23, "synthetic phase failure", "")
        output = "started %s pid=58092" % self.build_id if "-Start" in command else ""
        if "-Wait" in command:
            output = self.build_status + " " + self.wait_id
        return subprocess.CompletedProcess(command, 0, output, "")

    def call(self, address, kind, **params):
        self.calls.append(kind)
        if kind == self.fail_call:
            raise RuntimeError("synthetic bridge refusal")
        if kind == "daedalus.play_status":
            return {"running": False, "result": {"passed": 1, "total": 1,
                    "checks": [{"check": "synthetic", "pass": True}]}}
        return {"ok": True}


class ProgressTests(unittest.TestCase):
    def setUp(self):
        # The Windows shell sandbox's redirected OS Temp can deny atomic rename.
        # Use this checkout's writable directory; cleanup removes only this fixture.
        self.temp = tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).resolve().parent)
        self.root = pathlib.Path(self.temp.name)
        self.report = self.root / "turn-report.json"
        self.package = types.ModuleType("asset_pipeline")

    def tearDown(self):
        self.temp.cleanup()

    def run_main(self, fake=None, args=(), writer=None):
        fake = fake or Fake()
        self.package.wire = types.SimpleNamespace(UNREAL=None, call=fake.call)
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.dict(sys.modules, {"asset_pipeline": self.package}))
            stack.enter_context(mock.patch.object(T, "REPORT", str(self.report)))
            stack.enter_context(mock.patch.object(T, "ram", return_value={"free_gb": 5.0, "editor_private_gb": 1.0}))
            stack.enter_context(mock.patch.object(T.subprocess, "run", side_effect=fake.run))
            stack.enter_context(mock.patch.object(T.time, "sleep"))
            if writer is not None:
                stack.enter_context(mock.patch.object(T, "atomic_report", side_effect=writer))
            stack.enter_context(contextlib.redirect_stdout(stdout))
            stack.enter_context(contextlib.redirect_stderr(stderr))
            code = T.main(list(args))
        return code, fake, stdout.getvalue(), stderr.getvalue()

    def final(self):
        return json.loads(self.report.read_text(encoding="utf-8"))

    def test_actual_main_failed_preflight_exits_nonzero_without_editor_calls(self):
        code, fake, _, _ = self.run_main(Fake(fail_command="preflight.py"))
        self.assertEqual(code, 1)
        report = self.final()
        self.assertTrue(report["stopped"].startswith("preflight failed"))
        self.assertEqual(report["state"], "failed")
        self.assertFalse(report["steps"][-1]["ok"])
        self.assertEqual(fake.calls, [])
        self.assertFalse(any("-Start" in c for c in fake.commands))

    def test_actual_main_failed_build_exits_nonzero_without_editor_calls(self):
        code, fake, _, _ = self.run_main(Fake(fail_command="-Start"))
        self.assertEqual(code, 1)
        self.assertEqual(self.final()["stopped"], "build failed")
        self.assertEqual(fake.calls, [])

    def test_recorded_nonfatal_phase_failure_also_exits_nonzero(self):
        code, fake, _, _ = self.run_main(Fake(fail_call="save"), ["--light"])
        self.assertEqual(code, 1)
        report = self.final()
        self.assertIsNone(report["stopped"])
        self.assertEqual(report["state"], "failed")
        self.assertEqual(report["steps"][-1]["step"], "save")
        self.assertEqual(fake.calls, ["ping", "execute_python", "execute_python", "save"])

    def test_success_exits_zero_and_preserves_legacy_report_keys(self):
        code, _, _, _ = self.run_main()
        self.assertEqual(code, 0)
        report = self.final()
        self.assertTrue({"stopped", "ram_before", "ram_after", "steps"} <= set(report))
        self.assertEqual(report["state"], "succeeded")
        self.assertEqual(json.loads(pathlib.Path(report["progress_path"]).read_text()), report)

    def test_guid_build_receipt_waits_on_the_complete_started_id(self):
        job_id = "build-1014-051500-0123456789abcdef0123456789abcdef"
        code, fake, _, _ = self.run_main(Fake(build_id=job_id))
        self.assertEqual(code, 0)
        waits = [c for c in fake.commands if "-Wait" in c]
        self.assertEqual([c[c.index("-Id") + 1] for c in waits], [job_id])
        build = next(s for s in self.final()["steps"] if s["step"] == "build")
        self.assertEqual(build["result"]["job_id"], job_id)

    def test_different_guid_in_same_second_is_rejected_before_editor_calls(self):
        job_id = "build-1014-051500-0123456789abcdef0123456789abcdef"
        old_id = "build-1014-051500-fedcba9876543210fedcba9876543210"
        code, fake, _, _ = self.run_main(Fake(build_id=job_id, wait_id=old_id))
        self.assertEqual(code, 1)
        self.assertEqual(self.final()["stopped"], "build failed")
        self.assertEqual(fake.calls, [])

    def test_failed_guid_build_is_rejected_before_editor_calls(self):
        for status in ("BUILD FAILED", "JOB ENDED"):
            with self.subTest(status=status):
                job_id = "build-1014-051500-0123456789abcdef0123456789abcdef"
                code, fake, _, _ = self.run_main(Fake(build_id=job_id, build_status=status))
                self.assertEqual(code, 1)
                self.assertEqual(self.final()["stopped"], "build failed")
                self.assertEqual(fake.calls, [])

    def test_malformed_guid_receipt_does_not_wait_or_touch_editor(self):
        for suffix in ("012345", "g" * 32, "0" * 33):
            with self.subTest(suffix=suffix):
                code, fake, _, _ = self.run_main(Fake(build_id="build-1014-051500-" + suffix))
                self.assertEqual(code, 1)
                self.assertEqual(fake.calls, [])
                self.assertFalse(any("-Wait" in c for c in fake.commands))

    def test_dry_run_performs_no_actions_or_report_writes(self):
        writer = mock.Mock(side_effect=AssertionError("unexpected write"))
        code, fake, _, _ = self.run_main(args=["--dry-run"], writer=writer)
        self.assertEqual(code, 0)
        writer.assert_not_called()
        self.assertEqual(fake.commands, [])
        self.assertEqual(fake.calls, [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_two_runs_have_unique_reports_and_keep_both_checkpoints(self):
        self.assertEqual(self.run_main(args=["--light"])[0], 0)
        first = self.final()
        self.assertEqual(self.run_main(args=["--light"])[0], 0)
        second = self.final()
        self.assertNotEqual(first["job_id"], second["job_id"])
        self.assertNotEqual(first["progress_path"], second["progress_path"])
        self.assertEqual(json.loads(pathlib.Path(first["progress_path"]).read_text()), first)
        self.assertEqual(json.loads(pathlib.Path(second["progress_path"]).read_text()), second)
        self.assertEqual(len(list(self.root.glob("turn-*.json"))), 3)  # two jobs and legacy alias

    def test_every_completed_step_is_published_and_snapshots_are_independent(self):
        saved = []
        runner = T.Turn(None, None, None, lambda text: None, checkpoint=saved.append, job_id="synthetic")
        runner.step("first", lambda: {"value": 1})
        runner.step("second", lambda: (_ for _ in ()).throw(ValueError("failed")))
        report = runner.finish(None)
        self.assertEqual([r["completed_steps"] for r in saved], [1, 2, 2])
        self.assertEqual(saved[0]["last_step"], "first")
        self.assertEqual(len(saved[0]["steps"]), 1)
        self.assertEqual(report["state"], "failed")

    def test_checkpoint_replacement_is_complete_and_preserves_previous_on_failure(self):
        path = self.root / "checkpoint.json"
        previous = {"completed_steps": 1, "steps": [{"step": "first", "ok": True}]}
        T.atomic_report(str(path), previous)
        next_report = {"completed_steps": 2, "steps": previous["steps"] + [{"step": "second", "ok": True}]}
        def failed_replace(source, destination):
            self.assertEqual(json.loads(pathlib.Path(source).read_text()), next_report)
            self.assertEqual(json.loads(path.read_text()), previous)
            raise OSError("synthetic replace failure")
        with mock.patch.object(T.os, "replace", side_effect=failed_replace), self.assertRaises(OSError):
            T.atomic_report(str(path), next_report)
        self.assertEqual(json.loads(path.read_text()), previous)
        self.assertEqual(list(self.root.glob(".turn-*.tmp")), [])

    def test_serialization_failure_preserves_previous_checkpoint(self):
        path = self.root / "checkpoint.json"
        T.atomic_report(str(path), {"completed_steps": 1})
        with self.assertRaises(TypeError):
            T.atomic_report(str(path), {"result": object()})
        self.assertEqual(json.loads(path.read_text()), {"completed_steps": 1})
        self.assertEqual(list(self.root.glob(".turn-*.tmp")), [])

    def test_checkpoint_failure_stops_before_next_phase_and_records_completed_work(self):
        real_writer = T.atomic_report
        def writer(path, report):
            if report["state"] == "running" and report["completed_steps"] == 2:
                raise OSError("synthetic checkpoint refusal")
            return real_writer(path, report)
        code, fake, _, _ = self.run_main(writer=writer)
        self.assertEqual(code, 1)
        self.assertEqual(fake.calls, [])
        self.assertFalse(any("-Start" in c for c in fake.commands))
        report = self.final()
        self.assertEqual(report["completed_steps"], 2)
        self.assertEqual(report["state"], "failed")
        self.assertIn("checkpoint refusal", report["stopped"])

    def test_initial_checkpoint_failure_performs_no_action(self):
        code, fake, _, _ = self.run_main(writer=mock.Mock(side_effect=OSError("unwritable")))
        self.assertEqual(code, 1)
        self.assertEqual(fake.calls, [])
        self.assertEqual(fake.commands, [])

    def test_failed_legacy_alias_write_marks_job_failed(self):
        real_writer = T.atomic_report
        def writer(path, report):
            if path == str(self.report):
                raise OSError("synthetic alias refusal")
            return real_writer(path, report)
        code, _, _, _ = self.run_main(args=["--light"], writer=writer)
        self.assertEqual(code, 1)
        job = json.loads(next(self.root.glob("turn-*.json")).read_text())
        self.assertEqual(job["state"], "failed")
        self.assertIn("alias refusal", job["stopped"])


if __name__ == "__main__":
    unittest.main()
