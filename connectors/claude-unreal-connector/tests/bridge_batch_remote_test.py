# SPDX-License-Identifier: MIT
"""Offline batch admission against actual bridge remote worker lifetimes."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

from bridge_lifecycle_test import Fixture, SOURCE


class RemoteHarness:
    def __init__(self, fixture):
        self.fixture = fixture
        fixture.unreal.LOGDIR = str(Path(__file__).resolve().parent)
        self.workers = []
        self.now = 0
        self.mode = "success"
        self.start_interrupt = None
        self.remote_interrupt = None
        self.malformed_reply = None
        self.effects = []
        self.observed_registration = []
        harness = self

        class Worker:
            def __init__(self, target, args, **kwargs):
                self.target, self.args = target, args

            def start(self):
                # Submission must be visible before a background worker can run or wait on its lock.
                harness.observed_registration.append(
                    any(box is self.args[1] for box in fixture.bridge._remote_workers))
                if harness.mode == "thread_start_failure":
                    raise RuntimeError("thread start failed")
                harness.workers.append(self)
                if harness.start_interrupt is not None:
                    raise harness.start_interrupt

            def finish(self):
                self.target(*self.args)

        class Remote:
            def run_command(self, code, unattended):
                harness.effects.append("remote")
                if harness.remote_interrupt is not None:
                    raise harness.remote_interrupt
                if harness.mode == "lost_reply":
                    raise OSError("reply lost")
                if harness.mode == "missing_receipt":
                    return None
                if harness.mode == "invalid_receipt":
                    return []
                if harness.mode == "explicit_failure":
                    return {"success": False, "result": "known code error", "output": []}
                if harness.mode == "malformed_status":
                    return harness.malformed_reply
                return {"success": True, "output": []}

            def stop(self):
                pass

        self.remote = Remote()
        fixture.stack.enter_context(patch.object(fixture.bridge.threading, "Thread", Worker))
        fixture.stack.enter_context(patch.object(fixture.bridge.time, "time", lambda: self.now))
        fixture.stack.enter_context(patch.object(fixture.bridge, "_remote_node",
                                                 return_value=(self.remote, "offline")))

    def execute(self, **params):
        item = self.fixture.enqueue("execute_python", dict(code="result = None", **params))
        self.fixture.bridge.pump()
        return item


class BatchRemoteTests(unittest.TestCase):
    def batch(self, f):
        return f.enqueue("batch", {"commands": [{"type": "test.mutate"}]})

    def register(self, f):
        calls = []
        f.bridge.register("test.mutate", lambda p: calls.append("mutate"))
        f.bridge.register("test.read", lambda p: "observed", risk="READ")
        return calls

    def assert_busy(self, box):
        self.assertTrue(box["done"].is_set())
        self.assertEqual(box["reply"].get("code"), "BUSY")
        self.assertIs(box["reply"].get("dispatched"), False)
        self.assertEqual(box["reply"].get("effects"), "none")

    def test_worker_registered_before_start_and_waiting_before_lock_blocks_batch(self):
        with Fixture() as f:
            calls = self.register(f)
            remote = RemoteHarness(f)
            _, executing, _ = remote.execute()
            self.assertEqual(remote.observed_registration, [True])
            self.assertFalse(remote.workers[0].args[1]["dispatch_attempted"])
            _, batch, _ = self.batch(f)
            f.bridge.pump()
            self.assert_busy(batch)
            self.assertEqual(calls, [])
            self.assertFalse(executing["done"].is_set())
            remote.workers[0].finish()
            f.bridge.pump()
            _, permitted, _ = self.batch(f)
            f.bridge.pump()
            self.assertEqual(permitted["reply"]["status"], "ok")
            self.assertEqual(calls, ["mutate"])

    def test_timeout_is_terminal_but_late_worker_and_unknown_barrier_survive_restart(self):
        with Fixture() as f:
            calls = self.register(f)
            remote = RemoteHarness(f)
            _, executing, _ = remote.execute(timeout=0, request_id="uncertain")
            remote.now = 1
            f.bridge.pump()
            terminal = dict(executing["reply"])
            self.assertEqual(terminal["code"], "REMOTE_EXECUTION_UNCERTAIN")
            self.assertEqual(f.bridge._running, [])
            self.assertFalse(remote.workers[0].args[1]["done"])
            _, blocked, _ = self.batch(f)
            f.bridge.pump()
            self.assert_busy(blocked)
            remote.workers[0].finish()
            self.assertEqual(remote.effects, ["remote"])
            self.assertEqual(executing["reply"], terminal)
            f.bridge.stop()
            # Fixture's listener threads must remain dormant; only remote jobs use captured Worker.
            with patch.object(f.bridge.threading, "Thread"):
                f.start()
            _, after_restart, _ = self.batch(f)
            _, read, _ = f.enqueue("test.read")
            _, ordinary, _ = f.enqueue("test.mutate")
            f.bridge.pump()
            self.assert_busy(after_restart)
            self.assertEqual(read["reply"]["result"], "observed")
            self.assertEqual(ordinary["reply"]["status"], "ok")
            self.assertEqual(calls, ["mutate"], "remote-only uncertainty is not a global write gate")
            _, replay, _ = f.enqueue("execute_python", {"code": "ignored", "request_id": "uncertain"})
            f.bridge.pump()
            self.assertTrue(replay["reply"]["replayed"])
            self.assertEqual(len(remote.workers), 1)

    def test_interrupted_remote_generator_cannot_hide_outstanding_worker_after_restart(self):
        with Fixture() as f:
            calls = self.register(f)
            remote = RemoteHarness(f)
            _, executing, _ = remote.execute()
            f.bridge.stop()
            self.assertEqual(executing["reply"]["code"], "BRIDGE_STOPPED")
            self.assertEqual(f.bridge._running, [])
            with patch.object(f.bridge.threading, "Thread"):
                f.start()
            _, blocked, _ = self.batch(f)
            f.bridge.pump()
            self.assert_busy(blocked)
            self.assertEqual(calls, [])
            remote.workers[0].finish()
            _, permitted, _ = self.batch(f)
            f.bridge.pump()
            self.assertEqual(permitted["reply"]["status"], "ok")
            self.assertEqual(calls, ["mutate"])

    def test_lost_reply_worker_completion_latches_before_new_batch(self):
        with Fixture() as f:
            calls = self.register(f)
            remote = RemoteHarness(f)
            remote.mode = "lost_reply"
            _, executing, _ = remote.execute()
            remote.workers[0].finish()
            self.assertTrue(remote.workers[0].args[1]["done"])
            f.bridge.pump()
            self.assertEqual(executing["reply"]["code"], "REMOTE_EXECUTION_UNCERTAIN")
            _, blocked, _ = self.batch(f)
            f.bridge.pump()
            self.assert_busy(blocked)
            self.assertEqual(calls, [])

    def test_thread_start_failure_does_not_leave_false_outstanding_worker(self):
        with Fixture() as f:
            calls = self.register(f)
            remote = RemoteHarness(f)
            remote.mode = "thread_start_failure"
            _, executing, _ = remote.execute()
            self.assertIn("thread start failed", executing["reply"]["message"])
            self.assertEqual(f.bridge._remote_workers, [])
            _, permitted, _ = self.batch(f)
            f.bridge.pump()
            self.assertEqual(permitted["reply"]["status"], "ok")
            self.assertEqual(calls, ["mutate"])

    def test_failed_second_start_does_not_forget_equal_first_worker_box(self):
        with Fixture() as f:
            self.register(f)
            remote = RemoteHarness(f)
            remote.execute()
            first = remote.workers[0].args[1]
            remote.mode = "thread_start_failure"
            remote.execute()
            self.assertEqual(len(f.bridge._remote_workers), 1)
            self.assertIs(f.bridge._remote_workers[0], first, "worker removal uses identity, not equal box values")
            f.bridge.stop()
            with patch.object(f.bridge.threading, "Thread"):
                f.start()
            _, blocked, _ = self.batch(f)
            f.bridge.pump()
            self.assert_busy(blocked)
            remote.mode = "success"
            remote.workers[0].finish()
            _, permitted, _ = self.batch(f)
            f.bridge.pump()
            self.assertEqual(permitted["reply"]["status"], "ok")

    def test_lost_reply_after_stop_latches_even_without_command_generator(self):
        with Fixture() as f:
            calls = self.register(f)
            remote = RemoteHarness(f)
            remote.execute()
            f.bridge.stop()
            remote.mode = "lost_reply"
            remote.workers[0].finish()
            with patch.object(f.bridge.threading, "Thread"):
                f.start()
            _, blocked, _ = self.batch(f)
            f.bridge.pump()
            self.assert_busy(blocked)
            self.assertEqual(calls, [])
            self.assertEqual(f.bridge._remote_workers, [], "completed worker records are reaped")
            _, still_blocked, _ = self.batch(f)
            f.bridge.pump()
            self.assert_busy(still_blocked)

    def test_remote_child_keeps_batch_owner_across_wait_and_releases_after_completion(self):
        with Fixture() as f:
            calls = self.register(f)
            remote = RemoteHarness(f)
            _, batch, _ = f.enqueue("batch", {"commands": [
                {"type": "execute_python", "params": {"code": "result = None"}}]})
            _, foreign, _ = f.enqueue("test.mutate")
            f.bridge.pump()
            self.assertFalse(batch["done"].is_set())
            self.assert_busy(foreign)
            self.assertEqual(calls, [])
            self.assertEqual(remote.observed_registration, [True])
            remote.workers[0].finish()
            _, after, _ = f.enqueue("test.mutate")
            f.bridge.pump()
            self.assertEqual(batch["reply"]["status"], "ok")
            self.assertEqual(after["reply"]["status"], "ok")
            self.assertEqual(calls, ["mutate"])

    def test_control_interrupt_during_thread_start_retains_possible_worker(self):
        for kind in (KeyboardInterrupt, SystemExit):
            with self.subTest(kind=kind.__name__), Fixture() as f:
                self.register(f)
                remote = RemoteHarness(f)
                remote.start_interrupt = kind("start receipt interrupted")
                _, executing, _ = f.enqueue("execute_python", {"code": "result = None"})
                with self.assertRaises(kind):
                    f.bridge.pump()
                self.assertEqual(executing["reply"]["code"], "COMMAND_INTERRUPTED")
                self.assertTrue(executing["done"].is_set())
                self.assertEqual(len(f.bridge._remote_workers), 1)
                self.assertFalse(remote.workers[0].args[1]["done"])
                _, blocked, _ = self.batch(f)
                f.bridge.pump()
                self.assert_busy(blocked)
                remote.workers[0].finish()
                _, still_blocked, _ = self.batch(f)
                f.bridge.pump()
                self.assert_busy(still_blocked)

    def test_dispatched_worker_control_interrupt_is_uncertain_and_same_id_never_reexecutes(self):
        for kind in (KeyboardInterrupt, SystemExit):
            with self.subTest(kind=kind.__name__), Fixture() as f:
                self.register(f)
                remote = RemoteHarness(f)
                remote.remote_interrupt = kind("worker interrupted after effect")
                _, executing, _ = remote.execute(request_id="worker-control")
                with self.assertRaises(kind):
                    remote.workers[0].finish()
                self.assertTrue(remote.workers[0].args[1]["done"])
                self.assertIsNone(remote.workers[0].args[1]["error"])
                f.bridge.pump()
                terminal = executing["reply"]
                self.assertEqual(terminal["code"], "REMOTE_EXECUTION_UNCERTAIN")
                self.assertIs(terminal["retryable"], False)
                _, blocked, _ = self.batch(f)
                _, replay, _ = f.enqueue("execute_python", {
                    "code": "must not run", "request_id": "worker-control"})
                f.bridge.pump()
                self.assert_busy(blocked)
                self.assertTrue(replay["reply"]["replayed"])
                self.assertEqual(replay["reply"]["code"], "REMOTE_EXECUTION_UNCERTAIN")
                self.assertEqual(remote.effects, ["remote"])
                self.assertEqual(len(remote.workers), 1)

    def test_missing_dispatched_reply_is_uncertain_without_reinterpreting_valid_failure(self):
        for mode in ("missing_receipt", "invalid_receipt"):
            with self.subTest(mode=mode), Fixture() as f:
                self.register(f)
                remote = RemoteHarness(f)
                remote.mode = mode
                _, executing, _ = remote.execute()
                remote.workers[0].finish()
                f.bridge.pump()
                self.assertEqual(executing["reply"]["code"], "REMOTE_EXECUTION_UNCERTAIN")
                _, blocked, _ = self.batch(f)
                f.bridge.pump()
                self.assert_busy(blocked)

    def test_valid_boolean_success_and_failure_do_not_create_uncertainty_barrier(self):
        for mode, status in (("success", "ok"), ("explicit_failure", "error")):
            with self.subTest(mode=mode), Fixture() as f:
                calls = self.register(f)
                remote = RemoteHarness(f)
                remote.mode = mode
                _, executing, _ = remote.execute()
                remote.workers[0].finish()
                f.bridge.pump()
                self.assertEqual(executing["reply"]["status"], status)
                self.assertNotIn("code", executing["reply"])
                if status == "error":
                    self.assertIn("known code error", executing["reply"]["message"])
                _, permitted, _ = self.batch(f)
                f.bridge.pump()
                self.assertEqual(permitted["reply"]["status"], "ok")
                self.assertEqual(calls, ["mutate"])

    def test_missing_and_nonboolean_status_are_retained_uncertainty_without_second_effect(self):
        replies = [{}, {"output": []}] + [
            {"success": status, "output": []} for status in (None, "true", "false", 1, 0)]
        for receipt in replies:
            with self.subTest(receipt=receipt), Fixture() as f:
                self.register(f)
                remote = RemoteHarness(f)
                remote.mode, remote.malformed_reply = "malformed_status", receipt
                _, executing, _ = remote.execute(request_id="malformed")
                remote.workers[0].finish()
                f.bridge.pump()
                terminal = executing["reply"]
                self.assertEqual(terminal["code"], "REMOTE_EXECUTION_UNCERTAIN")
                self.assertIs(terminal["dispatched"], True)
                self.assertEqual(terminal["effects"], "unknown")
                self.assertIs(terminal["retryable"], False)
                _, blocked, _ = self.batch(f)
                _, replay, _ = f.enqueue("execute_python", {"code": "must not run", "request_id": "malformed"})
                f.bridge.pump()
                self.assert_busy(blocked)
                self.assertTrue(replay["reply"]["replayed"])
                self.assertEqual(replay["reply"]["code"], "REMOTE_EXECUTION_UNCERTAIN")
                self.assertEqual(remote.effects, ["remote"])
                self.assertEqual(len(remote.workers), 1)

    def test_mutant_without_outstanding_worker_gate_exposes_batch_before_late_effect(self):
        needle = "elif _remote_workers:"
        self.assertEqual(SOURCE.count(needle), 1)
        with Fixture(SOURCE.replace(needle, "elif False:", 1)) as f:
            calls = self.register(f)
            remote = RemoteHarness(f)
            remote.execute()
            f.bridge.stop()
            with patch.object(f.bridge.threading, "Thread"):
                f.start()
            _, unsafe, _ = self.batch(f)
            f.bridge.pump()
            with self.assertRaises(AssertionError):
                self.assert_busy(unsafe)
            self.assertEqual(calls, ["mutate"])
            self.assertFalse(remote.workers[0].args[1]["done"])
            self.assertEqual(remote.effects, [])

    def test_mutant_without_uncertain_outcome_gate_exposes_batch_after_late_completion(self):
        needle = 'if _remote_barrier["unknown"]:'
        self.assertEqual(SOURCE.count(needle), 1)
        with Fixture(SOURCE.replace(needle, "if False:", 1)) as f:
            calls = self.register(f)
            remote = RemoteHarness(f)
            _, executing, _ = remote.execute(timeout=0)
            remote.now = 1
            f.bridge.pump()
            self.assertEqual(executing["reply"]["code"], "REMOTE_EXECUTION_UNCERTAIN")
            remote.workers[0].finish()
            _, unsafe, _ = self.batch(f)
            f.bridge.pump()
            with self.assertRaises(AssertionError):
                self.assert_busy(unsafe)
            self.assertEqual(calls, ["mutate"])
            self.assertEqual(remote.effects, ["remote"])


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BatchRemoteTests))
    good = result.testsRun - len(result.failures) - len(result.errors)
    print("%d/%d" % (good, result.testsRun))
    sys.exit(0 if result.wasSuccessful() else 1)
