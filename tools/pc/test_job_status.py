# SPDX-License-Identifier: MIT
"""Offline checks: synthetic job artifacts only, with no process or editor probes."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

try:
    from tools.pc import job_status
except ModuleNotFoundError:
    import job_status


class JobStatusTests(unittest.TestCase):
    JOB_ID = "job-1014-024500"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.jobs = Path(self.temp.name)

    def artifact(self, suffix, content):
        path = self.jobs / (self.JOB_ID + suffix)
        path.write_bytes(content)
        return path

    def snapshot(self, **kwargs):
        result = job_status.snapshot(self.JOB_ID, self.jobs, **kwargs)
        self.assertEqual(result["schema"], "pc-job-status/v1")
        self.assertEqual(result["job_id"], self.JOB_ID)
        self.assertIs(result["process_verified"], False)
        self.assertIsInstance(result["tail"], list)
        self.assertIsInstance(result["errors"], list)
        return result

    def assert_completed(self, result, code):
        self.assertEqual(result["state"], "completed")
        self.assertEqual(result["evidence"], "exit_marker")
        self.assertEqual(result["exit_code"], code)
        self.assertIs(result["terminal"], True)
        self.assertIsNone(result["launch_pid"])

    def test_default_tail_is_last_40_lines(self):
        self.artifact(".log", "".join(f"line {i}\n" for i in range(45)).encode())
        result = self.snapshot()
        self.assertEqual(result["tail"], [f"line {i}" for i in range(5, 45)])
        self.assertTrue(result["tail_truncated"])
        self.assertEqual(result["errors"], [])

    def test_log_without_exit_is_incomplete_evidence_not_liveness(self):
        self.artifact(".log", b"the last known message\n")
        result = self.snapshot()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["evidence"], "log")
        self.assertIsNone(result["exit_code"])
        self.assertIsNone(result["launch_pid"])
        self.assertFalse(result["terminal"])
        self.assertFalse(result["tail_truncated"])
        self.assertEqual(result["errors"], [])

    def test_empty_log_still_supplies_incomplete_evidence(self):
        self.artifact(".log", b"")
        result = self.snapshot()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["evidence"], "log")
        self.assertEqual(result["tail"], [])
        self.assertEqual(result["errors"], [])

    def test_missing_all_artifacts_is_unknown_with_error(self):
        result = self.snapshot()
        self.assertEqual(result["state"], "unknown")
        self.assertIsNone(result["evidence"])
        self.assertIsNone(result["exit_code"])
        self.assertIsNone(result["launch_pid"])
        self.assertFalse(result["terminal"])
        self.assertEqual(result["tail"], [])
        self.assertTrue(result["errors"])

    def test_exit_records_signed_and_unsigned_32_bit_codes(self):
        for code in (0, 23, -1, -2147483648, 2147483647, 4294967295):
            with self.subTest(code=code):
                self.artifact(".exit", f"done {code}\r\n".encode())
                result = self.snapshot()
                self.assert_completed(result, code)
                self.assertEqual(result["errors"], [])
                self.assertEqual(result["tail"], [])

    def test_exit_accepts_case_insensitive_done(self):
        self.artifact(".exit", b"DONE -23\r\n")
        self.assert_completed(self.snapshot(), -23)

    def test_exit_supports_utf8_and_utf16_boms(self):
        for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16-be"):
            with self.subTest(encoding=encoding):
                raw = "done 23\r\n".encode(encoding)
                if encoding == "utf-16-be":
                    raw = b"\xfe\xff" + raw
                self.artifact(".exit", raw)
                self.assert_completed(self.snapshot(), 23)

    def test_partial_malformed_and_out_of_range_exit_are_unknown(self):
        self.artifact(".log", b"still useful output\n")
        malformed = (
            b"\n", b"done\n", b"done \n", b"done -\n", b"done 1 extra\n",
            b"done 0\ndone 23\n", b"prefix done 0\n", b"done 1.0\n",
            b"done 4294967296\n", b"done -2147483649\n", b"done \xff\n",
        )
        for raw in malformed:
            with self.subTest(raw=raw):
                self.artifact(".exit", raw)
                result = self.snapshot()
                self.assertEqual(result["state"], "unknown")
                self.assertIsNone(result["exit_code"])
                self.assertFalse(result["terminal"])
                self.assertEqual(result["tail"], ["still useful output"])
                self.assertTrue(result["errors"])

    def test_unterminated_exit_cannot_be_mistaken_for_a_complete_prefix(self):
        for raw in (b"done 0", b"done 2", b"done 23\r", b"done 23\n "):
            with self.subTest(raw=raw):
                self.artifact(".exit", raw)
                result = self.snapshot()
                self.assertEqual(result["state"], "unknown")
                self.assertIsNone(result["exit_code"])
                self.assertFalse(result["terminal"])
                self.assertTrue(result["errors"])

    def test_oversize_exit_is_rejected_even_if_prefix_looks_complete(self):
        self.artifact(".exit", b"done 0" + b" " * job_status.MAX_MARKER_BYTES + b"\n")
        result = self.snapshot()
        self.assertEqual(result["state"], "unknown")
        self.assertFalse(result["terminal"])
        self.assertTrue(result["errors"])

    def test_unreadable_exit_reports_error_and_does_not_use_log_as_completion(self):
        (self.jobs / (self.JOB_ID + ".exit")).mkdir()
        self.artifact(".log", b"output\n")
        result = self.snapshot()
        self.assertEqual(result["state"], "unknown")
        self.assertFalse(result["terminal"])
        self.assertTrue(result["errors"])

    def test_valid_exit_takes_precedence_over_invalid_launch_receipt(self):
        self.artifact(".exit", b"done 23\n")
        (self.jobs / (self.JOB_ID + ".started")).mkdir()
        result = self.snapshot()
        self.assert_completed(result, 23)
        self.assertEqual(result["errors"], [])

    def test_malformed_exit_does_not_fall_back_to_a_valid_launch_receipt(self):
        self.artifact(".exit", b"done \n")
        self.artifact(".started", b"pid=42\n")
        result = self.snapshot()
        self.assertEqual(result["state"], "unknown")
        self.assertIsNone(result["launch_pid"])
        self.assertFalse(result["terminal"])
        self.assertTrue(result["errors"])

    def test_valid_launch_receipt_is_incomplete_even_without_log(self):
        for pid in (1, 42, 4294967295):
            with self.subTest(pid=pid):
                self.artifact(".started", f"pid={pid}\r\n".encode())
                result = self.snapshot()
                self.assertEqual(result["state"], "incomplete")
                self.assertEqual(result["evidence"], "launch_receipt")
                self.assertEqual(result["launch_pid"], pid)
                self.assertIsNone(result["exit_code"])
                self.assertFalse(result["terminal"])
                self.assertEqual(result["errors"], [])

    def test_launch_receipt_and_log_are_returned_together(self):
        self.artifact(".started", b"pid=42\n")
        self.artifact(".log", b"one\ntwo\n")
        result = self.snapshot(lines=1)
        self.assertEqual(result["evidence"], "launch_receipt")
        self.assertEqual(result["launch_pid"], 42)
        self.assertEqual(result["tail"], ["two"])
        self.assertTrue(result["tail_truncated"])

    def test_launch_receipt_supports_boms(self):
        for encoding in ("utf-8-sig", "utf-16"):
            with self.subTest(encoding=encoding):
                self.artifact(".started", "pid=42\r\n".encode(encoding))
                result = self.snapshot()
                self.assertEqual(result["evidence"], "launch_receipt")
                self.assertEqual(result["launch_pid"], 42)
                self.assertEqual(result["errors"], [])

    def test_invalid_launch_receipt_is_unknown_even_with_log(self):
        self.artifact(".log", b"output\n")
        for raw in (b"\n", b"pid=\n", b"pid=0\n", b"pid=-1\n", b"pid=4294967296\n",
                    b"pid=42 extra\n", b"pid=42\npid=43\n", b"pid=\xff\n"):
            with self.subTest(raw=raw):
                self.artifact(".started", raw)
                result = self.snapshot()
                self.assertEqual(result["state"], "unknown")
                self.assertIsNone(result["launch_pid"])
                self.assertFalse(result["terminal"])
                self.assertEqual(result["tail"], ["output"])
                self.assertTrue(result["errors"])

    def test_unterminated_launch_receipt_is_unknown(self):
        for raw in (b"pid=42", b"pid=42\r", b"pid=42\n "):
            with self.subTest(raw=raw):
                self.artifact(".started", raw)
                result = self.snapshot()
                self.assertEqual(result["state"], "unknown")
                self.assertIsNone(result["launch_pid"])
                self.assertFalse(result["terminal"])
                self.assertTrue(result["errors"])

    def test_oversize_launch_receipt_is_unknown(self):
        self.artifact(".started", b"pid=42" + b" " * job_status.MAX_MARKER_BYTES + b"\n")
        result = self.snapshot()
        self.assertEqual(result["state"], "unknown")
        self.assertTrue(result["errors"])

    def test_unreadable_launch_receipt_is_unknown(self):
        (self.jobs / (self.JOB_ID + ".started")).mkdir()
        result = self.snapshot()
        self.assertEqual(result["state"], "unknown")
        self.assertTrue(result["errors"])

    def test_unreadable_log_is_reported_even_with_valid_exit(self):
        self.artifact(".exit", b"done 0\n")
        (self.jobs / (self.JOB_ID + ".log")).mkdir()
        result = self.snapshot()
        self.assert_completed(result, 0)
        self.assertEqual(result["tail"], [])
        self.assertTrue(result["errors"])

    def test_invalid_ids_cannot_select_a_path(self):
        invalid_ids = ("", "job-", "other-42", "../job-42", "job-../42",
                       "job-42/other", "job-42\\other", "job-42.exit", "job-a:b",
                       "job- a", "job-42\n", "job-é", "job-" + "a" * 121,
                       "C:\\jobs\\job-42", None, 42)
        for job_id in invalid_ids:
            with self.subTest(job_id=job_id), self.assertRaises(ValueError):
                job_status.snapshot(job_id, self.jobs)

    def test_valid_id_boundaries_and_characters(self):
        for job_id in ("job-a", "job-0", "job-A_0-z", "job-" + "a" * 120):
            with self.subTest(job_id=job_id):
                (self.jobs / (job_id + ".exit")).write_bytes(b"done 0\n")
                result = job_status.snapshot(job_id, self.jobs)
                self.assertEqual(result["job_id"], job_id)
                self.assertEqual(result["state"], "completed")

    def test_lines_must_be_an_integer_in_range(self):
        for lines in (0, -1, 201, 1.5, "40", None, True, False):
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                job_status.snapshot(self.JOB_ID, self.jobs, lines=lines)

    def test_line_limit_boundaries(self):
        self.artifact(".log", b"first\nlast\n")
        self.assertEqual(self.snapshot(lines=1)["tail"], ["last"])
        result = self.snapshot(lines=200)
        self.assertEqual(result["tail"], ["first", "last"])
        self.assertFalse(result["tail_truncated"])

    def test_tail_preserves_blank_lines_crlf_and_final_unterminated_line(self):
        self.artifact(".log", b"alpha\r\n\r\nbeta\n\nlast")
        result = self.snapshot()
        self.assertEqual(result["tail"], ["alpha", "", "beta", "", "last"])
        self.assertFalse(result["tail_truncated"])

    def test_tail_preserves_trailing_blank_line(self):
        self.artifact(".log", b"alpha\n\n")
        self.assertEqual(self.snapshot()["tail"], ["alpha", ""])

    def test_tail_decodes_utf8_and_replaces_invalid_bytes(self):
        self.artifact(".log", "snowman ☃\n".encode() + b"bad \xff\n")
        self.assertEqual(self.snapshot()["tail"], ["snowman ☃", "bad �"])

    def test_byte_cap_drops_only_the_partial_leading_line(self):
        self.artifact(".log", b"x" * (job_status.MAX_TAIL_BYTES + 17) + b"\nlast\n")
        result = self.snapshot()
        self.assertEqual(result["tail"], ["last"])
        self.assertTrue(result["tail_truncated"])

    def test_snapshot_uses_only_exact_id_and_never_mutates_artifacts(self):
        self.artifact(".log", b"selected job output\n")
        self.artifact(".exit.tmp", b"done 0\n")
        (self.jobs / "job-other.exit").write_bytes(b"done 23\n")
        (self.jobs / "job-other.log").write_bytes(b"other job output\n")

        def contents():
            return {path.name: path.read_bytes() for path in self.jobs.iterdir()}

        before = contents()
        result = self.snapshot()
        self.assertEqual(result["state"], "incomplete")
        self.assertEqual(result["evidence"], "log")
        self.assertEqual(result["tail"], ["selected job output"])
        self.assertIsNone(result["exit_code"])
        self.assertEqual(contents(), before)

    def test_byte_cap_retains_a_complete_line_at_the_window_boundary(self):
        suffix = b"keep\n" + b"x" * (job_status.MAX_TAIL_BYTES - 11) + b"\nlast\n"
        self.assertEqual(len(suffix), job_status.MAX_TAIL_BYTES)
        self.artifact(".log", b"prefix\n" + suffix)
        result = self.snapshot()
        self.assertEqual(len(result["tail"]), 3)
        self.assertEqual(result["tail"][0], "keep")
        self.assertEqual(result["tail"][-1], "last")
        self.assertTrue(result["tail_truncated"])

    def test_oversize_unterminated_line_is_not_returned_as_a_complete_line(self):
        self.artifact(".log", b"x" * (job_status.MAX_TAIL_BYTES + 1))
        result = self.snapshot()
        self.assertEqual(result["tail"], [])
        self.assertTrue(result["tail_truncated"])

    def test_artifact_reads_are_bounded_even_for_large_files(self):
        self.artifact(".exit", b"done 0\n")
        self.artifact(".log", b"x" * (8 * job_status.MAX_TAIL_BYTES) + b"\nlast\n")
        original_open = job_status._open_regular
        reads = []
        test = self

        class BudgetedFile:
            def __init__(self, path, source):
                self.path = path
                self.context = source
                self.source = None

            def __enter__(self):
                self.source = self.context.__enter__()
                return self

            def __exit__(self, *args):
                return self.context.__exit__(*args)

            def __getattr__(self, name):
                return getattr(self.source, name)

            def read(self, size=-1):
                test.assertGreaterEqual(size, 0, "unbounded artifact read")
                cap = job_status.MAX_TAIL_BYTES if self.path.suffix == ".log" else job_status.MAX_MARKER_BYTES + 1
                test.assertLessEqual(size, cap)
                reads.append((self.path.suffix, size))
                return self.source.read(size)

        def bounded_open(path):
            return BudgetedFile(path, original_open(path))

        with mock.patch.object(job_status, "_open_regular", bounded_open):
            result = self.snapshot()
        self.assertEqual(result["tail"], ["last"])
        self.assertLessEqual(sum(size for suffix, size in reads if suffix == ".log"),
                             job_status.MAX_TAIL_BYTES + 1)
        self.assertLessEqual(sum(size for suffix, size in reads if suffix == ".exit"),
                             job_status.MAX_MARKER_BYTES + 1)


class JobStatusCliTests(unittest.TestCase):
    JOB_ID = "job-cli-42"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.jobs = Path(self.temp.name)

    def run_cli(self, *args, env=None):
        return subprocess.run(
            [sys.executable, str(Path(job_status.__file__).resolve()), *args],
            capture_output=True, text=True, encoding="utf-8", timeout=10, env=env,
        )

    def test_explicit_id_and_jobs_dir_return_json_with_recorded_nonzero_code(self):
        (self.jobs / (self.JOB_ID + ".exit")).write_bytes(b"done 23\n")
        (self.jobs / (self.JOB_ID + ".log")).write_bytes(b"one\ntwo\n")
        process = self.run_cli("--id", self.JOB_ID, "--jobs-dir", str(self.jobs), "--lines", "1")
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["state"], "completed")
        self.assertEqual(result["exit_code"], 23)
        self.assertEqual(result["tail"], ["two"])
        self.assertIs(result["process_verified"], False)

    def test_default_jobs_dir_is_beneath_localappdata(self):
        default_jobs = self.jobs / "Daedalus" / "jobs"
        default_jobs.mkdir(parents=True)
        (default_jobs / (self.JOB_ID + ".exit")).write_bytes(b"done 0\n")
        env = dict(os.environ, LOCALAPPDATA=str(self.jobs))
        process = self.run_cli("--id", self.JOB_ID, env=env)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["state"], "completed")

    def test_artifact_errors_return_json_and_exit_one(self):
        process = self.run_cli("--id", self.JOB_ID, "--jobs-dir", str(self.jobs))
        self.assertEqual(process.returncode, 1, process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["state"], "unknown")
        self.assertTrue(result["errors"])

    def test_log_only_incomplete_snapshot_exits_zero(self):
        (self.jobs / (self.JOB_ID + ".log")).write_bytes(b"last message\n")
        process = self.run_cli("--id", self.JOB_ID, "--jobs-dir", str(self.jobs))
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["state"], "incomplete")
        self.assertFalse(result["process_verified"])

    def test_invalid_arguments_exit_two(self):
        cases = (
            (), ("--id", "../job-42"), ("--id", self.JOB_ID, "--lines", "0"),
            ("--id", self.JOB_ID, "--lines", "201"),
            ("--id", self.JOB_ID, "--lines", "many"),
        )
        for args in cases:
            with self.subTest(args=args):
                process = self.run_cli(*args, "--jobs-dir", str(self.jobs))
                self.assertEqual(process.returncode, 2, process.stderr)


if __name__ == "__main__":
    unittest.main()
