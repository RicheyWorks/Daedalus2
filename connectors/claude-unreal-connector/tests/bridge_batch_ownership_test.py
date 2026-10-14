# SPDX-License-Identifier: MIT
"""Actual bridge scheduling, fake Unreal: no editor, sockets, workers or exports.

These witnesses cover cooperating bridge-owned batch transactions. A recorded fake
transaction is not proof of Unreal undo-buffer behavior or external/native isolation.
Run: python connectors/claude-unreal-connector/tests/bridge_batch_ownership_test.py
"""
import unittest
from unittest.mock import patch

from bridge_lifecycle_test import Connection, Fixture, SOURCE


def transaction_probe(fixture, close_error=None, enter_error=None):
    """Observe context ownership without depending on production owner fields."""
    active, events = [], []
    original = fixture.unreal.ScopedEditorTransaction

    class RecordedTransaction(original):
        def __enter__(self):
            result = super().__enter__()
            active.append(self.description)
            events.append(("begin", self.description))
            if enter_error is not None:
                raise enter_error
            return result

        def __exit__(self, *exc):
            if close_error is not None:
                events.append(("close failed", self.description))
                raise close_error
            try:
                return super().__exit__(*exc)
            finally:
                if not active or active[-1] != self.description:
                    raise AssertionError("fake transaction contexts unwound out of order")
                active.pop()
                events.append(("end", self.description))

    fixture.unreal.ScopedEditorTransaction = RecordedTransaction
    return active, events


def batch(command="test.hold", transaction="A", params=None, **options):
    return dict({"transaction": transaction,
                 "commands": [{"type": command, "params": params or {}}]}, **options)


def install_commands(fixture, active, calls):
    def record(kind, params):
        item = (kind, params.get("caller", "?"), tuple(active))
        calls.append(item)
        return item

    def hold(params):
        record("entered", params)
        yield
        record("resumed", params)
        yield
        return {"finished": True}

    fixture.bridge.register("test.hold", hold)
    fixture.bridge.register("test.mutate", lambda p: record("mutation", p))
    fixture.bridge.register("test.read", lambda p: record("observation", p), risk="READ")


