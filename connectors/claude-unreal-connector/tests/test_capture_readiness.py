# SPDX-License-Identifier: MIT
"""Readiness and capture-order tests; no sockets, servers, or live editor.

Run with ``python -m unittest discover -s tests -p test_capture_readiness.py``.
The fake editor still enforces its game-thread rule. Engine APIs and monotonic
time are controlled here so a slow probe or a readiness flap is reproducible.
"""
import importlib.util
from pathlib import Path
import queue
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
PYTHON = HERE.parent / "plugin" / "ClaudeUnrealBridge" / "Content" / "Python"
REGISTRY_CHECK = "asset_registry_initial_scan"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


readiness = _load("_capture_readiness_test_helper", PYTHON / "capture_readiness.py")
fake_unreal = _load("_capture_readiness_fake_unreal", HERE / "fake_unreal.py")
with mock.patch.dict(sys.modules, {"capture_readiness": readiness, "unreal": fake_unreal}):
    bridge = _load("_capture_readiness_test_bridge", PYTHON / "claude_unreal_bridge.py")


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class SequencePredicate:
    """Consume readings, then repeat the final one; exceptions model API errors."""
    def __init__(self, readings, on_read=None):
        self.readings = list(readings)
        if not self.readings:
            raise ValueError("at least one reading is required")
        self.calls = 0
        self.on_read = on_read

    def __call__(self):
        value = self.readings[min(self.calls, len(self.readings) - 1)]
        self.calls += 1
        if self.on_read is not None:
            self.on_read()
        if isinstance(value, Exception):
            raise value
        return value


def api_with(registry=None, partition=None):
    api = types.SimpleNamespace()
    if registry is not None:
        api.AssetRegistryHelpers = types.SimpleNamespace(
            get_asset_registry=lambda: types.SimpleNamespace(is_loading_assets=registry))
    if partition is not None:
        api.WorldPartitionSubsystem = type("WorldPartitionSubsystem", (), {})
        api.SubsystemBlueprintLibrary = types.SimpleNamespace(
            get_world_subsystem=lambda world, cls: types.SimpleNamespace(
                is_all_streaming_completed=partition))
    return api


