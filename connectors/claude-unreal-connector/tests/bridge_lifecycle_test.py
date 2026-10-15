# SPDX-License-Identifier: MIT
"""Offline lifecycle regressions: actual bridge, fake Unreal, no listeners or sleeps.

Run: python connectors/claude-unreal-connector/tests/bridge_lifecycle_test.py
"""
import contextlib
import importlib.util
import json
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest.mock import Mock, patch


HERE = Path(__file__).resolve().parent
BRIDGE = HERE.parent / "plugin" / "ClaudeUnrealBridge" / "Content" / "Python" / "claude_unreal_bridge.py"
SOURCE = BRIDGE.read_text(encoding="utf-8")


class Listener:
    def __init__(self):
        self.address = None
        self.closed = 0

    def setsockopt(self, *args):
        pass

    def bind(self, address):
        self.address = address

    def listen(self, backlog):
        pass

    def getsockname(self):
        return self.address

    def close(self):
        self.closed += 1

    def accept(self):
        raise AssertionError("offline tests must never accept a real connection")


class DormantThread:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.started = False

    def start(self):
        self.started = True  # Deliberately never execute the listener loop.


class Connection:
    """Memory input/output with a deterministic callback before a request arrives."""
    def __init__(self, request, before_recv=None):
        self.data = (json.dumps(request) + "\n").encode()
        self.before_recv = before_recv
        self.sent = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def settimeout(self, timeout):
        self.timeout = timeout

    def recv(self, size):
        if self.before_recv:
            callback, self.before_recv = self.before_recv, None
            callback()
        data, self.data = self.data, b""
        return data

    def sendall(self, data):
        self.sent.append(json.loads(data))


class Fixture:
    def __init__(self, source=SOURCE):
        spec = importlib.util.spec_from_file_location("lifecycle_fake_unreal", HERE / "fake_unreal.py")
        self.unreal = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.unreal)
        self.owner = threading.get_ident()
        self.unreal.GAME_THREAD[0] = self.owner
        self.unreal.register_slate_post_tick_callback = Mock(return_value="test-tick")
        self.unreal.unregister_slate_post_tick_callback = Mock()
        # Assert cleanup's thread explicitly: the older fake destroy_actor lacks this check.
        destroy = self.unreal.EditorActorSubsystem.destroy_actor

        def checked_destroy(subsystem, actor):
            self.unreal._game_thread_only("destroy_actor")
            return destroy(subsystem, actor)

        self.unreal.EditorActorSubsystem.destroy_actor = checked_destroy
        self.bridge = types.ModuleType("lifecycle_bridge_under_test")
        self.bridge.__file__ = str(BRIDGE)
        with patch.dict(sys.modules, {"unreal": self.unreal}):
            exec(compile(source, str(BRIDGE), "exec"), self.bridge.__dict__)
        self.bridge.set_policy(self.bridge.RISKS)
        self.stack = contextlib.ExitStack()
        self.listeners = []

    def __enter__(self):
        def listener(*args, **kwargs):
            result = Listener()
            self.listeners.append(result)
            return result

        self.stack.enter_context(patch.object(self.bridge.socket, "socket", side_effect=listener))
        self.stack.enter_context(patch.object(self.bridge.threading, "Thread", DormantThread))
        self.start()
        return self

    def __exit__(self, *args):
        try:
            self.bridge.stop()
            # Mutant fixtures may intentionally omit production cleanup.
            for gen, _, _ in list(self.bridge._running):
                gen.close()
        finally:
            self.stack.close()

    def start(self):
        return self.bridge.start(9877)

    def enqueue(self, command, params=None, request_id=1):
        request = {"id": request_id, "type": command, "params": params or {}}
        box = {"done": threading.Event(), "reply": None}
        accepted, job_id = self.bridge._admit(request, box, self.bridge._server["generation"])
        if not accepted:
            raise AssertionError("fixture request should be admitted")
        return request, box, job_id

    def capture(self, params=None):
        item = self.enqueue("capture_view", params)
        self.bridge.pump()
        return item

    def captures(self):
        return [actor for actor in self.unreal.LEVEL if actor.cls == "SceneCapture2D"]