class BatchOwnershipTests(unittest.TestCase):
    def assert_busy(self, box):
        self.assertTrue(box["done"].is_set(), "accepted request must receive a terminal reply")
        self.assertEqual(box["reply"]["status"], "error")
        self.assertEqual(box["reply"]["code"], "BUSY")
        self.assertIs(box["reply"]["dispatched"], False)
        self.assertEqual(box["reply"]["effects"], "none")

    def assert_interrupted(self, box):
        self.assertTrue(box["done"].is_set(), "control interrupt must settle the accepted caller")
        self.assertEqual(box["reply"]["status"], "error")
        self.assertEqual(box["reply"]["code"], "COMMAND_INTERRUPTED")
        self.assertIs(box["reply"]["dispatched"], True)
        self.assertEqual(box["reply"]["effects"], "unknown")
        self.assertIs(box["reply"]["retryable"], False)

    def finish(self, fixture, box, ticks=8):
        for _ in range(ticks):
            if box["done"].is_set():
                break
            fixture.bridge.pump()
        self.assertTrue(box["done"].is_set(), "bounded fake generator must finish")
        return box["reply"]

    def test_yielding_batch_refuses_foreign_mutation_before_function_runs(self):
        with Fixture() as f:
            active, events = transaction_probe(f)
            calls = []
            install_commands(f, active, calls)
            _, owner, _ = f.enqueue("batch", batch(params={"caller": "A"}), request_id=101)
            _, foreign, _ = f.enqueue("test.mutate", {"caller": "B"}, request_id=202)
            f.bridge.pump()
            self.assert_busy(foreign)
            self.assertEqual(calls, [("entered", "A", ("A",))])
            self.assertFalse(owner["done"].is_set())
            self.assertEqual(active, ["A"])
            self.assertTrue(self.finish(f, owner)["result"]["ok"])
            self.assertEqual(active, [])
            self.assertEqual(events, [("begin", "A"), ("end", "A")])

    def test_actual_sensitive_read_capture_cannot_spawn_inside_foreign_batch(self):
        with Fixture() as f:
            active, _ = transaction_probe(f)
            install_commands(f, active, [])
            f.enqueue("batch", batch(), request_id=101)
            _, capture, _ = f.enqueue("capture_view", {"async": True}, request_id=202)
            # Prove zero actual capture calls; no fake image is written by this test.
            with patch.object(f.unreal.RenderingLibrary, "export_render_target",
                              side_effect=AssertionError("no export is allowed")):
                f.bridge.pump()
                self.assert_busy(capture)
                self.assertEqual(f.captures(), [])
                self.assertNotIn("spawn SceneCapture2D", f.unreal.CALLS)
                self.assertNotIn("capture_scene", f.unreal.CALLS)

    def test_prior_non_read_generator_prevents_batch_opening_its_transaction(self):
        for risk in ("MUTATE", "DESTRUCTIVE", "SENSITIVE_READ"):
            with self.subTest(risk=risk), Fixture() as f:
                active, events = transaction_probe(f)
                calls = []
                install_commands(f, active, calls)

                def prior(p):
                    calls.append(("prior first", tuple(active)))
                    yield
                    calls.append(("prior last", tuple(active)))

                f.bridge.register("test.prior", prior, risk=risk)
                _, earlier, _ = f.enqueue("test.prior", request_id=101)
                _, candidate, _ = f.enqueue("batch", batch(), request_id=202)
                f.bridge.pump()
                self.assert_busy(candidate)
                self.assertFalse(earlier["done"].is_set())
                self.assertEqual(events, [], "refused batch must not open an undo context")
                self.finish(f, earlier)
                self.assertEqual(calls, [("prior first", ()), ("prior last", ())])
                _, retry, _ = f.enqueue("batch", batch(), request_id=303)
                self.assertTrue(self.finish(f, retry)["result"]["ok"])

    def test_nonyielding_batch_releases_before_next_mutation_in_same_pump(self):
        with Fixture() as f:
            active, events = transaction_probe(f)
            calls = []
            install_commands(f, active, calls)
            _, owner, _ = f.enqueue("batch", batch("test.mutate", params={"caller": "A"}))
            _, later, _ = f.enqueue("test.mutate", {"caller": "B"}, request_id=2)
            f.bridge.pump()
            self.assertTrue(owner["reply"]["result"]["ok"])
            self.assertEqual(later["reply"]["status"], "ok")
            self.assertEqual(calls, [("mutation", "A", ("A",)), ("mutation", "B", ())])
            self.assertEqual(events, [("begin", "A"), ("end", "A")])

    def test_read_observation_remains_available_during_yielding_batch(self):
        with Fixture() as f:
            active, _ = transaction_probe(f)
            calls = []
            install_commands(f, active, calls)
            _, owner, _ = f.enqueue("batch", batch(), request_id=101)
            _, read, _ = f.enqueue("test.read", {"caller": "R"}, request_id=202)
            f.bridge.pump()
            self.assertFalse(owner["done"].is_set())
            self.assertEqual(read["reply"]["status"], "ok")
            self.assertIn(("observation", "R", ("A",)), calls)

    def test_prior_read_generator_does_not_block_batch(self):
        with Fixture() as f:
            active, events = transaction_probe(f)
            install_commands(f, active, [])

            def read(p):
                yield
                return False

            f.bridge.register("test.read_generator", read, risk="READ")
            _, observation, _ = f.enqueue("test.read_generator", request_id=101)
            _, owner, _ = f.enqueue("batch", batch(), request_id=202)
            f.bridge.pump()
            self.assertEqual(events, [("begin", "A")])
            self.assertFalse(owner["done"].is_set())
            self.assertEqual(self.finish(f, observation)["result"], False)
            self.assertTrue(self.finish(f, owner)["result"]["ok"])

    def test_socket_side_job_result_keeps_accepted_busy_identity(self):
        with Fixture() as f:
            active, _ = transaction_probe(f)
            install_commands(f, active, [])
            _, owner, owner_id = f.enqueue("batch", batch(**{"async": True}), request_id=101)
            _, denied, denied_id = f.enqueue("test.mutate", {"async": True}, request_id=202)
            f.bridge.pump()
            self.assert_busy(denied)
            for identifier, state, reply in ((owner_id, "running", None),
                                              (denied_id, "done", denied["reply"])):
                connection = Connection({"id": 303, "type": "job_result",
                                         "params": {"job_id": identifier}})
                f.bridge._client(connection, f.bridge._server["generation"])
                result = connection.sent[0]["result"]
                self.assertEqual(result["job_id"], identifier)
                self.assertEqual(result["state"], state)
                if reply is not None:
                    self.assertEqual(result["reply"], reply)
            self.assertFalse(owner["done"].is_set())

    def test_cached_terminal_replay_does_not_execute_mutation_during_batch(self):
        with Fixture() as f:
            active, _ = transaction_probe(f)
            calls = []
            install_commands(f, active, calls)
            executions = []
            f.bridge.register("test.once", lambda p: executions.append(tuple(active)) or False)
            _, first, _ = f.enqueue("test.once", {"request_id": "completed-1"})
            f.bridge.pump()
            self.assertEqual(first["reply"]["result"], False)
            _, owner, _ = f.enqueue("batch", batch(), request_id=101)
            _, replay, _ = f.enqueue("test.once", {"request_id": "completed-1"}, request_id=202)
            f.bridge.pump()
            self.assertEqual(replay["reply"]["status"], "ok")
            self.assertIs(replay["reply"]["replayed"], True)
            self.assertEqual(replay["reply"]["id"], 202)
            self.assertIs(replay["reply"]["result"], False)
            self.assertEqual(executions, [()])
            self.assertFalse(owner["done"].is_set())

    def test_two_yielding_batches_never_open_overlapping_transaction_scopes(self):
        with Fixture() as f:
            active, events = transaction_probe(f)
            install_commands(f, active, [])
            _, first, _ = f.enqueue("batch", batch(transaction="A"), request_id=101)
            _, second, _ = f.enqueue("batch", batch(transaction="B"), request_id=202)
            f.bridge.pump()
            self.assert_busy(second)
            self.assertEqual(events, [("begin", "A")])
            self.finish(f, first)
            _, retried, _ = f.enqueue("batch", batch(transaction="B"), request_id=303)
            self.assertTrue(self.finish(f, retried)["result"]["ok"])
            self.assertEqual(events, [("begin", "A"), ("end", "A"),
                                      ("begin", "B"), ("end", "B")])

    def test_busy_is_not_cached_as_success_and_explicit_retry_can_run_after_release(self):
        with Fixture() as f:
            active, _ = transaction_probe(f)
            calls = []
            install_commands(f, active, calls)
            _, owner, _ = f.enqueue("batch", batch(), request_id=101)
            params = {"caller": "B", "request_id": "known-not-dispatched"}
            _, refused, _ = f.enqueue("test.mutate", params, request_id=202)
            f.bridge.pump()
            self.assert_busy(refused)
            self.finish(f, owner)
            _, retry, _ = f.enqueue("test.mutate", params, request_id=303)
            f.bridge.pump()
            self.assertEqual(retry["reply"]["status"], "ok")
            self.assertFalse(retry["reply"].get("replayed", False))
            self.assertEqual([item for item in calls if item[0] == "mutation"],
                             [("mutation", "B", ())])

    def test_invalid_batch_releases_reservation_without_opening_transaction(self):
        with Fixture() as f:
            active, events = transaction_probe(f)
            calls = []
            install_commands(f, active, calls)
            _, invalid, _ = f.enqueue("batch", {"commands": []}, request_id=101)
            _, next_command, _ = f.enqueue("test.mutate", {"caller": "B"}, request_id=202)
            f.bridge.pump()
            self.assertEqual(invalid["reply"]["status"], "error")
            self.assertIn("batch needs commands", invalid["reply"]["message"])
            self.assertEqual(next_command["reply"]["status"], "ok")
            self.assertEqual(events, [])
            self.assertEqual(calls, [("mutation", "B", ())])

    def test_unknown_and_policy_refusal_keep_their_existing_outcomes(self):
        with Fixture() as f:
            active, _ = transaction_probe(f)
            calls = []
            install_commands(f, active, calls)
            f.enqueue("batch", batch(), request_id=101)
            f.bridge.pump()
            f.bridge.register("test.dangerous", lambda p: calls.append("forbidden"), risk="DESTRUCTIVE")
            f.bridge.set_policy(("READ", "SENSITIVE_READ", "MUTATE"))
            _, unknown, _ = f.enqueue("test.missing", request_id=202)
            _, refused, _ = f.enqueue("test.dangerous", request_id=303)
            f.bridge.pump()
            self.assertEqual(unknown["reply"]["code"], "UNKNOWN")
            self.assertEqual(refused["reply"]["code"], "REFUSED")
            self.assertNotIn("forbidden", calls)

    def test_child_advancement_failure_stops_keep_going_and_gates_later_mutation(self):
        for keep in (False, True):
            with self.subTest(keep_going=keep), Fixture() as f:
                active, events = transaction_probe(f)
                calls = []
                install_commands(f, active, calls)

                def failing(p):
                    calls.append(("failure entered", tuple(active)))
                    try:
                        yield
                        raise ValueError("child failure")
                    finally:
                        calls.append(("failure cleanup", tuple(active)))

                f.bridge.register("test.failure", failing)
                params = {"transaction": "A", "keep_going": keep, "commands": [
                    {"type": "test.failure"},
                    {"type": "test.mutate", "params": {"caller": "A-later"}}]}
                _, owner, _ = f.enqueue("batch", params, request_id=101)
                f.bridge.pump()
                _, later, _ = f.enqueue("test.mutate", {"caller": "B"}, request_id=202)
                f.bridge.pump()
                self.assertTrue(owner["done"].is_set())
                self.assertEqual(owner["reply"]["status"], "error")
                self.assertIn("child failure", owner["reply"]["message"])
                self.assert_busy(later)
                self.assertIn(("failure cleanup", ("A",)), calls)
                self.assertFalse(any(item[0] == "mutation" for item in calls))
                self.assertEqual(active, [])
                self.assertEqual(events, [("begin", "A"), ("end", "A")])

    def test_synchronous_batch_item_failure_preserves_keep_going_and_healthy_release(self):
        for keep in (False, True):
            with self.subTest(keep_going=keep), Fixture() as f:
                active, events = transaction_probe(f)
                calls = []
                install_commands(f, active, calls)

                def failing(p):
                    calls.append(("synchronous failure", tuple(active)))
                    raise ValueError("synchronous child failure")

                f.bridge.register("test.sync_failure", failing)
                params = {"transaction": "A", "keep_going": keep, "commands": [
                    {"type": "test.sync_failure"},
                    {"type": "test.mutate", "params": {"caller": "A-later"}}]}
                _, owner, _ = f.enqueue("batch", params, request_id=101)
                _, later, _ = f.enqueue("test.mutate", {"caller": "B"}, request_id=202)
                f.bridge.pump()
                self.assertEqual(owner["reply"]["status"], "ok")
                self.assertFalse(owner["reply"]["result"]["ok"])
                self.assertEqual(owner["reply"]["result"]["results"][0]["status"], "error")
                self.assertIn("synchronous child failure", owner["reply"]["result"]["results"][0]["message"])
                self.assertEqual(later["reply"]["status"], "ok")
                self.assertIn(("mutation", "B", ()), calls)
                self.assertEqual(("mutation", "A-later", ("A",)) in calls, keep)
                self.assertEqual(active, [])
                self.assertEqual(events, [("begin", "A"), ("end", "A")])

    def capture_natural_cleanup_case(self, source=SOURCE, expect_barrier=True):
        with Fixture(source) as f:
            active, events = transaction_probe(f)
            calls, destruction = [], []
            install_commands(f, active, calls)

            def failed_destroy(subsystem, actor):
                f.unreal._game_thread_only("destroy_actor")
                destruction.append((actor, tuple(active)))
                raise ValueError("capture natural cleanup failed")

            # Exercise the real built-in generator while keeping image handling entirely in memory.
            export = f.stack.enter_context(patch.object(f.unreal.RenderingLibrary, "export_render_target"))
            png = f.stack.enter_context(patch.object(f.bridge, "_png_b64", return_value=("memory-png", 1)))
            f.stack.enter_context(patch.object(f.bridge.os.path, "exists", return_value=True))
            f.stack.enter_context(patch.object(f.bridge.os.path, "getsize", return_value=1))
            f.stack.enter_context(patch.object(f.unreal.EditorActorSubsystem, "destroy_actor", failed_destroy))
            params = {"transaction": "A", "keep_going": True, "commands": [
                {"type": "capture_view"},
                {"type": "test.mutate", "params": {"caller": "must-not-run"}}]}
            _, owner, _ = f.enqueue("batch", params, request_id=101)
            f.bridge.pump()
            capture = f.captures()[0]
            self.assertFalse(owner["done"].is_set())
            self.assertEqual(destruction, [])
            export.assert_not_called()
            png.assert_not_called()
            f.bridge.pump()
            self.assertTrue(owner["done"].is_set())
            if expect_barrier:
                self.assertEqual(owner["reply"]["status"], "error")
                self.assertIn("capture natural cleanup failed", owner["reply"]["message"])
                self.assertEqual(calls, [])
            else:
                self.assertEqual(owner["reply"]["status"], "ok")
                self.assertFalse(owner["reply"]["result"]["ok"])
                self.assertIn("capture natural cleanup failed", owner["reply"]["result"]["results"][0]["message"])
                self.assertEqual(calls, [("mutation", "must-not-run", ("A",))])
            self.assertEqual(destruction, [(capture, ("A",))])
            self.assertEqual(f.captures(), [capture], "failed destruction leaves the fake actor present")
            export.assert_called_once()
            png.assert_called_once()
            self.assertEqual(active, [])
            self.assertEqual(events, [("begin", "A"), ("end", "A")])
            terminal = dict(owner["reply"])
            if not expect_barrier:
                # Prior candidate witness: a real cleanup failure was followed by another child mutation.
                return

            for restart in (False, True):
                if restart:
                    f.bridge.stop()
                    f.start()
                _, mutation, _ = f.enqueue("test.mutate", {"caller": "must-not-run"}, request_id=202)
                _, candidate, _ = f.enqueue("batch", batch(transaction="B"), request_id=303)
                _, read, _ = f.enqueue("test.read", {"caller": "R"}, request_id=404)
                f.bridge.pump()
                self.assert_busy(mutation)
                self.assert_busy(candidate)
                self.assertEqual(read["reply"]["status"], "ok")
                self.assertEqual(owner["reply"], terminal)
            self.assertFalse(any(item[0] == "mutation" for item in calls))
            self.assertEqual(destruction, [(capture, ("A",))])
            self.assertEqual(f.captures(), [capture])

    def test_actual_capture_natural_destroy_failure_stops_keep_going_and_latches_unknown(self):
        self.capture_natural_cleanup_case()

    def test_mutant_without_child_advancement_guard_reproduces_capture_cleanup_failure(self):
        guard = ('                            except BaseException:\n'
                 '                                # next() also runs generator finalizers; a later close() may be a no-op.\n'
                 '                                _batch_scope["unknown"] = "batch child advancement failed; cleanup state is unknown"\n'
                 '                                raise\n')
        self.assertEqual(SOURCE.count(guard), 1, "mutation must remove only the child advancement guard")
        self.capture_natural_cleanup_case(SOURCE.replace(guard, "", 1), expect_barrier=False)

    def test_natural_generator_cleanup_failure_latches_for_exception_and_control_interrupts(self):
        for error_type in (ValueError, KeyboardInterrupt, SystemExit):
            with self.subTest(failure=error_type.__name__), Fixture() as f:
                active, events = transaction_probe(f)
                calls, cleanups = [], []
                install_commands(f, active, calls)

                def child(p):
                    try:
                        yield
                        return False
                    finally:
                        cleanups.append(tuple(active))
                        raise error_type("natural child cleanup failed")

                f.bridge.register("test.natural_cleanup", child)
                params = {"transaction": "A", "keep_going": True, "commands": [
                    {"type": "test.natural_cleanup"},
                    {"type": "test.mutate", "params": {"caller": "must-not-run"}}]}
                _, owner, _ = f.enqueue("batch", params, request_id=101)
                f.bridge.pump()
                if error_type is ValueError:
                    f.bridge.pump()
                else:
                    with self.assertRaises(error_type):
                        f.bridge.pump()
                    self.assert_interrupted(owner)
                self.assertTrue(owner["done"].is_set())
                self.assertEqual(owner["reply"]["status"], "error")
                self.assertIn("natural child cleanup failed", owner["reply"]["message"])
                self.assertEqual(cleanups, [("A",)])
                self.assertEqual(calls, [])
                self.assertEqual(active, [])
                self.assertEqual(events, [("begin", "A"), ("end", "A")])
                terminal = dict(owner["reply"])
                f.bridge.pump()
                self.assertEqual(owner["reply"], terminal)
                f.bridge.stop()
                f.start()
                _, mutation, _ = f.enqueue("test.mutate", request_id=202)
                _, read, _ = f.enqueue("test.read", request_id=303)
                f.bridge.pump()
                self.assert_busy(mutation)
                self.assertEqual(read["reply"]["status"], "ok")
                self.assertEqual(cleanups, [("A",)])
                self.assertFalse(any(item[0] == "mutation" for item in calls))

    def test_nested_pump_does_not_execute_foreign_command_or_reenter_batch(self):
        with Fixture() as f:
            active, events = transaction_probe(f)
            calls = []
            install_commands(f, active, calls)

            def nested(p):
                calls.append(("nested first", tuple(active)))
                f.bridge.pump()
                yield
                calls.append(("nested last", tuple(active)))
                f.bridge.pump()

            f.bridge.register("test.nested", nested)
            _, owner, _ = f.enqueue("batch", batch("test.nested"), request_id=101)
            _, foreign, _ = f.enqueue("test.mutate", {"caller": "B"}, request_id=202)
            f.bridge.pump()
            self.assert_busy(foreign)
            self.assertEqual(calls, [("nested first", ("A",))])
            self.assertTrue(self.finish(f, owner)["result"]["ok"])
            self.assertEqual(calls, [("nested first", ("A",)), ("nested last", ("A",))])
            self.assertEqual(events, [("begin", "A"), ("end", "A")])

    def test_self_stop_closes_child_inside_owner_then_settles_queue_and_restart(self):
        with Fixture() as f:
            active, events = transaction_probe(f)
            calls = []
            install_commands(f, active, calls)

            def child(p):
                try:
                    calls.append(("child entered", tuple(active)))
                    f.bridge.stop()
                    calls.append(("stop returned", tuple(active)))
                    yield
                    calls.append("must not resume")
                finally:
                    calls.append(("child cleanup", tuple(active)))

            f.bridge.register("test.self_stop", child)
            _, owner, _ = f.enqueue("batch", batch("test.self_stop"), request_id=101)
            _, pending, _ = f.enqueue("test.mutate", {"caller": "B"}, request_id=202)
            f.bridge.pump()
            self.assertEqual(owner["reply"]["code"], "BRIDGE_STOPPED")
            self.assertIs(owner["reply"]["dispatched"], True)
            self.assertEqual(pending["reply"]["code"], "BRIDGE_STOPPED")
            self.assertIs(pending["reply"]["dispatched"], False)
            self.assertEqual(calls, [("child entered", ("A",)), ("stop returned", ("A",)),
                                     ("child cleanup", ("A",))])
            self.assertEqual(active, [])
            self.assertEqual(events, [("begin", "A"), ("end", "A")])
            f.start()
            _, next_batch, _ = f.enqueue("batch", batch("test.mutate"), request_id=303)
            self.assertTrue(self.finish(f, next_batch)["result"]["ok"])

    def test_failed_transaction_close_latches_unknown_and_refuses_next_batch(self):
        with Fixture() as f:
            active, events = transaction_probe(f, close_error=ValueError("undo context close failed"))
            calls = []
            install_commands(f, active, calls)
            _, failed, _ = f.enqueue("batch", batch("test.mutate"), request_id=101)
            f.bridge.pump()
            self.assertTrue(failed["done"].is_set())
            self.assertEqual(failed["reply"]["status"], "error")
            self.assertIn("undo context close failed", failed["reply"]["message"])
            _, next_batch, _ = f.enqueue("batch", batch(transaction="B"), request_id=202)
            _, mutation, _ = f.enqueue("test.mutate", request_id=303)
            f.bridge.pump()
            self.assert_busy(next_batch)
            self.assert_busy(mutation)
            self.assertEqual(events, [("begin", "A"), ("close failed", "A")])
            self.assertEqual(calls, [("mutation", "?", ("A",))])
            f.bridge.stop()
            f.start()
            _, after_restart, _ = f.enqueue("test.mutate", request_id=404)
            f.bridge.pump()
            self.assert_busy(after_restart)

    def test_failed_transaction_enter_blocks_mutation_without_running_children(self):
        with Fixture() as f:
            active, events = transaction_probe(f, enter_error=ValueError("undo context enter failed"))
            calls = []
            install_commands(f, active, calls)
            _, failed, _ = f.enqueue("batch", batch("test.mutate"), request_id=101)
            f.bridge.pump()
            self.assertEqual(failed["reply"]["status"], "error")
            self.assertIn("undo context enter failed", failed["reply"]["message"])
            _, mutation, _ = f.enqueue("test.mutate", request_id=202)
            _, read, _ = f.enqueue("test.read", {"caller": "R"}, request_id=303)
            f.bridge.pump()
            self.assert_busy(mutation)
            self.assertEqual(read["reply"]["status"], "ok")
            self.assertEqual(events, [("begin", "A")])
            self.assertEqual(calls, [("observation", "R", ("A",))])

    def test_child_close_failure_during_stop_keeps_unknown_barrier_after_restart(self):
        with Fixture() as f:
            active, events = transaction_probe(f)
            install_commands(f, active, [])
            cleanups = []

            def child(p):
                try:
                    yield
                    yield
                finally:
                    cleanups.append(tuple(active))
                    raise ValueError("child finalizer failed")

            f.bridge.register("test.bad_close", child)
            _, owner, _ = f.enqueue("batch", batch("test.bad_close"), request_id=101)
            f.bridge.pump()
            f.bridge.stop()
            self.assertEqual(owner["reply"]["code"], "BRIDGE_STOPPED")
            self.assertIn("child finalizer failed", owner["reply"]["cleanup_error"])
            self.assertEqual(cleanups, [("A",)])
            f.start()
            _, attempted, _ = f.enqueue("batch", batch(transaction="B"), request_id=202)
            _, mutation, _ = f.enqueue("test.mutate", request_id=303)
            f.bridge.pump()
            self.assert_busy(attempted)
            self.assert_busy(mutation)
            self.assertEqual(events, [("begin", "A"), ("end", "A")])

    def test_keep_going_does_not_run_later_mutation_after_child_close_failure(self):
        with Fixture() as f:
            active, _ = transaction_probe(f)
            calls = []
            install_commands(f, active, calls)

            def child(p):
                try:
                    calls.append(("child entered", tuple(active)))
                    yield
                finally:
                    calls.append(("child cleanup", tuple(active)))
                    raise ValueError("child finalizer failed")

            f.bridge.register("test.bad_close", child)
            params = {"transaction": "A", "keep_going": True, "commands": [
                {"type": "test.bad_close"},
                {"type": "test.mutate", "params": {"caller": "must-not-run"}}]}
            _, owner, _ = f.enqueue("batch", params, request_id=101)
            f.bridge.pump()
            f.bridge.stop()
            self.assertEqual(owner["reply"]["code"], "BRIDGE_STOPPED")
            self.assertIn("child finalizer failed", owner["reply"]["cleanup_error"])
            self.assertEqual(calls, [("child entered", ("A",)), ("child cleanup", ("A",))])
            f.start()
            _, later, _ = f.enqueue("test.mutate", request_id=202)
            f.bridge.pump()
            self.assert_busy(later)

    def interrupted_command_case(self, error_type, phase):
        """Exercise actual scheduling and replay after an effect precedes an interrupt."""
        with Fixture() as f:
            active, events = transaction_probe(f)
            calls = []
            install_commands(f, active, calls)
            executions, cleanups = [], []

            if phase == "synchronous":
                def interrupted(p):
                    try:
                        executions.append(tuple(active))
                        raise error_type("command interrupt witness")
                    finally:
                        cleanups.append(tuple(active))

                command = "test.interrupt"
                params = {"request_id": "interrupt-" + phase, "async": True}
            else:
                def interrupted(p):
                    try:
                        if phase == "resumed":
                            yield
                        executions.append(tuple(active))
                        raise error_type("command interrupt witness")
                        yield  # Initial case is a generator even before its first yield.
                    finally:
                        cleanups.append(tuple(active))

                command = "batch"
                params = {"request_id": "interrupt-" + phase, "async": True, "transaction": "A",
                          "keep_going": True, "commands": [
                              {"type": "test.interrupt"},
                              {"type": "test.mutate", "params": {"caller": "must-not-run"}}]}

            f.bridge.register("test.interrupt", interrupted)
            _, owner, job_id = f.enqueue(command, params, request_id=101)
            if phase == "resumed":
                f.bridge.pump()
                self.assertFalse(owner["done"].is_set())
                self.assertEqual(active, ["A"])
                self.assertEqual(executions, [])
            with self.assertRaises(error_type):
                f.bridge.pump()
            self.assert_interrupted(owner)
            self.assertEqual(owner["reply"]["id"], 101)
            expected_scope = () if phase == "synchronous" else ("A",)
            self.assertEqual(executions, [expected_scope])
            self.assertEqual(cleanups, [expected_scope])
            self.assertEqual(active, [], "the interrupted transaction must have unwound")
            self.assertEqual(calls, [], "keep_going must not consume a control interrupt")
            terminal = dict(owner["reply"])

            # A closed generator must not become a successful None result next tick.
            f.bridge.pump()
            self.assertEqual(owner["reply"], terminal)
            polled = f.bridge._job_result({"id": 909}, {"job_id": job_id})
            self.assertEqual(polled["result"]["state"], "done")
            self.assertEqual(polled["result"]["reply"], terminal)

            # Exact request-ID replay returns the terminal failure without another effect.
            _, replay, _ = f.enqueue(command, params, request_id=202)
            f.bridge.pump()
            self.assert_interrupted(replay)
            self.assertEqual(replay["reply"]["id"], 202)
            self.assertIs(replay["reply"]["replayed"], True)
            self.assertEqual(executions, [expected_scope])
            self.assertEqual(cleanups, [expected_scope])
            self.assertEqual(owner["reply"], terminal)

            # Synchronous interruption releases healthy ownership; child advancement conservatively latches.
            _, next_batch, _ = f.enqueue(
                "batch", batch("test.mutate", transaction="B", params={"caller": "B"}),
                request_id=303)
            _, next_mutation, _ = f.enqueue("test.mutate", {"caller": "outside"}, request_id=404)
            _, next_read, _ = f.enqueue("test.read", {"caller": "R"}, request_id=505)
            f.bridge.pump()
            self.assertEqual(next_read["reply"]["status"], "ok")
            if phase == "synchronous":
                self.assertTrue(next_batch["reply"]["result"]["ok"])
                self.assertEqual(next_mutation["reply"]["status"], "ok")
                self.assertEqual(calls, [("mutation", "B", ("B",)), ("mutation", "outside", ()),
                                         ("observation", "R", ())])
                self.assertEqual(events, [("begin", "B"), ("end", "B")])
            else:
                self.assert_busy(next_batch)
                self.assert_busy(next_mutation)
                self.assertEqual(calls, [("observation", "R", ())])
                self.assertEqual(events, [("begin", "A"), ("end", "A")])
                f.bridge.stop()
                f.start()
                _, after_restart, _ = f.enqueue("test.mutate", request_id=606)
                _, cached, _ = f.enqueue(command, params, request_id=707)
                f.bridge.pump()
                self.assert_busy(after_restart)
                self.assert_interrupted(cached)
                self.assertIs(cached["reply"]["replayed"], True)
                self.assertEqual(executions, [expected_scope])
                self.assertEqual(cleanups, [expected_scope])
            self.assertEqual(active, [])

    def test_keyboard_interrupt_on_initial_batch_step_is_terminal_and_replayed(self):
        self.interrupted_command_case(KeyboardInterrupt, "initial")

    def test_system_exit_on_initial_batch_step_is_terminal_and_replayed(self):
        self.interrupted_command_case(SystemExit, "initial")

    def test_keyboard_interrupt_on_resumed_batch_step_is_terminal_and_replayed(self):
        self.interrupted_command_case(KeyboardInterrupt, "resumed")

    def test_system_exit_on_resumed_batch_step_is_terminal_and_replayed(self):
        self.interrupted_command_case(SystemExit, "resumed")

    def test_keyboard_interrupt_in_synchronous_command_is_terminal_and_replayed(self):
        self.interrupted_command_case(KeyboardInterrupt, "synchronous")

    def test_system_exit_in_synchronous_command_is_terminal_and_replayed(self):
        self.interrupted_command_case(SystemExit, "synchronous")

    def test_transaction_close_control_interrupt_preserves_unknown_barrier_and_replay(self):
        for error_type in (KeyboardInterrupt, SystemExit):
            with self.subTest(interrupt=error_type.__name__), Fixture() as f:
                active, events = transaction_probe(f, close_error=error_type("transaction close interrupted"))
                calls = []
                install_commands(f, active, calls)
                params = batch("test.mutate", params={"caller": "A"},
                               **{"async": True, "request_id": "close-interrupted"})
                _, owner, job_id = f.enqueue("batch", params, request_id=101)
                with self.assertRaises(error_type):
                    f.bridge.pump()
                self.assert_interrupted(owner)
                terminal = dict(owner["reply"])
                self.assertEqual(calls, [("mutation", "A", ("A",))])
                self.assertEqual(events, [("begin", "A"), ("close failed", "A")])

                _, candidate, _ = f.enqueue("batch", batch(transaction="B"), request_id=202)
                _, mutation, _ = f.enqueue("test.mutate", {"caller": "must-not-run"}, request_id=303)
                _, observation, _ = f.enqueue("test.read", {"caller": "R"}, request_id=404)
                f.bridge.pump()
                self.assert_busy(candidate)
                self.assert_busy(mutation)
                self.assertEqual(observation["reply"]["status"], "ok")
                self.assertEqual(owner["reply"], terminal)
                self.assertEqual(f.bridge._job_result({"id": 909}, {"job_id": job_id})
                                 ["result"]["reply"], terminal)

                f.bridge.stop()
                f.start()
                _, after_restart, _ = f.enqueue("test.mutate", request_id=505)
                _, replay, _ = f.enqueue("batch", params, request_id=606)
                _, read, _ = f.enqueue("test.read", {"caller": "R-after"}, request_id=707)
                f.bridge.pump()
                self.assert_busy(after_restart)
                self.assert_interrupted(replay)
                self.assertEqual(replay["reply"]["id"], 606)
                self.assertIs(replay["reply"]["replayed"], True)
                self.assertEqual(read["reply"]["status"], "ok")
                self.assertEqual([call for call in calls if call[0] == "mutation"],
                                 [("mutation", "A", ("A",))])
                self.assertEqual(events, [("begin", "A"), ("close failed", "A")])
                self.assertEqual(owner["reply"], terminal)

    def test_mutant_without_execution_gate_rejects_foreign_mutation_witness(self):
        needle = "busy = _batch_busy(req, risk)"
        self.assertEqual(SOURCE.count(needle), 1, "mutation must alter the actual execution gate")
        mutant = SOURCE.replace(needle, "busy = None", 1)
        with Fixture(mutant) as f:
            active, _ = transaction_probe(f)
            calls = []
            install_commands(f, active, calls)
            f.enqueue("batch", batch(params={"caller": "A"}), request_id=101)
            _, foreign, _ = f.enqueue("test.mutate", {"caller": "B"}, request_id=202)
            f.bridge.pump()
            with self.assertRaises(AssertionError):
                self.assert_busy(foreign)
            self.assertIn(("mutation", "B", ("A",)), calls)

    def test_mutant_without_prior_generator_check_rejects_transaction_overlap_witness(self):
        needle = "for _gen, other, box in _running"
        self.assertEqual(SOURCE.count(needle), 1, "mutation must alter the prior-generator gate")
        mutant = SOURCE.replace(needle, "for _gen, other, box in ()", 1)
        with Fixture(mutant) as f:
            active, events = transaction_probe(f)
            install_commands(f, active, [])
            f.enqueue("test.hold", request_id=101)
            _, candidate, _ = f.enqueue("batch", batch(), request_id=202)
            f.bridge.pump()
            with self.assertRaises(AssertionError):
                self.assert_busy(candidate)
            self.assertEqual(events, [("begin", "A")])

    def test_mutant_without_unknown_barrier_rejects_post_failure_dispatch_witness(self):
        needle = 'reason = _batch_scope["unknown"]'
        self.assertEqual(SOURCE.count(needle), 1, "mutation must alter the unknown-state gate")
        mutant = SOURCE.replace(needle, "reason = None", 1)
        with Fixture(mutant) as f:
            active, _ = transaction_probe(f, close_error=ValueError("undo close failed"))
            calls = []
            install_commands(f, active, calls)
            f.enqueue("batch", batch("test.mutate", params={"caller": "A"}), request_id=101)
            f.bridge.pump()
            _, foreign, _ = f.enqueue("test.mutate", {"caller": "B"}, request_id=202)
            f.bridge.pump()
            with self.assertRaises(AssertionError):
                self.assert_busy(foreign)
            self.assertIn(("mutation", "B", ("A",)), calls)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(BatchOwnershipTests))
    failed = {getattr(test, "test_case", test).id() for test, _ in result.failures + result.errors}
    print("%d/%d" % (result.testsRun - len(failed), result.testsRun))
    raise SystemExit(0 if result.wasSuccessful() else 1)
