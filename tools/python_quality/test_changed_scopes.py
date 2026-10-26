# SPDX-License-Identifier: MIT
"""Offline routing contracts; Git integration uses fresh temporary fixtures only."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.python_quality import changed_scopes as routing


ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = Path(__file__).with_name("scopes.json")
POLICY = json.loads(MAP_PATH.read_text(encoding="utf-8"))
BOTH = {"team_handoff", "world_package"}


def record(status: str, *paths: str) -> bytes:
    return b"\0".join(item.encode("utf-8") for item in (status, *paths)) + b"\0"


def selected(result: dict) -> set[str]:
    return {row["scope"] for row in result["matrix"]["include"]}


class NameStatusTests(unittest.TestCase):
    def test_single_path_statuses_and_prefix_boundaries(self):
        for status in ("A", "M", "D", "T"):
            for scope in BOTH:
                with self.subTest(status=status, scope=scope):
                    result = routing.select_scopes(record(status, f"tools/{scope}/file.py"), POLICY)
                    self.assertEqual(selected(result), {scope})
                    self.assertEqual(result["reason"], "verified_diff")
        for path in ("tools/team_handoff_extra/a.py", "tools/world_package2/a.py",
                     "tools/team_handoff\\a.py", " tools/team_handoff/a.py",
                     "tools/python_quality_extra/a.py", ".github/workflows/python-source-quality.yml.extra"):
            with self.subTest(path=path):
                self.assertFalse(routing.select_scopes(record("M", path), POLICY)["any"])

    def test_shared_dependencies_select_both(self):
        for path in POLICY["shared_paths"] + ["tools/python_quality/changed_scopes.py"]:
            with self.subTest(path=path):
                result = routing.select_scopes(record("D", path), POLICY)
                self.assertEqual(selected(result), BOTH)
                self.assertEqual(result["reason"], "shared_change")

    def test_rename_and_copy_endpoints_are_both_considered(self):
        cases = (
            ("R100", "tools/team_handoff/old.py", "docs/new.py", {"team_handoff"}),
            ("R97", "docs/old.py", "tools/world_package/new.py", {"world_package"}),
            ("C075", "tools/team_handoff/old.py", "tools/world_package/new.py", BOTH),
            ("C0", "docs/old.py", "tools/world_package/new.py", {"world_package"}),
            ("R100", "tools/team_handoff/old.py", "tools/python_quality/new.py", BOTH),
        )
        for status, before, after, expected in cases:
            with self.subTest(status=status, before=before, after=after):
                self.assertEqual(routing.parse_name_status_z(record(status, before, after)), (before, after))
                self.assertEqual(selected(routing.select_scopes(record(status, before, after), POLICY)), expected)

    def test_spaces_tabs_newlines_and_literal_backslashes_are_preserved(self):
        paths = ("tools/team_handoff/ leading trailing .py ",
                 "tools/world_package/tab\tand\nnewline.py", "tools/team_handoff/literal\\name.py")
        raw = b"".join(record("M", path) for path in paths)
        self.assertEqual(routing.parse_name_status_z(raw), paths)
        self.assertEqual(selected(routing.select_scopes(raw, POLICY)), BOTH)

    def test_invalid_and_truncated_records_conservatively_select_both(self):
        invalid = (b"M\0tools/team_handoff/a.py", b"M\0", b"\0", b"R100\0old.py\0",
                   b"C75\0", b"M\0\0", b"M\0/absolute.py\0", b"M\0tools/../x.py\0",
                   b"M\0tools//x.py\0", b"M\0./x.py\0", b"M\0x.py/\0",
                   b"M\0tools/team_handoff/\xff.py\0", b"\xff\0x.py\0",
                   b"U\0x.py\0", b"R101\0a\0b\0", b"R-1\0a\0b\0", b"R\0a\0b\0")
        for raw in invalid:
            with self.subTest(raw=raw):
                with self.assertRaises(routing.ScopeError):
                    routing.parse_name_status_z(raw)
                result = routing.select_scopes(raw, POLICY)
                self.assertEqual(selected(result), BOTH)
                self.assertEqual(result["reason"], "invalid_diff")
        for raw in (b"x" * (routing.MAX_DIFF_BYTES + 1), bytearray(b"M\0x.py\0")):
            self.assertEqual(selected(routing.select_scopes(raw, POLICY)), BOTH)

    def test_empty_verified_diff_skips_but_missing_diff_does_not(self):
        self.assertEqual(routing.parse_name_status_z(b""), ())
        self.assertEqual(selected(routing.select_scopes(b"", POLICY)), set())
        self.assertFalse(routing.select_scopes(b"", POLICY)["any"])
        self.assertEqual(selected(routing.select_scopes(None, POLICY)), BOTH)
        self.assertEqual(selected(routing.select_scopes(b"", POLICY, context_valid=False)), BOTH)


class ScopeMapTests(unittest.TestCase):
    def test_published_map_and_order_independence(self):
        self.assertEqual(routing.load_scope_map(MAP_PATH), POLICY)
        policy = copy.deepcopy(POLICY)
        policy["scopes"].reverse()
        policy["shared_paths"].reverse()
        result = routing.select_scopes(None, policy)
        self.assertEqual(result["matrix"]["include"], POLICY["scopes"])

    def test_finite_schema_rejects_extra_commands_paths_and_missing_fields(self):
        mutations = []
        value = copy.deepcopy(POLICY)
        value["command"] = "python arbitrary.py"
        mutations.append(value)
        value = copy.deepcopy(POLICY)
        value["version"] = True
        mutations.append(value)
        value = copy.deepcopy(POLICY)
        del value["shared_paths"]
        mutations.append(value)
        value = copy.deepcopy(POLICY)
        value["scopes"][0]["command"] = "arbitrary"
        mutations.append(value)
        value = copy.deepcopy(POLICY)
        value["scopes"][0]["path"] = "tools/unapproved"
        mutations.append(value)
        value = copy.deepcopy(POLICY)
        value["scopes"][0]["scope"] += "\nany=false"
        mutations.append(value)
        value = copy.deepcopy(POLICY)
        del value["scopes"][0]["path"]
        mutations.append(value)
        value = copy.deepcopy(POLICY)
        value["scopes"][1] = value["scopes"][0]
        mutations.append(value)
        value = copy.deepcopy(POLICY)
        value["shared_paths"][0] = "tools/unapproved"
        mutations.append(value)
        value = copy.deepcopy(POLICY)
        value["shared_paths"].pop()
        mutations.append(value)
        value = copy.deepcopy(POLICY)
        value["shared_paths"][1] = value["shared_paths"][0]
        mutations.append(value)
        for value in mutations + [None, [], {"version": 1}]:
            with self.subTest(value=value):
                with self.assertRaises(routing.ScopeError):
                    routing.validate_scope_map(value)

    def test_map_loader_rejects_duplicate_keys_and_unreadable_or_oversized_inputs(self):
        with tempfile.TemporaryDirectory(prefix="quality-map-") as directory:
            path = Path(directory) / "map.json"
            raw_map = json.dumps(POLICY)
            duplicate = raw_map.replace('"version": 1', '"version": 1, "version": 1')
            duplicate_row = raw_map.replace('"scope": "team_handoff"',
                                            '"scope": "team_handoff", "scope": "team_handoff"')
            for raw in (duplicate.encode(), duplicate_row.encode(), b"{", b"\xff",
                        b" " * (routing.MAX_MAP_BYTES + 1)):
                path.write_bytes(raw)
                with self.subTest(raw_prefix=raw[:80]):
                    with self.assertRaises(routing.ScopeError):
                        routing.load_scope_map(path)
            with self.assertRaises(routing.ScopeError):
                routing.load_scope_map(Path(directory) / "absent.json")


class ContextTests(unittest.TestCase):
    def test_manual_unsupported_and_invalid_contexts_need_no_git(self):
        cases = (("workflow_dispatch", None, None, None, "manual"),
                 ("schedule", None, None, None, "unsupported_event"),
                 ("push", None, "a" * 40, None, "invalid_context"),
                 ("push", "0" * 40, "a" * 40, None, "invalid_context"),
                 ("push", "a" * 40, "b" * 64, None, "invalid_context"),
                 ("push", "not-a-sha", "b" * 40, None, "invalid_context"),
                 ("pull_request", "a" * 40, "b" * 40, None, "invalid_context"))
        with mock.patch.object(routing, "_git") as git:
            for event, base, head, pr_head, reason in cases:
                with self.subTest(event=event, base=base, head=head):
                    result = routing.route_git(POLICY, ROOT, event, base, head, pr_head)
                    self.assertEqual(selected(result), BOTH)
                    self.assertEqual(result["reason"], reason)
            git.assert_not_called()

    def test_failed_git_and_timeout_cannot_become_empty_success(self):
        failures = (subprocess.CompletedProcess(["git"], 128, b"", b"fixture Git failure"),
                    OSError("fixture unavailable"), subprocess.TimeoutExpired(["git"], 15))
        for failure in failures:
            with self.subTest(failure=failure):
                kwargs = {"side_effect": failure} if isinstance(failure, Exception) else {"return_value": failure}
                with mock.patch.object(routing.subprocess, "run", **kwargs):
                    result = routing.route_git(POLICY, ROOT, "push", "a" * 40, "b" * 40)
                self.assertEqual(selected(result), BOTH)
                self.assertEqual(result["reason"], "unavailable_context")

    def test_only_verified_successful_empty_git_diff_can_skip(self):
        for diff_status in (0, 128):
            with self.subTest(diff_status=diff_status):
                def run(command, **kwargs):
                    action = command[1]
                    if action == "rev-parse":
                        output = b"b" * 40 + b"\n"
                    elif action == "cat-file":
                        output = b"commit\n"
                    else:
                        output = b""
                    return subprocess.CompletedProcess(command, diff_status if action == "diff" else 0,
                                                       output, b"fixture error" if diff_status else b"")

                with mock.patch.object(routing.subprocess, "run", side_effect=run) as git:
                    result = routing.route_git(POLICY, ROOT, "push", "a" * 40, "b" * 40)
                self.assertEqual(git.call_args.args[0][1], "diff")
                self.assertEqual(selected(result), set() if diff_status == 0 else BOTH)
                self.assertEqual(result["reason"], "verified_diff" if diff_status == 0 else "unavailable_context")


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-B", "-m", "tools.python_quality.changed_scopes", *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True, timeout=15, check=False)

    def test_manual_cli_emits_only_fixed_safe_github_output_fields(self):
        with tempfile.TemporaryDirectory(prefix="quality-cli-") as directory:
            output = Path(directory) / "github-output"
            output.write_text("previous=value\n", encoding="utf-8")
            result = self.run_cli("--event", "workflow_dispatch", "--scope-map", MAP_PATH,
                                  "--repository", directory, "--github-output", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(selected(payload), BOTH)
            lines = output.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 4)
            self.assertEqual(lines[0], "previous=value")
            self.assertEqual(json.loads(lines[1].removeprefix("matrix=")), payload["matrix"])
            self.assertEqual(lines[2:], ["any=true", "reason=manual"])

    def test_invalid_map_refuses_without_output_mutation(self):
        with tempfile.TemporaryDirectory(prefix="quality-cli-") as directory:
            policy = copy.deepcopy(POLICY)
            policy["scopes"][0]["path"] = "tools/team_handoff\nany=false"
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps(policy), encoding="utf-8")
            output = Path(directory) / "output"
            output.write_bytes(b"preserve\n")
            result = self.run_cli("--event", "workflow_dispatch", "--scope-map", path, "--github-output", output)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("python-quality:", result.stderr)
            self.assertEqual(output.read_bytes(), b"preserve\n")

    def test_output_io_error_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory(prefix="quality-cli-") as directory:
            result = self.run_cli("--event", "workflow_dispatch", "--scope-map", MAP_PATH,
                                  "--github-output", directory)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")


class SyntheticGitContextTests(unittest.TestCase):
    """One bounded local DAG; never inspect, fetch, or modify a source checkout."""

    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="quality-git-fixture-")
        cls.addClassCleanup(temporary.cleanup)
        cls.repository = Path(temporary.name)
        cls.empty_hooks = cls.repository / "empty-hooks"
        cls.empty_hooks.mkdir()
        template = cls.repository / "empty-template"
        template.mkdir()
        cls.git("init", "--quiet", "--template", str(template), ".")
        for key, value in (("core.hooksPath", str(cls.empty_hooks)), ("commit.gpgsign", "false"),
                           ("tag.gpgsign", "false"), ("core.fsmonitor", "false"),
                           ("core.autocrlf", "false"), ("user.name", "Offline Quality Fixture"),
                           ("user.email", "offline-quality@example.invalid")):
            cls.git("config", "--local", key, value)
        cls.put("tools/team_handoff/fixture.txt", "handoff base\n")
        cls.put("tools/team_handoff/rename-me.txt", "exact rename identity\n")
        cls.put("tools/world_package/fixture.txt", "package base\n")
        cls.put("docs/readme.txt", "docs base\n")
        cls.base = cls.commit("fixture base")
        cls.git("checkout", "--quiet", "-b", "fixture-push")
        cls.put("tools/team_handoff/fixture.txt", "handoff first push commit\n")
        cls.commit("push first module")
        cls.put("tools/world_package/fixture.txt", "package second push commit\n")
        cls.push_head = cls.commit("push second module")
        cls.git("checkout", "--quiet", "-b", "fixture-pr", cls.base)
        cls.put("tools/team_handoff/fixture.txt", "handoff PR change\n")
        cls.pr_head = cls.commit("PR module change")
        cls.git("checkout", "--quiet", "-b", "fixture-main-context", cls.base)
        cls.put("tools/world_package/fixture.txt", "unrelated main change\n")
        cls.pr_base = cls.commit("unrelated main module change")
        cls.git("merge", "--quiet", "--no-ff", "--no-edit", "fixture-pr")
        cls.merge_head = cls.git("rev-parse", "HEAD").strip()
        cls.git("checkout", "--quiet", "-b", "fixture-rename", cls.base)
        cls.git("mv", "tools/team_handoff/rename-me.txt", "tools/world_package/moved.txt")
        cls.rename_head = cls.commit("rename between approved roots")
        cls.git("checkout", "--quiet", "-b", "fixture-delete", cls.base)
        cls.git("rm", "--quiet", "tools/team_handoff/fixture.txt")
        cls.delete_head = cls.commit("delete from handoff root")

    @classmethod
    def git(cls, *args):
        command = ["git", "-c", f"core.hooksPath={cls.empty_hooks}", "-c", "commit.gpgsign=false",
                   "-c", "tag.gpgsign=false", "-c", "core.fsmonitor=false", *args]
        try:
            result = subprocess.run(command, cwd=cls.repository, capture_output=True, text=True,
                                    timeout=15, check=False)
        except OSError as exc:
            raise AssertionError(f"Synthetic Git action stopped; no retry: {command!r}: {exc}") from exc
        if result.returncode:
            raise AssertionError(f"Synthetic Git action stopped; no retry: {command!r}; "
                                 f"target={cls.repository}; exit={result.returncode}; {result.stderr.strip()}")
        return result.stdout

    @classmethod
    def put(cls, path, content):
        target = cls.repository / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    @classmethod
    def commit(cls, message):
        cls.git("add", "--", "tools", "docs")
        cls.git("commit", "--quiet", "-m", message)
        return cls.git("rev-parse", "HEAD").strip()

    def checkout(self, identity):
        self.git("checkout", "--quiet", "--detach", identity)

    def test_push_range_includes_earlier_commits(self):
        self.checkout(self.push_head)
        result = routing.route_git(POLICY, self.repository, "push", self.base, self.push_head)
        self.assertEqual(result["reason"], "verified_diff")
        self.assertEqual(selected(result), BOTH)

    def test_verified_pr_merge_excludes_unrelated_base_changes(self):
        self.checkout(self.merge_head)
        result = routing.route_git(POLICY, self.repository, "pull_request", self.pr_base,
                                   self.merge_head, self.pr_head)
        self.assertEqual(result["reason"], "verified_diff")
        self.assertEqual(selected(result), {"team_handoff"})

    def test_stale_nonmerge_mismatched_and_unavailable_contexts_fall_back(self):
        cases = (("pull_request", self.base, self.merge_head, self.pr_head, self.merge_head),
                 ("pull_request", self.base, self.pr_head, self.pr_head, self.pr_head),
                 ("pull_request", self.pr_base, self.merge_head, self.push_head, self.merge_head),
                 ("push", self.base, self.push_head, None, self.merge_head),
                 ("push", "f" * 40, self.push_head, None, self.push_head),
                 ("push", self.push_head, self.base, None, self.base))
        for event, base, head, pr_head, checkout in cases:
            with self.subTest(event=event, base=base, head=head, checkout=checkout):
                self.checkout(checkout)
                result = routing.route_git(POLICY, self.repository, event, base, head, pr_head)
                self.assertEqual(selected(result), BOTH)
                self.assertEqual(result["reason"], "unavailable_context")

    def test_actual_rename_and_deletion_select_affected_roots(self):
        for head, expected in ((self.rename_head, BOTH), (self.delete_head, {"team_handoff"})):
            with self.subTest(head=head):
                self.checkout(head)
                result = routing.route_git(POLICY, self.repository, "push", self.base, head)
                self.assertEqual(result["reason"], "verified_diff")
                self.assertEqual(selected(result), expected)


if __name__ == "__main__":
    unittest.main()
