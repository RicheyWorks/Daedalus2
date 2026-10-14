# SPDX-License-Identifier: MIT
"""Production bridge regressions using in-memory remote workers and effects.

No listener, sockets, editor, real remote client, sleeps, or shared fake mutations.
The only executed user program increments a counter on this test's Unreal stub.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest import mock

TESTS = Path(__file__).resolve().parent
BRIDGE = TESTS.parent / "plugin/ClaudeUnrealBridge/Content/Python/claude_unreal_bridge.py"
CODE = "unreal.counter += 1\nresult = unreal.counter"


def load_file(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Clock:
    def __init__(self):
        self.now = 0

    def time(self):
        self.now += 1
        return self.now

    def sleep(self, seconds):
        pass


class Lock:
    def __init__(self):
        self.available, self.error, self.acquires, self.releases = True, None, 0, 0

    def acquire(self, timeout):
        assert timeout == 30
        self.acquires += 1
        if self.error:
            raise self.error
        return self.available

    def release(self):
        self.releases += 1


class RemoteOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.fake = load_file(TESTS / "fake_unreal.py", "remote_test_unreal")
        self.fake.GAME_THREAD[0] = threading.get_ident()
        self.fake.LOGDIR = str(TESTS)
        self.fake.counter = 0
        self.original_level, self.original_state = list(self.fake.LEVEL), dict(self.fake.STATE)
        self.events, self.workers = [], []
        self.mode, self.transport_error, self.cleanup_failure = "success", OSError("reply lost"), False
        self.deferred = False
        fixture = self

        class Remote:
            def start(self):
                fixture.events.append("start")
                if fixture.mode == "start_failure":
                    raise OSError("start failed before command")

            def stop(self):
                fixture.events.append("cleanup")
                if fixture.cleanup_failure:
                    raise OSError("cleanup failed")

            @property
            def remote_nodes(self):
                return [] if fixture.mode == "off" else [
                    {"node_id": "fake-node", "project_root": str(TESTS)}]

            def open_command_connection(self, node):
                fixture.events.append("open")
                if fixture.mode == "open_failure":
                    raise OSError("open failed before command")

            def run_command(self, command, unattended):
                fixture.events.append("run_entered")
                if unattended is not True:
                    raise AssertionError("remote call must be unattended")
                if fixture.mode == "entry_error":
                    raise fixture.transport_error
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    exec(compile(command, "<fake-remote>", "exec"), {"unreal": fixture.fake})
                fixture.events.append("remote_effect")
                if fixture.mode == "lost_reply":
                    raise fixture.transport_error
                if fixture.mode == "code_error":
                    return {"success": False, "result": "remote code error", "output": []}
                return {"success": True, "result": "None", "output": [
                    {"type": "Info", "output": line} for line in output.getvalue().splitlines()]}

        class Worker:
            def __init__(self, target, args, **kwargs):
                self.target, self.args = target, args

            def start(self):
                fixture.workers.append(self)
                if not fixture.deferred:
                    self.finish()

            def finish(self):
                self.target(*self.args)

        self.rex = types.ModuleType("remote_execution")
        self.rex.RemoteExecution = Remote
        self.modules_patch = mock.patch.dict(sys.modules, {"unreal": self.fake, "remote_execution": self.rex})
        self.modules_patch.start()
        self.addCleanup(self.modules_patch.stop)
        self.env_patch = mock.patch.dict(os.environ, {"CLAUDE_UNREAL_ALLOW": "READ,MUTATE"})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.bridge = load_file(BRIDGE, "remote_outcome_test_bridge")
        self.clock, self.lock = Clock(), Lock()
        self.bridge.time, self.bridge._remote_lock = self.clock, self.lock
        self.thread_patch = mock.patch.object(self.bridge.threading, "Thread", Worker)
        self.thread_patch.start()
        self.addCleanup(self.thread_patch.stop)
        self.socket_patch = mock.patch.object(self.bridge.socket, "socket", side_effect=AssertionError("no sockets"))
        self.socket_patch.start()
        self.addCleanup(self.socket_patch.stop)
        self.local_patch = mock.patch.object(self.bridge, "_exec_here", wraps=self.bridge._exec_here)
        self.local = self.local_patch.start()
        self.addCleanup(self.local_patch.stop)

    def tearDown(self):
        self.assertEqual(self.fake.LEVEL, self.original_level)
        self.assertEqual(self.fake.STATE, self.original_state)
        self.assertEqual(self.fake.CALLS, [])

    def dispatch(self, request_id=None, ident="offline", **params):
        params = dict({"code": CODE}, **params)
        if request_id is not None:
            params["request_id"] = request_id
        box = {"done": threading.Event(), "reply": None}
        self.bridge._start({"id": ident, "type": "execute_python", "params": params}, box)
        return box

    def reply(self, **params):
        box = self.dispatch(**params)
        self.assertTrue(box["done"].is_set())
        return box["reply"]

    def assert_uncertain(self, reply):
        self.assertEqual(reply["status"], "error")
        self.assertEqual(reply.get("code"), "REMOTE_EXECUTION_UNCERTAIN")
        self.assertIs(reply["dispatched"], True)
        self.assertEqual(reply["effects"], "unknown")
        self.assertIs(reply["retryable"], False)
        self.assertTrue(reply["message"])
        self.local.assert_not_called()

    def assert_fallback_once(self, reply):
        self.assertEqual(reply["status"], "ok")
        self.assertEqual(reply["result"]["result"], 1)
        self.assertIs(reply["result"]["unattended"], False)
        self.assertIn("ran directly", reply["result"]["note"])
        self.assertEqual(self.fake.counter, 1)
        self.assertEqual(self.local.call_count, 1)
        self.assertNotIn("run_entered", self.events)

    def test_oserror_after_remote_effect_never_replays_locally(self):
        self.mode = "lost_reply"
        reply = self.reply()
        self.assert_uncertain(reply)
        self.assertEqual(self.fake.counter, 1)
        self.assertEqual(self.events.count("run_entered"), 1)
        self.assertEqual(self.events.count("cleanup"), 1)
        self.assertEqual(self.lock.releases, 1)
        self.assertIn("OSError: reply lost", reply["message"])
        self.assertIsNone(self.bridge._remote["rx"])

    def test_timeout_error_after_remote_effect_never_replays_locally(self):
        self.mode, self.transport_error = "lost_reply", TimeoutError("remote receive timed out")
        reply = self.reply()
        self.assert_uncertain(reply)
        self.assertEqual(self.fake.counter, 1)
        self.assertEqual(self.events.count("run_entered"), 1)
        self.assertIn("TimeoutError: remote receive timed out", reply["message"])

    def test_run_entry_exception_before_effect_is_still_unknown(self):
        self.mode = "entry_error"
        reply = self.reply()
        self.assert_uncertain(reply)
        self.assertEqual(self.fake.counter, 0)
        self.assertEqual(self.events.count("run_entered"), 1)
        self.assertEqual(self.lock.releases, 1)

    def test_remote_off_falls_back_once_and_closes_provisional_client(self):
        self.mode = "off"
        self.assert_fallback_once(self.reply())
        self.assertEqual(self.events.count("cleanup"), 1)
        self.assertEqual(self.lock.releases, 1)

    def test_missing_remote_module_falls_back_once(self):
        with mock.patch.dict(sys.modules, {"remote_execution": None}):
            reply = self.reply()
        self.assert_fallback_once(reply)
        self.assertEqual(self.events, [])

    def test_start_failure_falls_back_once_and_closes_provisional_client(self):
        self.mode = "start_failure"
        self.assert_fallback_once(self.reply())
        self.assertEqual(self.events, ["start", "cleanup"])
        self.assertIsNone(self.bridge._remote["rx"])

    def test_open_failure_falls_back_once_and_closes_provisional_client(self):
        self.mode = "open_failure"
        self.assert_fallback_once(self.reply())
        self.assertEqual(self.events, ["start", "open", "cleanup"])
        self.assertIsNone(self.bridge._remote["rx"])

    def test_remote_lock_busy_falls_back_without_releasing_unowned_lock(self):
        self.lock.available = False
        self.assert_fallback_once(self.reply())
        self.assertEqual(self.lock.releases, 0)
        self.assertEqual(self.events, [])

    def test_remote_lock_error_falls_back_without_touching_another_owners_client(self):
        other_owner = mock.Mock()
        self.bridge._remote.update(rx=other_owner, node="another-node", error="another-state")
        previous = dict(self.bridge._remote)
        self.lock.error = OSError("lock acquire failed")
        self.assert_fallback_once(self.reply())
        self.assertEqual(self.lock.releases, 0)
        other_owner.stop.assert_not_called()
        self.assertEqual(self.bridge._remote, previous)

    def test_wrap_failure_occurs_before_attempt_and_can_fall_back(self):
        with mock.patch.object(self.bridge, "_wrap", side_effect=ValueError("wrap failed")):
            reply = self.reply()
        self.assert_fallback_once(reply)
        self.assertIn("wrap failed", reply["result"]["note"])
        self.assertEqual(self.lock.releases, 1)

    def test_normal_remote_success_retains_unattended_result(self):
        reply = self.reply()
        self.assertEqual(reply["status"], "ok")
        self.assertEqual(reply["result"], {"stdout": "", "result": 1, "unattended": True})
        self.assertEqual(self.fake.counter, 1)
        self.local.assert_not_called()
        self.assertNotIn("cleanup", self.events)

    def test_remote_reported_code_error_preserves_error_without_replay(self):
        self.mode = "code_error"
        reply = self.reply()
        self.assertEqual(reply["status"], "error")
        self.assertNotIn("code", reply)
        self.assertIn("remote code error", reply["message"])
        self.assertEqual(self.fake.counter, 1)
        self.local.assert_not_called()

    def test_explicit_attended_execution_stays_direct(self):
        reply = self.reply(unattended=False)
        self.assertEqual(reply["status"], "ok")
        self.assertEqual(reply["result"], {"stdout": "", "result": 1, "unattended": False})
        self.assertEqual(self.local.call_count, 1)
        self.assertEqual(self.fake.counter, 1)
        self.assertEqual(self.events, [])
        self.assertEqual(self.workers, [])

    def test_outstanding_worker_timeout_late_finish_cannot_replace_terminal_reply(self):
        self.deferred = True
        box = self.dispatch(request_id="late", timeout=5)
        self.assertFalse(box["done"].is_set())
        self.assertEqual(self.fake.counter, 0)
        self.clock.now = 10
        self.bridge.pump(max_jobs=0)
        self.assertTrue(box["done"].is_set())
        terminal = box["reply"]
        self.assert_uncertain(terminal)
        self.assertEqual(self.bridge._running, [])
        self.workers[0].finish()
        self.assertEqual(self.fake.counter, 1)
        self.assertIs(box["reply"], terminal)
        self.assertEqual(self.bridge._replies["late"]["code"], "REMOTE_EXECUTION_UNCERTAIN")
        replay = self.reply(request_id="late", ident="retry")
        self.assert_uncertain(replay)
        self.assertTrue(replay.get("replayed"))
        self.assertEqual(replay["id"], "retry")
        self.assertEqual(len(self.workers), 1)
        self.assertEqual(self.fake.counter, 1)

    def test_uncertain_request_id_retry_returns_terminal_without_new_remote_effect(self):
        self.mode = "lost_reply"
        first = self.reply(request_id="same", ident="first")
        self.assert_uncertain(first)
        second = self.reply(request_id="same", ident="second")
        self.assert_uncertain(second)
        self.assertTrue(second.get("replayed"))
        self.assertEqual(second["id"], "second")
        self.assertEqual(second["message"], first["message"])
        self.assertEqual(self.events.count("run_entered"), 1)
        self.assertEqual(len(self.workers), 1)
        self.assertEqual(self.fake.counter, 1)

    def test_uncertain_replay_retention_uses_existing_bounded_cache(self):
        self.bridge.REPLAY_KEEP = 2
        self.mode = "lost_reply"
        for request_id in ("one", "two", "three"):
            self.assert_uncertain(self.reply(request_id=request_id))
        self.assertEqual(set(self.bridge._replies), {"two", "three"})
        self.assertEqual(self.bridge._replay_order, ["two", "three"])
        self.assertEqual(self.fake.counter, 3)

    def test_cleanup_failure_preserves_attempt_error_and_releases_lock(self):
        self.mode, self.cleanup_failure = "lost_reply", True
        reply = self.reply()
        self.assert_uncertain(reply)
        self.assertIn("OSError: reply lost", reply["message"])
        self.assertNotIn("cleanup failed", reply["message"])
        self.assertEqual(self.fake.counter, 1)
        self.assertEqual(self.lock.releases, 1)
        self.assertIsNone(self.bridge._remote["rx"])

    def test_ordinary_exception_cannot_supply_structured_uncertainty_metadata(self):
        class OtherError(RuntimeError):
            code, dispatched, effects, retryable = "REMOTE_EXECUTION_UNCERTAIN", True, "unknown", False
        reply = self.bridge._error({"id": "test"}, OtherError("ordinary error"))
        self.assertEqual(reply["status"], "error")
        self.assertFalse({"code", "dispatched", "effects", "retryable"} & set(reply))

    def test_invalid_timeout_is_rejected_before_starting_worker(self):
        for timeout in ("invalid", -1, "-0.01", float("nan"), float("inf"), -float("inf")):
            with self.subTest(timeout=timeout):
                reply = self.reply(timeout=timeout)
                self.assertEqual(reply["status"], "error")
                self.assertIn("ValueError", reply["message"])
        self.assertEqual(self.workers, [])
        self.assertEqual(self.fake.counter, 0)
        self.local.assert_not_called()

    def test_zero_timeout_remains_allowed_for_immediate_completed_worker(self):
        reply = self.reply(timeout=0)
        self.assertEqual(reply["status"], "ok")
        self.assertEqual(reply["result"]["result"], 1)
        self.assertEqual(self.fake.counter, 1)
        self.assertEqual(len(self.workers), 1)
        self.local.assert_not_called()


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    passed = max(0, result.testsRun - len(result.failures) - len(result.errors))
    print("%d/%d" % (passed, result.testsRun))
    sys.exit(0 if result.wasSuccessful() else 1)