class LifecycleTests(unittest.TestCase):
    def assert_stopped(self, box, dispatched):
        self.assertTrue(box["done"].is_set(), "every accepted request receives a terminal event")
        self.assertEqual(box["reply"]["status"], "error")
        self.assertEqual(box["reply"]["code"], "BRIDGE_STOPPED")
        self.assertIs(box["reply"]["dispatched"], dispatched)
        self.assertEqual(box["reply"]["effects"], "unknown" if dispatched else "none")

    def test_actual_capture_finally_runs_on_owner_thread_and_repeat_stop_is_idempotent(self):
        with Fixture() as f:
            _, box, _ = f.capture()
            retained = f.bridge._running[0][0]
            self.assertEqual(len(f.captures()), 1)
            self.assertFalse(box["done"].is_set())
            listener = f.listeners[0]
            f.bridge.stop()
            self.assert_stopped(box, True)
            self.assertEqual(f.captures(), [])
            self.assertEqual(f.bridge._running, [])
            self.assertEqual(listener.closed, 1)
            f.unreal.unregister_slate_post_tick_callback.assert_called_once_with("test-tick")
            reply = dict(box["reply"])
            f.bridge.stop()
            self.assertEqual(box["reply"], reply)
            self.assertEqual(listener.closed, 1)
            self.assertEqual(f.unreal.CALLS.count("destroy SceneCapture2D"), 1)
            retained.close()
            self.assertEqual(f.unreal.CALLS.count("destroy SceneCapture2D"), 1)

    def test_pending_commands_receive_no_effects_and_never_execute_after_restart(self):
        with Fixture() as f:
            calls = []
            f.bridge.register("test.mutate", lambda p: calls.append(p) or "ran")
            _, box, _ = f.enqueue("test.mutate")
            f.bridge.stop()
            self.assert_stopped(box, False)
            f.start()
            f.bridge.pump()
            self.assertEqual(calls, [])
            self.assertTrue(f.bridge._jobs.empty())

    def test_completed_async_reply_remains_unchanged_after_stop_and_restart(self):
        with Fixture() as f:
            f.bridge.register("test.done", lambda p: {"answer": False})
            _, box, job_id = f.enqueue("test.done", {"async": True})
            f.bridge.pump()
            completed = dict(box["reply"])
            f.bridge.stop()
            f.start()
            polled = f.bridge._job_result({"id": 99}, {"job_id": job_id})
            self.assertEqual(polled["result"]["state"], "done")
            self.assertEqual(polled["result"]["reply"], completed)
            self.assertEqual(completed["result"], {"answer": False})

    def test_interrupted_async_reply_remains_terminal_after_restart(self):
        with Fixture() as f:
            _, box, job_id = f.capture({"async": True})
            f.bridge.stop()
            self.assert_stopped(box, True)
            f.start()
            reply = f.bridge._job_result({"id": 99}, {"job_id": job_id})
            self.assertEqual(reply["result"]["state"], "done")
            self.assertEqual(reply["result"]["reply"], box["reply"])
            f.bridge.pump()
            self.assertEqual(f.captures(), [])

    def test_cleanup_failure_is_reported_and_other_generators_and_pending_jobs_settle(self):
        with Fixture() as f:
            cleaned = []

            def failing(p):
                try:
                    yield
                finally:
                    cleaned.append("bad")
                    raise ValueError("cleanup boom")

            def healthy(p):
                try:
                    yield
                finally:
                    cleaned.append("good")

            f.bridge.register("test.bad", failing)
            f.bridge.register("test.good", healthy)
            _, bad, _ = f.enqueue("test.bad")
            _, good, _ = f.enqueue("test.good")
            f.bridge.pump()
            _, pending, _ = f.enqueue("test.good")
            f.bridge.stop()
            self.assert_stopped(bad, True)
            self.assertIn("ValueError: cleanup boom", bad["reply"]["cleanup_error"])
            self.assert_stopped(good, True)
            self.assertNotIn("cleanup_error", good["reply"])
            self.assert_stopped(pending, False)
            self.assertEqual(cleaned, ["bad", "good"])

    def test_stop_inside_generator_defers_close_until_unwind_and_blocks_later_queue(self):
        with Fixture() as f:
            events = []

            def self_stop(p):
                try:
                    events.append("entered")
                    f.bridge.stop()
                    events.append("stop returned")
                    self.assertNotIn("finally", events)
                    with self.assertRaises(RuntimeError):
                        f.start()
                    yield
                    events.append("resumed")
                finally:
                    events.append("finally")

            f.bridge.register("test.self_stop", self_stop)
            f.bridge.register("test.later", lambda p: events.append("later"))
            _, active, _ = f.enqueue("test.self_stop")
            _, pending, _ = f.enqueue("test.later")
            f.bridge.pump()
            self.assertEqual(events, ["entered", "stop returned", "finally"])
            self.assert_stopped(active, True)
            self.assert_stopped(pending, False)
            f.start()
            f.bridge.pump()
            self.assertEqual(events, ["entered", "stop returned", "finally"])

    def test_known_completion_during_self_stop_preserves_success(self):
        for generator in (False, True):
            with self.subTest(generator=generator), Fixture() as f:
                def ordinary(p):
                    f.bridge.stop()
                    return False

                def completed_generator(p):
                    f.bridge.stop()
                    if False:
                        yield
                    return False

                f.bridge.register("test.complete", completed_generator if generator else ordinary)
                _, completed, _ = f.enqueue("test.complete")
                f.bridge.pump()
                self.assertTrue(completed["done"].is_set())
                self.assertEqual(completed["reply"], {"id": 1, "status": "ok", "result": False})

    def test_cleanup_can_reenter_stop_but_cannot_restart_until_cleanup_finishes(self):
        with Fixture() as f:
            events = []

            def nested(p):
                try:
                    yield
                finally:
                    events.append("cleanup")
                    f.bridge.stop()
                    with self.assertRaises(RuntimeError):
                        f.start()
                    events.append("done")

            f.bridge.register("test.nested", nested)
            _, box, _ = f.enqueue("test.nested")
            f.bridge.pump()
            f.bridge.stop()
            self.assertEqual(events, ["cleanup", "done"])
            self.assert_stopped(box, True)
            f.start()

    def test_off_owner_stop_rejects_before_state_or_resource_changes(self):
        with Fixture() as f:
            _, box, _ = f.capture()
            state = dict(f.bridge._server)
            running = list(f.bridge._running)
            with patch.object(f.bridge.threading, "get_ident", return_value=f.owner + 1):
                with self.assertRaises(RuntimeError):
                    f.bridge.stop()
            self.assertEqual(f.bridge._server, state)
            self.assertEqual(f.bridge._running, running)
            self.assertEqual(len(f.captures()), 1)
            self.assertFalse(box["done"].is_set())
            self.assertEqual(f.listeners[0].closed, 0)
            f.unreal.unregister_slate_post_tick_callback.assert_not_called()

    def test_stale_client_spanning_stop_and_restart_cannot_enqueue(self):
        with Fixture() as f:
            calls = []
            f.bridge.register("test.mutate", lambda p: calls.append(1))
            old_generation = f.bridge._server["generation"]

            def restart():
                f.bridge.stop()
                f.start()

            conn = Connection({"id": 41, "type": "test.mutate", "params": {"async": True}}, restart)
            f.bridge._client(conn, old_generation)
            self.assertEqual(len(conn.sent), 1)
            self.assertEqual(conn.sent[0]["code"], "BRIDGE_STOPPED")
            self.assertFalse(conn.sent[0]["dispatched"])
            self.assertEqual(conn.sent[0]["effects"], "none")
            self.assertTrue(conn.closed)
            self.assertTrue(f.bridge._jobs.empty())
            self.assertEqual(f.bridge._job_boxes, {})
            f.bridge.pump()
            self.assertEqual(calls, [])

    def test_memory_client_accepted_async_job_gets_retained_shutdown_result(self):
        with Fixture() as f:
            generation = f.bridge._server["generation"]
            conn = Connection({"id": 42, "type": "capture_view", "params": {"async": True}})
            f.bridge._client(conn, generation)
            self.assertEqual(conn.sent[0]["status"], "ok")
            job_id = conn.sent[0]["result"]["job_id"]
            f.bridge.stop()
            f.start()
            poll = Connection({"id": 43, "type": "job_result", "params": {"job_id": job_id}})
            f.bridge._client(poll, f.bridge._server["generation"])
            result = poll.sent[0]["result"]
            self.assertEqual(result["state"], "done")
            self.assertFalse(result["reply"]["dispatched"])
            self.assertEqual(result["reply"]["effects"], "none")
            self.assertEqual(result["reply"]["code"], "BRIDGE_STOPPED")

    def test_timeout_race_does_not_overwrite_shared_shutdown_reply(self):
        with Fixture() as f:
            captured = []
            original_admit = f.bridge._admit

            def admit(*args):
                captured.append(args[1])
                return original_admit(*args)

            class RaceEvent:
                done = False
                def set(self):
                    self.done = True
                def is_set(self):
                    return self.done
                def wait(self, timeout):
                    f.bridge.stop()  # Completion arrives just after wait decided to time out.
                    return False

            conn = Connection({"id": 44, "type": "capture_view", "params": {}})
            with patch.object(f.bridge, "_admit", side_effect=admit), patch.object(f.bridge.threading, "Event", RaceEvent):
                f.bridge._client(conn, f.bridge._server["generation"])
            self.assert_stopped(captured[0], False)
            self.assertIn("did not run the command in time", conn.sent[0]["message"])
            self.assertEqual(captured[0]["reply"]["code"], "BRIDGE_STOPPED")

    def test_stopped_dispatched_request_id_replays_without_repeating_mutation(self):
        with Fixture() as f:
            effects = []

            def mutate(p):
                effects.append("changed")
                yield
                effects.append("resumed")

            f.bridge.register("test.once", mutate)
            _, active, _ = f.enqueue("test.once", {"request_id": "stopped-active"})
            f.bridge.pump()
            f.bridge.stop()
            self.assert_stopped(active, True)
            f.start()
            _, replay, _ = f.enqueue("test.once", {"request_id": "stopped-active"}, 45)
            f.bridge.pump()
            self.assertTrue(replay["done"].is_set())
            self.assertEqual(replay["reply"]["id"], 45)
            self.assertTrue(replay["reply"]["replayed"])
            self.assertEqual(replay["reply"]["code"], "BRIDGE_STOPPED")
            self.assertEqual(effects, ["changed"])

    def test_undispatched_request_id_can_retry_after_restart(self):
        with Fixture() as f:
            effects = []
            f.bridge.register("test.once", lambda p: effects.append(1) or "done")
            _, queued, _ = f.enqueue("test.once", {"request_id": "queued"})
            f.bridge.stop()
            self.assert_stopped(queued, False)
            f.start()
            _, retry, _ = f.enqueue("test.once", {"request_id": "queued"}, 46)
            f.bridge.pump()
            self.assertEqual(retry["reply"]["result"], "done")
            self.assertEqual(effects, [1])

    def test_batch_explicitly_closes_externally_retained_child_before_transaction_end(self):
        with Fixture() as f:
            children = []
            events = []

            def child(p):
                try:
                    yield
                finally:
                    events.append("child cleanup")
                    self.assertNotIn("transaction end", f.unreal.CALLS)

            def hold_child(p):
                gen = child(p)
                children.append(gen)  # Prevent CPython reference counting from masking a missing close.
                return gen

            f.bridge.register("test.child", hold_child)
            _, batch, _ = f.enqueue("batch", {"commands": [{"type": "test.child"}], "transaction": "lifecycle"})
            f.bridge.pump()
            f.bridge.stop()
            self.assert_stopped(batch, True)
            self.assertEqual(events, ["child cleanup"])
            self.assertEqual(f.unreal.CALLS, ["transaction begin lifecycle", "transaction end"])
            children[0].close()
            self.assertEqual(events, ["child cleanup"])

    def test_callback_registration_failure_closes_listener_and_allows_later_start(self):
        with Fixture() as f:
            f.bridge.stop()
            f.unreal.register_slate_post_tick_callback.side_effect = ValueError("callback boom")
            with self.assertRaisesRegex(ValueError, "callback boom"):
                f.start()
            self.assertEqual(f.listeners[-1].closed, 1)
            self.assertIsNone(f.bridge._server["sock"])
            self.assertIsNone(f.bridge._server["owner"])
            self.assertFalse(f.bridge._server["stopping"])
            f.unreal.register_slate_post_tick_callback.side_effect = None
            f.start()

    def test_thread_start_failure_closes_listener_and_allows_later_start(self):
        with Fixture() as f:
            f.bridge.stop()
            registered = f.unreal.register_slate_post_tick_callback.call_count
            with patch.object(DormantThread, "start", side_effect=RuntimeError("thread boom")):
                with self.assertRaisesRegex(RuntimeError, "thread boom"):
                    f.start()
            self.assertEqual(f.listeners[-1].closed, 1)
            self.assertIsNone(f.bridge._server["sock"])
            self.assertIsNone(f.bridge._server["tick"])
            self.assertIsNone(f.bridge._server["owner"])
            self.assertFalse(f.bridge._server["stopping"])
            self.assertEqual(f.unreal.register_slate_post_tick_callback.call_count, registered)
            self.assertEqual(f.start(), 9877)

    def test_control_interrupt_is_reraised_only_after_all_jobs_are_settled(self):
        with Fixture() as f:
            cleaned, mutations = [], []

            def exit_cleanup(p):
                try:
                    yield
                finally:
                    cleaned.append("exit")
                    raise SystemExit("control-exit")

            def keyboard_cleanup(p):
                try:
                    yield
                finally:
                    cleaned.append("keyboard")
                    raise KeyboardInterrupt("second-interrupt")

            def healthy(p):
                try:
                    yield
                finally:
                    cleaned.append("healthy")

            f.bridge.register("test.exit", exit_cleanup)
            f.bridge.register("test.keyboard", keyboard_cleanup)
            f.bridge.register("test.healthy", healthy)
            f.bridge.register("test.pending", lambda p: mutations.append(1))
            _, first, _ = f.enqueue("test.exit")
            _, second, _ = f.enqueue("test.keyboard")
            _, good, _ = f.enqueue("test.healthy")
            f.bridge.pump()
            _, pending, _ = f.enqueue("test.pending")
            with self.assertRaises(SystemExit) as raised:
                f.bridge.stop()
            self.assertEqual(raised.exception.code, "control-exit", "the first control interrupt is preserved")
            for box in (first, second, good):
                self.assert_stopped(box, True)
            self.assertIn("SystemExit: control-exit", first["reply"]["cleanup_error"])
            self.assertIn("KeyboardInterrupt: second-interrupt", second["reply"]["cleanup_error"])
            self.assertNotIn("cleanup_error", good["reply"])
            self.assert_stopped(pending, False)
            self.assertEqual(cleaned, ["exit", "keyboard", "healthy"])
            self.assertEqual(mutations, [])
            self.assertEqual(f.bridge._running, [])
            self.assertTrue(f.bridge._jobs.empty())
            self.assertIsNone(f.bridge._server["owner"])
            self.assertFalse(f.bridge._server["stopping"])
            f.bridge.stop()
            self.assertEqual(cleaned, ["exit", "keyboard", "healthy"])
            f.start()

    def test_shutdown_handle_failures_settle_jobs_block_restart_and_recover_on_retry(self):
        for handle in ("tick", "sock"):
            with self.subTest(handle=handle), Fixture() as f:
                mutations = []
                f.bridge.register("test.pending", lambda p: mutations.append(1))
                _, active, _ = f.capture()
                _, pending, _ = f.enqueue("test.pending")
                listener = f.listeners[0]
                if handle == "tick":
                    failing = f.unreal.unregister_slate_post_tick_callback
                    exception = ValueError("unregister boom")
                else:
                    failing = Mock(side_effect=OSError("close boom"))
                    exception = OSError("close boom")
                failure_context = (contextlib.nullcontext() if handle == "tick" else
                                   patch.object(listener, "close", failing))
                with failure_context:
                    if handle == "tick":
                        failing.side_effect = exception
                    with self.assertRaisesRegex(type(exception), str(exception)):
                        f.bridge.stop()
                    self.assert_stopped(active, True)
                    self.assert_stopped(pending, False)
                    self.assertEqual(f.captures(), [])
                    self.assertEqual(mutations, [])
                    self.assertEqual(f.bridge._running, [])
                    self.assertTrue(f.bridge._jobs.empty())
                    if handle == "tick":
                        self.assertEqual(f.bridge._server[handle], "test-tick")
                    else:
                        self.assertIs(f.bridge._server[handle], listener)
                    self.assertEqual(f.bridge._server["owner"], f.owner)
                    self.assertFalse(f.bridge._server["stopping"])
                    with self.assertRaisesRegex(RuntimeError, "retry stop"):
                        f.start()
                    replies = (dict(active["reply"]), dict(pending["reply"]))
                if handle == "tick":
                    failing.side_effect = None
                f.bridge.stop()
                self.assertIsNone(f.bridge._server["sock"])
                self.assertIsNone(f.bridge._server["tick"])
                self.assertIsNone(f.bridge._server["owner"])
                self.assertEqual((active["reply"], pending["reply"]), replies)
                self.assertEqual(f.unreal.CALLS.count("destroy SceneCapture2D"), 1)
                self.assertEqual(listener.closed, 1)
                f.bridge.stop()
                self.assertEqual(listener.closed, 1)
                self.assertEqual(f.start(), 9877)

    def test_mutant_skipping_generator_close_fails_actual_capture_cleanup(self):
        mutant = SOURCE.replace("                gen.close()", "                pass  # mutant: no close", 1)
        self.assertNotEqual(mutant, SOURCE)
        with Fixture(mutant) as f:
            f.capture()
            retained = f.bridge._running[0][0]
            f.bridge.stop()
            with self.assertRaises(AssertionError):
                self.assertEqual(f.captures(), [])
            retained.close()

    def test_mutant_without_listener_generation_fence_fails_stale_admission(self):
        mutant = SOURCE.replace('generation is not _server["generation"]', "False", 1)
        self.assertNotEqual(mutant, SOURCE)
        with Fixture(mutant) as f:
            old = f.bridge._server["generation"]
            f.bridge.stop()
            f.start()
            conn = Connection({"id": 47, "type": "capture_view", "params": {"async": True}})
            f.bridge._client(conn, old)
            with self.assertRaises(AssertionError):
                self.assertEqual(conn.sent[0].get("code"), "BRIDGE_STOPPED")


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LifecycleTests))
    print("%d/%d" % (result.testsRun - len(result.failures) - len(result.errors), result.testsRun))
    raise SystemExit(0 if result.wasSuccessful() else 1)