def finish(gen, max_steps=50):
    """A finite fake tick budget catches a stuck generator without sleeping."""
    for _ in range(max_steps):
        try:
            next(gen)
        except StopIteration as stop:
            return stop.value
    gen.close()
    raise AssertionError("generator exceeded the fake tick budget")


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.world = object()

    def wait(self, api, **kwargs):
        gen = readiness.wait_for_readiness(api, self.world, clock=self.clock, **kwargs)
        self.addCleanup(gen.close)
        return gen

    def test_two_warmup_frames_before_any_probe_and_two_idle_observations(self):
        registry = SequencePredicate([False])
        partition = SequencePredicate([True])
        gen = self.wait(api_with(registry, partition))
        next(gen)
        self.assertEqual((registry.calls, partition.calls), (0, 0))
        next(gen)
        self.assertEqual((registry.calls, partition.calls), (0, 0))
        next(gen)
        self.assertEqual((registry.calls, partition.calls), (0, 0))
        next(gen)
        self.assertEqual((registry.calls, partition.calls), (1, 1))
        report = finish(gen)
        self.assertEqual((registry.calls, partition.calls), (2, 2))
        self.assertTrue(report["condition_met"])
        self.assertEqual(report["warmup_frames"], 2)
        self.assertEqual(report["frames_waited"], 4)
        self.assertEqual(report["idle_frames_required"], 2)
        self.assertEqual(report["consecutive_idle_frames"], 2)

    def test_flaps_reset_the_consecutive_idle_count(self):
        # Asset registry: False means idle; partition: True means idle.
        registry = SequencePredicate([False, True, False, False])
        partition = SequencePredicate([True])
        gen = self.wait(api_with(registry, partition))
        for expected_calls in (0, 0, 0, 1, 2, 3):
            next(gen)
            self.assertEqual(registry.calls, expected_calls)
        report = finish(gen)
        self.assertEqual(registry.calls, 4)
        self.assertEqual(report["status"], "observed_idle")
        self.assertEqual(report["consecutive_idle_frames"], 2)
        self.assertEqual(report["frames_waited"], 6)

    def test_any_supported_busy_check_resets_the_count(self):
        registry = SequencePredicate([False])
        partition = SequencePredicate([True, False, True, True])
        report = finish(self.wait(api_with(registry, partition)))
        self.assertEqual((registry.calls, partition.calls), (4, 4))
        self.assertTrue(report["condition_met"])

    def test_partial_coverage_is_explicit_and_never_claims_render_completion(self):
        report = finish(self.wait(api_with(SequencePredicate([False]))))
        self.assertEqual(report["supported_checks"], [REGISTRY_CHECK])
        self.assertIn("world_partition", report["unsupported_checks"])
        self.assertIn("render_completion", report["unsupported_checks"])
        self.assertFalse(report["coverage_complete"])
        self.assertFalse(report["all_rendering_complete"])
        self.assertTrue(any(reason.startswith("render_completion:")
                            for reason in report["incomplete_reasons"]))
        self.assertTrue(report["condition_met"])

    def test_no_supported_predicates_cannot_pass(self):
        report = finish(self.wait(types.SimpleNamespace()))
        self.assertEqual(report["status"], "unsupported")
        self.assertFalse(report["condition_met"])
        self.assertEqual(report["supported_checks"], [])
        self.assertIn(REGISTRY_CHECK, report["unsupported_checks"])
        self.assertTrue(any("condition not met: unsupported" in reason
                            for reason in report["incomplete_reasons"]))

    def test_missing_providers_and_methods_report_unsupported(self):
        cases = (
            types.SimpleNamespace(AssetRegistryHelpers=types.SimpleNamespace()),
            types.SimpleNamespace(AssetRegistryHelpers=types.SimpleNamespace(
                get_asset_registry=lambda: None)),
            types.SimpleNamespace(AssetRegistryHelpers=types.SimpleNamespace(
                get_asset_registry=lambda: types.SimpleNamespace(is_loading_assets=False))),
            types.SimpleNamespace(WorldPartitionSubsystem=object(),
                SubsystemBlueprintLibrary=types.SimpleNamespace(get_world_subsystem=lambda w, c: None)),
        )
        for api in cases:
            with self.subTest(api=api):
                report = finish(self.wait(api))
                self.assertEqual(report["status"], "unsupported")
                self.assertFalse(report["condition_met"])

    def test_world_partition_requires_a_world_context(self):
        provider = mock.Mock(return_value=types.SimpleNamespace(is_all_streaming_completed=lambda: True))
        api = types.SimpleNamespace(WorldPartitionSubsystem=object(),
            SubsystemBlueprintLibrary=types.SimpleNamespace(get_world_subsystem=provider))
        report = finish(readiness.wait_for_readiness(api, None, clock=self.clock))
        self.assertEqual(report["status"], "unsupported")
        provider.assert_not_called()

    def test_provider_resolution_error_is_supported_but_unknown_and_fails(self):
        broken = mock.Mock(side_effect=RuntimeError("provider failed"))
        api = types.SimpleNamespace(AssetRegistryHelpers=types.SimpleNamespace(get_asset_registry=broken))
        report = finish(self.wait(api))
        self.assertEqual(report["status"], "probe_error")
        self.assertTrue(report["checks"][REGISTRY_CHECK]["supported"])
        self.assertEqual(report["checks"][REGISTRY_CHECK]["state"], "error")
        self.assertIn("RuntimeError: provider failed", report["checks"][REGISTRY_CHECK]["reason"])
        broken.assert_called_once_with()

    def test_predicate_exception_is_not_treated_as_idle(self):
        registry = SequencePredicate([RuntimeError("predicate failed")])
        report = finish(self.wait(api_with(registry)))
        self.assertEqual(report["status"], "probe_error")
        self.assertFalse(report["condition_met"])
        self.assertIn("RuntimeError: predicate failed", report["checks"][REGISTRY_CHECK]["reason"])
        self.assertEqual(registry.calls, 1)

    def test_non_bool_predicate_values_are_rejected(self):
        for value in (0, 1, None, "False", [], object()):
            with self.subTest(value=value):
                report = finish(self.wait(api_with(SequencePredicate([value]))))
                self.assertEqual(report["status"], "probe_error")
                self.assertFalse(report["condition_met"])
                self.assertIn("did not return a bool", report["checks"][REGISTRY_CHECK]["reason"])

    def test_one_good_predicate_does_not_hide_another_error(self):
        report = finish(self.wait(api_with(SequencePredicate([False]),
                                          SequencePredicate([RuntimeError("partition failed")]))))
        self.assertEqual(report["status"], "probe_error")
        self.assertEqual(report["checks"][REGISTRY_CHECK]["state"], "idle")
        self.assertEqual(report["checks"]["world_partition"]["state"], "error")

    def test_deadline_includes_warmup_and_prevents_probe(self):
        registry = SequencePredicate([False])
        gen = self.wait(api_with(registry), timeout=1)
        next(gen)
        self.clock.advance(1)
        report = finish(gen)
        self.assertEqual(report["status"], "timeout")
        self.assertEqual(report["frames_waited"], 1)
        self.assertEqual(registry.calls, 0)
        self.assertFalse(report["condition_met"])

    def test_shared_deadline_takes_precedence_over_a_fresh_timeout(self):
        self.clock.advance(4)
        registry = SequencePredicate([False])
        gen = self.wait(api_with(registry), timeout=10, deadline=5)
        next(gen)
        self.clock.advance(1)
        report = finish(gen)
        self.assertEqual(report["status"], "timeout")
        self.assertEqual(registry.calls, 0)

    def test_slow_predicate_cannot_pass_after_crossing_deadline(self):
        registry = SequencePredicate([False], on_read=lambda: self.clock.advance(0.6))
        report = finish(self.wait(api_with(registry), timeout=1))
        self.assertEqual(registry.calls, 2)
        self.assertEqual(report["status"], "timeout")
        self.assertFalse(report["condition_met"])
        self.assertGreaterEqual(report["elapsed_seconds"], 1)

    def test_slow_provider_cannot_pass_after_crossing_deadline(self):
        def get_registry():
            self.clock.advance(2)
            return types.SimpleNamespace(is_loading_assets=lambda: False)
        api = types.SimpleNamespace(AssetRegistryHelpers=types.SimpleNamespace(get_asset_registry=get_registry))
        report = finish(self.wait(api, timeout=1))
        self.assertEqual(report["status"], "timeout")
        self.assertFalse(report["condition_met"])

    def test_frame_limit_bounds_wait_even_if_monotonic_clock_does_not_advance(self):
        registry = SequencePredicate([True])
        with mock.patch.object(readiness, "MAX_FRAMES", 4):
            report = finish(self.wait(api_with(registry)), max_steps=6)
        self.assertEqual(report["status"], "frame_limit")
        self.assertEqual(report["frames_waited"], 4)
        self.assertFalse(report["condition_met"])

    def test_cancellation_during_warmup_does_not_probe(self):
        registry = SequencePredicate([False])
        cancelled = [False]
        gen = self.wait(api_with(registry), cancelled=lambda: cancelled[0])
        next(gen)
        cancelled[0] = True
        report = finish(gen)
        self.assertEqual(report["status"], "cancelled")
        self.assertEqual(registry.calls, 0)

    def test_cancellation_triggered_by_predicate_invalidates_its_idle_result(self):
        cancelled = [False]
        registry = SequencePredicate([False], on_read=lambda: cancelled.__setitem__(0, True))
        report = finish(self.wait(api_with(registry), cancelled=lambda: cancelled[0]))
        self.assertEqual(report["status"], "cancelled")
        self.assertFalse(report["condition_met"])
        self.assertEqual(registry.calls, 1)

    def test_post_capture_confirmation_advances_before_its_first_sample(self):
        registry = SequencePredicate([False])
        gen = self.wait(api_with(registry), warmup_frames=0, fail_on_busy=True)
        next(gen)
        self.assertEqual(registry.calls, 0)
        next(gen)
        self.assertEqual(registry.calls, 1)
        report = finish(gen)
        self.assertEqual(registry.calls, 2)
        self.assertEqual(report["frames_waited"], 2)
        self.assertTrue(report["condition_met"])

    def test_post_capture_busy_invalidates_immediately(self):
        registry = SequencePredicate([False, True, False, False])
        report = finish(self.wait(api_with(registry), warmup_frames=0, fail_on_busy=True))
        self.assertEqual(report["status"], "capture_invalidated")
        self.assertEqual(registry.calls, 2)
        self.assertEqual(report["consecutive_idle_frames"], 0)
        self.assertFalse(report["condition_met"])

    def test_readiness_does_not_call_heavyweight_wait_flush_or_update_apis(self):
        api = api_with(SequencePredicate([False]), SequencePredicate([True]))
        heavy_names = ("flush_async_loading", "flush_rendering_commands", "force_update",
                       "finish_all_compilation", "wait_for_shader_compilation",
                       "block_till_all_requests_finished", "tick", "collect_garbage")
        guards = {name: mock.Mock(side_effect=AssertionError("heavyweight API invoked: " + name))
                  for name in heavy_names}
        for name, guard in guards.items():
            setattr(api, name, guard)
        report = finish(self.wait(api))
        self.assertTrue(report["condition_met"])
        for guard in guards.values():
            guard.assert_not_called()


class CaptureBridgeTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.tmp = tempfile.TemporaryDirectory(prefix="capture-readiness-test-")
        self.addCleanup(self.tmp.cleanup)
        self.level = list(fake_unreal.LEVEL)
        self.addCleanup(lambda: fake_unreal.LEVEL.__setitem__(slice(None), self.level))
        fake_unreal.CALLS.clear()
        fake_unreal.STATE.update(pie=False, pie_wait=0)
        fake_unreal._SUBS.clear()
        fake_unreal._SHOTS.clear()
        fake_unreal.GAME_THREAD[0] = threading.get_ident()
        self.addCleanup(lambda: fake_unreal.GAME_THREAD.__setitem__(0, None))
        bridge._jobs = queue.Queue()
        bridge._running.clear()
        bridge._pumping.clear()
        bridge._replies.clear()
        bridge._replay_order.clear()
        bridge._server.update(sock=object(), thread=None, port=None, tick=None)
        self.addCleanup(lambda: bridge._server.update(sock=None, thread=None, port=None, tick=None))
        self.addCleanup(self.close_running)
        bridge.set_policy(bridge.RISKS)
        self.registry = SequencePredicate([False])
        self.exports = []
        original_export = fake_unreal.RenderingLibrary.export_render_target
        def export(*args):
            self.exports.append(self.registry.calls)
            return original_export(*args)
        original_wait = readiness.wait_for_readiness
        def wait(*args, **kwargs):
            kwargs["clock"] = self.clock
            return original_wait(*args, **kwargs)
        patches = (
            mock.patch.object(bridge.time, "monotonic", self.clock),
            mock.patch.object(bridge, "wait_for_readiness", wait),
            mock.patch.object(bridge.tempfile, "gettempdir", return_value=self.tmp.name),
            mock.patch.object(fake_unreal.AssetRegistryHelpers, "get_asset_registry",
                              side_effect=lambda: types.SimpleNamespace(is_loading_assets=self.registry)),
            mock.patch.object(fake_unreal.RenderingLibrary, "export_render_target", side_effect=export),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    @staticmethod
    def close_running():
        for gen, _req, _box in list(bridge._running):
            gen.close()
        bridge._running.clear()

    def capture_count(self):
        return fake_unreal.CALLS.count("capture_scene")

    def destroy_count(self):
        return fake_unreal.CALLS.count("destroy SceneCapture2D")

    def capture(self, params):
        gen = bridge.cmd_capture_view(params)
        self.addCleanup(gen.close)
        return gen

    def test_no_export_until_preconditions_and_post_capture_confirmation(self):
        gen = self.capture({"width": 640, "height": 360})
        steps = ((1, 0, 0), (2, 0, 0), (3, 0, 0), (4, 1, 0), (5, 2, 1), (6, 3, 1))
        for step, samples, captures in steps:
            next(gen)
            with self.subTest(step=step):
                self.assertEqual(self.registry.calls, samples)
                self.assertEqual(self.capture_count(), captures)
                self.assertEqual(self.exports, [])
        result = finish(gen)
        self.assertEqual(self.exports, [4])
        self.assertTrue(result["captured"])
        self.assertTrue(result["readiness_before_capture"]["condition_met"])
        self.assertTrue(result["readiness"]["condition_met"])
        self.assertFalse(result["readiness"]["all_rendering_complete"])
        self.assertEqual(result["readiness"]["frames_waited"], 2)
        self.assertGreater(result["bytes"], 0)
        self.assertTrue(Path(result["path"]).is_file())
        self.assertEqual(self.destroy_count(), 1)
        self.assertEqual(fake_unreal.LEVEL, self.level)

    def test_unsupported_readiness_reports_capture_false_and_never_exports(self):
        with mock.patch.object(fake_unreal, "AssetRegistryHelpers", None):
            result = finish(self.capture({}))
        self.assertFalse(result["captured"])
        self.assertEqual(result["readiness"]["status"], "unsupported")
        self.assertEqual(result["readiness_phase"], "before_capture")
        self.assertEqual((self.capture_count(), self.exports), (0, []))
        self.assertEqual(self.destroy_count(), 1)

    def test_pre_capture_flap_delays_capture_until_two_new_idle_ticks(self):
        self.registry = SequencePredicate([False, True, False, False])
        gen = self.capture({})
        for _ in range(6):
            next(gen)
            self.assertEqual(self.capture_count(), 0)
            self.assertEqual(self.exports, [])
        next(gen)
        self.assertEqual(self.registry.calls, 4)
        self.assertEqual(self.capture_count(), 1)
        self.assertEqual(self.exports, [])
        self.assertTrue(finish(gen)["captured"])

    def test_post_capture_busy_invalidates_without_recapture_or_export(self):
        self.registry = SequencePredicate([False, False, True, False, False])
        result = finish(self.capture({}))
        self.assertFalse(result["captured"])
        self.assertEqual(result["readiness_phase"], "after_capture")
        self.assertEqual(result["readiness"]["status"], "capture_invalidated")
        self.assertTrue(result["readiness_before_capture"]["condition_met"])
        self.assertEqual(self.registry.calls, 3)
        self.assertEqual((self.capture_count(), self.exports), (1, []))
        self.assertEqual(self.destroy_count(), 1)

    def test_post_capture_probe_error_prevents_export_and_cleans_up(self):
        self.registry = SequencePredicate([False, False, RuntimeError("late error")])
        result = finish(self.capture({}))
        self.assertFalse(result["captured"])
        self.assertEqual(result["readiness"]["status"], "probe_error")
        self.assertEqual(result["readiness_phase"], "after_capture")
        self.assertEqual((self.capture_count(), self.exports), (1, []))
        self.assertEqual(self.destroy_count(), 1)

    def test_shared_deadline_includes_both_phases_and_slow_predicates(self):
        self.registry = SequencePredicate([False], on_read=lambda: self.clock.advance(0.26))
        result = finish(self.capture({"readiness_timeout": 1}))
        self.assertFalse(result["captured"])
        self.assertEqual(result["readiness_phase"], "after_capture")
        self.assertEqual(result["readiness"]["status"], "timeout")
        self.assertGreaterEqual(self.clock(), 1)
        self.assertEqual((self.capture_count(), self.exports), (1, []))
        self.assertEqual(self.destroy_count(), 1)

    def test_shared_deadline_also_counts_warmup_ticks(self):
        gen = self.capture({"readiness_timeout": 1})
        next(gen)
        for _ in range(3):
            self.clock.advance(0.2)
            next(gen)
        self.assertEqual(self.capture_count(), 0)
        self.clock.advance(0.4)
        result = finish(gen)
        self.assertFalse(result["captured"])
        self.assertEqual(result["readiness"]["status"], "timeout")
        self.assertEqual(result["readiness_phase"], "before_capture")
        self.assertEqual(self.exports, [])

    def test_socket_shutdown_during_warmup_returns_cancelled_and_cleans_up(self):
        gen = self.capture({})
        next(gen)
        bridge._server["sock"] = None
        result = finish(gen)
        self.assertFalse(result["captured"])
        self.assertEqual(result["readiness"]["status"], "cancelled")
        self.assertEqual((self.capture_count(), self.exports), (0, []))
        self.assertEqual(self.destroy_count(), 1)

    def test_replacement_socket_during_post_capture_wait_cancels_old_owner(self):
        gen = self.capture({})
        for _ in range(5):
            next(gen)
        self.assertEqual(self.capture_count(), 1)
        bridge._server["sock"] = object()
        result = finish(gen)
        self.assertFalse(result["captured"])
        self.assertEqual(result["readiness_phase"], "after_capture")
        self.assertEqual(result["readiness"]["status"], "cancelled")
        self.assertEqual((self.capture_count(), self.exports), (1, []))
        self.assertEqual(self.destroy_count(), 1)

    def test_generator_close_cleans_up_before_and_after_capture(self):
        for steps in (1, 5):
            with self.subTest(steps=steps):
                fake_unreal.CALLS.clear()
                self.registry = SequencePredicate([False])
                gen = self.capture({})
                for _ in range(steps):
                    next(gen)
                gen.close()
                gen.close()
                self.assertEqual(self.destroy_count(), 1)
                self.assertEqual(fake_unreal.LEVEL, self.level)
                self.assertEqual(self.exports, [])

    def test_timeout_validation_happens_before_any_capture_allocation(self):
        values = (False, True, 0, -1, 31, float("nan"), float("inf"), "invalid", None)
        with mock.patch.object(fake_unreal.RenderingLibrary, "create_render_target2d") as allocate:
            for value in values:
                with self.subTest(value=value):
                    gen = self.capture({"readiness_timeout": value})
                    with self.assertRaises((ValueError, TypeError)):
                        next(gen)
                    allocate.assert_not_called()
                    self.assertEqual(fake_unreal.CALLS, [])

    def test_invalid_dimension_is_rejected_before_any_capture_allocation(self):
        with mock.patch.object(fake_unreal.RenderingLibrary, "create_render_target2d") as allocate:
            with self.assertRaises(ValueError):
                next(self.capture({"width": "bad"}))
            allocate.assert_not_called()
        self.assertEqual(fake_unreal.CALLS, [])

    def test_queue_pump_advances_once_per_tick_and_preserves_independent_reads(self):
        capture_box = {"done": threading.Event(), "reply": None}
        read_box = {"done": threading.Event(), "reply": None}
        bridge._jobs.put(({"id": "capture", "type": "capture_view", "params": {}}, capture_box))
        bridge._jobs.put(({"id": "read", "type": "get_level_info", "params": {}}, read_box))
        bridge.pump()
        self.assertFalse(capture_box["done"].is_set())
        self.assertTrue(read_box["done"].is_set())
        self.assertEqual(read_box["reply"]["status"], "ok")
        self.assertEqual(self.registry.calls, 0)
        for samples in (0, 0, 1, 2, 3):
            bridge.pump()
            self.assertEqual(self.registry.calls, samples)
            self.assertFalse(capture_box["done"].is_set())
            self.assertEqual(self.exports, [])
        bridge.pump()
        self.assertTrue(capture_box["done"].is_set())
        self.assertTrue(capture_box["reply"]["result"]["captured"])
        self.assertEqual(self.exports, [4])
        self.assertEqual(bridge._running, [])

    def test_queue_pump_cancellation_finishes_reply_without_export(self):
        box = {"done": threading.Event(), "reply": None}
        bridge._jobs.put(({"id": "capture", "type": "capture_view", "params": {}}, box))
        bridge.pump()
        bridge._server["sock"] = None
        bridge.pump()
        self.assertTrue(box["done"].is_set())
        self.assertEqual(box["reply"]["status"], "ok")
        self.assertFalse(box["reply"]["result"]["captured"])
        self.assertEqual(box["reply"]["result"]["readiness"]["status"], "cancelled")
        self.assertEqual(self.exports, [])
        self.assertEqual(self.destroy_count(), 1)
        self.assertEqual(bridge._running, [])

    def test_capture_does_not_use_console_commands_play_or_force_update(self):
        guards = (
            mock.patch.object(fake_unreal.SystemLibrary, "execute_console_command",
                              side_effect=AssertionError("console mutation invoked")),
            mock.patch.object(fake_unreal.LevelEditorSubsystem, "editor_request_begin_play",
                              side_effect=AssertionError("Play invoked")),
            mock.patch.object(fake_unreal.RenderingLibrary, "flush_rendering_commands", create=True,
                              side_effect=AssertionError("render flush invoked")),
            mock.patch.object(fake_unreal, "force_update", create=True,
                              side_effect=AssertionError("force update invoked")),
        )
        mocks = [guard.start() for guard in guards]
        try:
            self.assertTrue(finish(self.capture({}))["captured"])
            for guard in mocks:
                guard.assert_not_called()
        finally:
            for guard in reversed(guards):
                guard.stop()


if __name__ == "__main__":
    unittest.main()
