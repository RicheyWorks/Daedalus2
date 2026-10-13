# SPDX-License-Identifier: MIT
"""Offline publication/recovery canaries for the copied artqueue candidate.

Run only after candidate/artqueue.py is ready:
    python -m unittest discover -s candidate -p artqueue_publication_test.py -v

The candidate is loaded with synthetic sibling modules. No editor, hub, network,
shared art directory, launcher or production module is used.
"""
import importlib.util
import json
import os
from pathlib import Path
import queue
import re
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock


ASSET = "Prop_PublicationCanary"
OTHER = "Prop_ProducerOwned"
CLAIM = re.compile(r"\[queue-claim:([0-9a-f]{32})\]")
BOARD = (
    "# Offline art queue\n\n"
    "| # | Asset | Kind | Status | Notes |\n"
    "|---|---|---|---|---|\n"
    "| 1 | %s | prop | READY | asset owner note |\n"
    "<!-- blender-team rows: begin -->\n"
    "| 2 | %s | prop | READY | producer note |\n"
    "<!-- blender-team rows: end -->\n"
) % (ASSET, OTHER)


class NoShipping:
    """Effect counter: any attempted shipment is an explicit test failure."""

    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append(("ship", args, kwargs))
        raise AssertionError("Reconciliation must not ship or reimport")

    def export(self, *args, **kwargs):
        self.calls.append(("export", args, kwargs))
        raise AssertionError("Reconciliation must not export")

    def land(self, *args, **kwargs):
        self.calls.append(("land", args, kwargs))
        raise AssertionError("Reconciliation must not import")


def load_candidate():
    """Use real candidate code with dependency boundaries replaced before import."""
    name = "_offline_artqueue_publication_candidate"
    package = types.ModuleType(name)
    package.__path__ = [str(Path(__file__).parent)]
    sys.modules[name] = package
    pipeline = types.ModuleType(name + ".ship")
    effect_guard = NoShipping()
    pipeline.ship = effect_guard
    pipeline.export = effect_guard.export
    pipeline.land = effect_guard.land
    pipeline.prebuilt = effect_guard.export
    wire = types.ModuleType(name + ".wire")
    wire.BLENDER = ("offline-blender", 0)
    wire.UNREAL = ("offline-unreal", 0)
    wire.BridgeError = type("OfflineBridgeError", (RuntimeError,), {})
    wire.reachable = lambda *args, **kwargs: True

    def fake_call(addr, command, **kwargs):
        if command == "execute_python":
            return {"result": False}  # The Play preflight only; shipping is injected.
        return {"result": {"objects": [ASSET], "source": "collection"}}

    wire.call = fake_call
    link = types.ModuleType(name + ".teamlink")
    for suffix, module in (("ship", pipeline), ("wire", wire), ("teamlink", link)):
        sys.modules[name + "." + suffix] = module
        setattr(package, suffix, module)
    source_path = Path(__file__).resolve().parents[1] / "asset_pipeline" / "artqueue.py"
    spec = importlib.util.spec_from_file_location(name + ".artqueue", source_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def report(asset=ASSET):
    mesh = {"name": asset, "triangles": 12, "materials": ["M_Canary"], "dims": [1.0, 0.5, 0.25]}
    return {
        "name": asset, "path": "offline-fixture.glb",
        "dest": "/Game/Daedalus/Art/Prop/" + asset,
        "started": 1.0, "seconds": 0.2, "exported_s": 0.05, "imported_s": 0.15,
        "ok": True,
        "checks": [{"check": "offline import evidence", "ok": True, "detail": "fixture"}],
        "blender": {"objects": [mesh]},
        "file": {"nodes": [{"name": asset, "mesh": 0, "dims": mesh["dims"]}], "meshes": [mesh]},
        "unreal": {"meshes": [{"name": asset, "path": "/Game/Canary." + asset,
                                  "triangles": 12, "render_triangles": 12}], "materials": []},
    }


def sharing_error():
    error = PermissionError(13, "injected queue sharing violation")
    error.winerror = 5
    return error


class PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_candidate()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="artqueue-publication-offline-")
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.queue_file = self.folder / "QUEUE.md"
        self.queue_file.write_text(BOARD, encoding="utf-8")
        self.shipping = NoShipping()
        self.watcher = self.mod.Watcher(str(self.folder), ship=self.shipping, link=None)
        self.report_file = self.folder / "reports" / (ASSET + ".json")

    def row(self, asset=ASSET):
        rows, _ = self.mod.parse(self.queue_file.read_text(encoding="utf-8"))
        return next(row for row in rows if row["asset"] == asset)

    def events(self):
        path = self.folder / "feed.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

    def claim(self):
        prepared = self.watcher.prepare(ASSET)
        self.assertEqual(len(prepared), 3)
        self.assertEqual(self.mod.state(self.row()["status"]), "SHIPPING")
        token = CLAIM.search(self.row()["notes"])
        self.assertIsNotNone(token, "a successful claim needs its durable attempt token")
        return token.group(1)

    def pending(self):
        """Create a verified import with an injected failure publishing its row."""
        token = self.claim()
        real_replace = os.replace

        def deny_queue(source, destination):
            if Path(destination) == self.queue_file:
                raise sharing_error()
            return real_replace(source, destination)

        with mock.patch.object(self.mod.os, "replace", side_effect=deny_queue), \
                mock.patch.object(self.mod.time, "sleep", return_value=None):
            try:
                self.watcher.finish(ASSET, "Prop", report())
            except Exception:
                # Either an explicit publication exception or pending result is acceptable;
                # the durable evidence and lack of shipping effects are the contract.
                pass
        stored = json.loads(self.report_file.read_text(encoding="utf-8"))
        publication = stored["_queue_publication"]
        self.assertEqual(publication["state"], "pending")
        self.assertEqual(publication["asset"], ASSET)
        self.assertEqual(publication["claim_token"], token)
        self.assertTrue(publication["status"].startswith("SHIPPED"))
        self.assertIsInstance(publication["notes"], str)
        self.assertEqual(self.mod.state(self.row()["status"]), "SHIPPING")
        self.assertFalse(any(e.get("asset") == ASSET and e.get("event") == "shipped" for e in self.events()))
        self.assertEqual(self.shipping.calls, [])
        return stored

    def test_sharing_violation_is_bounded_and_retry_rebases_producer_edit(self):
        real_replace = os.replace
        sources = []
        injected = False

        def replace(source, destination):
            nonlocal injected
            if Path(destination) == self.queue_file:
                sources.append(str(source))
                if not injected:
                    injected = True
                    text = self.queue_file.read_text(encoding="utf-8")
                    text = self.mod.set_row(text, OTHER, "DOING", "producer advanced during retry")
                    self.queue_file.write_text(text + "<!-- producer appended footer -->\n", encoding="utf-8")
                    raise sharing_error()
            return real_replace(source, destination)

        with mock.patch.object(self.mod.os, "replace", side_effect=replace), \
                mock.patch.object(self.mod.time, "sleep", return_value=None):
            self.assertTrue(self.watcher.update(ASSET, "SHIPPING", "claim fixture"))
        self.assertGreaterEqual(len(sources), 2)
        self.assertLessEqual(len(sources), 10, "sharing errors require a finite retry bound")
        self.assertEqual(self.row(OTHER)["status"], "DOING")
        self.assertEqual(self.row(OTHER)["notes"], "producer advanced during retry")
        self.assertIn("<!-- producer appended footer -->", self.queue_file.read_text(encoding="utf-8"))
        self.assertTrue(all(Path(source) != Path(str(self.queue_file) + ".tmp") for source in sources))

    def test_final_reread_prevents_overwriting_edit_after_temp_was_written(self):
        real_read = self.watcher.read
        changed = False

        def read():
            nonlocal changed
            # Discover a written staging file without relying on its random filename.
            staging = [p for p in self.folder.iterdir() if p.is_file() and p != self.queue_file]
            if staging and not changed:
                changed = True
                text = self.queue_file.read_text(encoding="utf-8")
                text = self.mod.set_row(text, OTHER, "DOING", "edit after staging")
                self.queue_file.write_text(text, encoding="utf-8")
            return real_read()

        with mock.patch.object(self.watcher, "read", side_effect=read):
            self.assertTrue(self.watcher.update(ASSET, "SHIPPING", "own claim"))
        self.assertTrue(changed, "the writer must reread after writing its staging file")
        self.assertEqual(self.row(OTHER)["status"], "DOING")
        self.assertEqual(self.row(OTHER)["notes"], "edit after staging")

    def test_independent_updates_use_distinct_staging_paths(self):
        real_replace = os.replace
        sources = []

        def replace(source, destination):
            if Path(destination) == self.queue_file:
                sources.append(str(source))
            return real_replace(source, destination)

        with mock.patch.object(self.mod.os, "replace", side_effect=replace):
            self.assertTrue(self.watcher.update(ASSET, "DOING", "first"))
            self.assertTrue(self.watcher.update(OTHER, "DOING", "second"))
        self.assertEqual(len(sources), 2)
        self.assertEqual(len(set(sources)), 2)
        self.assertFalse(Path(str(self.queue_file) + ".tmp").exists())

    def test_failed_claim_never_exports_imports_or_announces_shipping(self):
        original = self.queue_file.read_bytes()
        with mock.patch.object(self.watcher, "_change_board", return_value=False):
            try:
                self.watcher.ship_one(ASSET)
            except Exception:
                pass
        self.assertEqual(self.queue_file.read_bytes(), original)
        self.assertEqual(self.shipping.calls, [])
        self.assertFalse(any(e.get("asset") == ASSET and e.get("event") == "shipping" for e in self.events()))

    def test_verified_report_precedes_publication_and_is_then_marked_published(self):
        token = self.claim()
        real_replace = os.replace
        observations = []

        def replace(source, destination):
            if Path(destination) == self.queue_file:
                saved = json.loads(self.report_file.read_text(encoding="utf-8"))
                observations.append(saved["_queue_publication"])
            return real_replace(source, destination)

        with mock.patch.object(self.mod.os, "replace", side_effect=replace):
            self.watcher.finish(ASSET, "Prop", report())
        self.assertTrue(observations)
        self.assertEqual(observations[0]["state"], "pending")
        self.assertEqual(observations[0]["claim_token"], token)
        saved = json.loads(self.report_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["_queue_publication"]["state"], "published")
        self.assertEqual(self.mod.state(self.row()["status"]), "SHIPPED")
        self.assertEqual(sum(e.get("asset") == ASSET and e.get("event") == "shipped" for e in self.events()), 1)
        self.assertEqual(self.shipping.calls, [])

    def test_pending_report_survives_restart_and_reconciles_without_shipping(self):
        self.pending()
        restarted = self.mod.Watcher(str(self.folder), ship=self.shipping, link=None)
        restarted.recover()
        self.assertEqual(self.mod.state(self.row()["status"]), "SHIPPED")
        saved = json.loads(self.report_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["_queue_publication"]["state"], "published")
        self.assertEqual(self.shipping.calls, [])
        # Repeated reconciliation cannot publish or dispatch the same attempt twice.
        before = self.events()
        restarted.recover()
        self.assertEqual(self.events(), before)
        self.assertEqual(self.shipping.calls, [])

    def test_unknown_shipping_rows_are_preserved_without_blanket_reset(self):
        text = self.mod.set_row(BOARD, ASSET, "SHIPPING", "legacy claim without report")
        text = self.mod.set_row(text, OTHER, "SHIPPING", "[queue-claim:" + "a" * 32 + "]")
        self.queue_file.write_text(text, encoding="utf-8")
        self.watcher.recover()
        self.assertEqual(self.queue_file.read_text(encoding="utf-8"), text)
        self.assertEqual(self.shipping.calls, [])
        self.assertFalse(any(e.get("event") == "requeued" for e in self.events()))

    def test_pending_report_with_changed_claim_is_not_published(self):
        saved = self.pending()
        token = saved["_queue_publication"]["claim_token"]
        replacement = "b" * 32 if token != "b" * 32 else "c" * 32
        text = self.mod.set_row(self.queue_file.read_text(encoding="utf-8"), ASSET,
                                "SHIPPING", "[queue-claim:" + replacement + "] owner superseded claim")
        self.queue_file.write_text(text, encoding="utf-8")
        restarted = self.mod.Watcher(str(self.folder), ship=self.shipping, link=None)
        restarted.recover()
        self.assertEqual(self.queue_file.read_text(encoding="utf-8"), text)
        self.assertEqual(json.loads(self.report_file.read_text(encoding="utf-8"))["_queue_publication"]["state"], "pending")
        self.assertEqual(self.shipping.calls, [])

    def test_reconcile_retry_does_not_overwrite_claim_superseded_during_retry(self):
        saved = self.pending()
        old_token = saved["_queue_publication"]["claim_token"]
        new_token = "d" * 32 if old_token != "d" * 32 else "e" * 32
        restarted = self.mod.Watcher(str(self.folder), ship=self.shipping, link=None)
        real_replace = os.replace
        injected = False

        def replace(source, destination):
            nonlocal injected
            if Path(destination) == self.queue_file and not injected:
                injected = True
                text = self.queue_file.read_text(encoding="utf-8")
                text = self.mod.set_row(text, ASSET, "SHIPPING",
                                        "[queue-claim:" + new_token + "] owner changed revision")
                self.queue_file.write_text(text, encoding="utf-8")
                raise sharing_error()
            return real_replace(source, destination)

        with mock.patch.object(self.mod.os, "replace", side_effect=replace), \
                mock.patch.object(self.mod.time, "sleep", return_value=None):
            restarted.recover()
        self.assertTrue(injected)
        self.assertEqual(self.mod.state(self.row()["status"]), "SHIPPING")
        self.assertIn("[queue-claim:" + new_token + "]", self.row()["notes"])
        self.assertEqual(json.loads(self.report_file.read_text(encoding="utf-8"))["_queue_publication"]["state"], "pending")
        self.assertEqual(self.shipping.calls, [])

    def test_tick_excludes_pending_report_even_when_row_is_ready(self):
        saved = self.pending()
        text = self.mod.set_row(self.queue_file.read_text(encoding="utf-8"), ASSET, "READY", "owner review pending")
        text = self.mod.set_row(text, OTHER, "TODO")
        self.queue_file.write_text(text, encoding="utf-8")
        restarted = self.mod.Watcher(str(self.folder), ship=self.shipping, link=None)
        with mock.patch.object(restarted, "ship_one", side_effect=AssertionError("pending import must not dispatch")) as ship_one:
            restarted.tick()
        ship_one.assert_not_called()
        self.assertEqual(self.shipping.calls, [])
        self.assertEqual(json.loads(self.report_file.read_text(encoding="utf-8"))["_queue_publication"], saved["_queue_publication"])

    def _write_held_report(self, publication):
        self.report_file.parent.mkdir(exist_ok=True)
        value = report()
        value["_queue_publication"] = publication
        self.report_file.write_text(json.dumps(value), encoding="utf-8")
        text = self.mod.set_row(BOARD, OTHER, "TODO")
        self.queue_file.write_text(text, encoding="utf-8")

    def _assert_report_ready_is_held(self):
        before = self.report_file.read_bytes()
        self.watcher.tick()
        self.assertEqual(self.row()["status"], "READY")
        self.assertEqual(self.shipping.calls, [])
        self.assertEqual(self.report_file.read_bytes(), before)

    def test_unreadable_report_on_ready_row_never_dispatches(self):
        self._write_held_report({"state": "pending", "asset": ASSET})
        real_open = open

        def denied(path, *args, **kwargs):
            if Path(path) == self.report_file:
                raise PermissionError("offline unreadable publication witness")
            return real_open(path, *args, **kwargs)

        with mock.patch("builtins.open", side_effect=denied):
            self.watcher.tick()
        self.assertEqual(self.row()["status"], "READY")
        self.assertEqual(self.shipping.calls, [])

    def test_publication_metadata_wrong_asset_never_dispatches(self):
        self._write_held_report({"state": "pending", "asset": OTHER,
                                 "claim_token": "f" * 32, "status": "SHIPPED", "notes": "fixture"})
        self._assert_report_ready_is_held()

    def test_publication_metadata_wrong_state_never_dispatches(self):
        self._write_held_report({"state": "not-a-publication-state", "asset": ASSET,
                                 "claim_token": "f" * 32, "status": "SHIPPED", "notes": "fixture"})
        self._assert_report_ready_is_held()

    def test_publication_metadata_nondict_never_dispatches(self):
        self._write_held_report(["pending", ASSET])
        self._assert_report_ready_is_held()

    def test_single_ship_bridge_error_after_effect_is_held_across_ticks(self):
        effects = []

        def ship(*args, **kwargs):
            effects.append(args)
            raise self.mod.wire.BridgeError("offline reply error after dispatch")

        self.queue_file.write_text(self.mod.set_row(BOARD, OTHER, "TODO"), encoding="utf-8")
        watcher = self.mod.Watcher(str(self.folder), ship=ship, link=None)
        self.assertEqual(watcher.ship_one(ASSET), (ASSET, "UNCERTAIN_IMPORT"))
        self.assertEqual(self.row()["status"], "SHIPPING")
        watcher.clock = lambda: time.time() + 10 * self.mod.BLOCKED_RETRY_S
        watcher.tick()
        watcher.tick()
        self.assertEqual(len(effects), 1)
        self.assertEqual(self.row()["status"], "SHIPPING")
        self.assertFalse(any(e.get("event") == "requeued" for e in self.events()))

    def test_eof_dispatch_witness_survives_ready_reset_and_fresh_watcher(self):
        effects = []

        def ship(*args, **kwargs):
            # The durable witness must exist before an import effect is possible.
            stored = json.loads(self.report_file.read_text(encoding="utf-8"))
            witness = stored["_queue_uncertainty"]
            self.assertEqual(witness["state"], "unresolved")
            self.assertEqual(witness["asset"], ASSET)
            self.assertRegex(witness["claim_token"], r"^[0-9a-f]{32}$")
            effects.append(args)
            raise EOFError("offline import reply ended after dispatch")

        self.queue_file.write_text(self.mod.set_row(BOARD, OTHER, "TODO"), encoding="utf-8")
        watcher = self.mod.Watcher(str(self.folder), ship=ship, link=None)
        self.assertEqual(watcher.ship_one(ASSET), (ASSET, "UNCERTAIN_IMPORT"))
        self.assertEqual(len(effects), 1)
        witness_bytes = self.report_file.read_bytes()
        reset = self.mod.set_row(self.queue_file.read_text(encoding="utf-8"), ASSET, "READY", "")
        self.queue_file.write_text(reset, encoding="utf-8")
        guard = NoShipping()
        restarted = self.mod.Watcher(str(self.folder), ship=guard, link=None)
        restarted.recover()
        restarted.tick()
        restarted.tick()
        self.assertEqual(guard.calls, [])
        self.assertEqual(len(effects), 1)
        self.assertEqual(self.row()["status"], "READY")
        self.assertEqual(self.row()["notes"], "")
        self.assertEqual(self.report_file.read_bytes(), witness_bytes)

    def test_overlapped_bridge_error_after_effect_stops_next_land(self):
        effects = []

        class FakeShipping:
            def export(inner, asset, *args, **kwargs):
                return report(asset)

            def land(inner, value, *args, **kwargs):
                effects.append(value["name"])
                raise self.mod.wire.BridgeError("offline reply error after import effect")

        watcher = self.mod.Watcher(str(self.folder), ship=FakeShipping(), link=None)
        watcher.prepare = lambda asset: (asset, "Prop", {"objects": [asset], "source": "collection"})
        watcher._stage = mock.Mock()
        watcher.finish = mock.Mock(side_effect=AssertionError("no success after uncertain dispatch"))
        assets = ["Prop_BridgeUncertain_%02d" % i for i in range(8)]
        result = watcher.ship_overlapped(assets)
        self.assertEqual(effects, [assets[0]])
        self.assertIn((assets[0], "UNCERTAIN_IMPORT"), result)
        watcher.finish.assert_not_called()

    def test_decode_or_judge_exception_after_effect_is_uncertain_without_retry(self):
        for error in (json.JSONDecodeError("offline bad reply", "{", 0), KeyError("meshes")):
            with self.subTest(error=type(error).__name__):
                # Each subcase owns a fresh temporary attempt; the preceding
                # unresolved witness must not turn this into a restart test.
                if self.report_file.exists():
                    self.report_file.unlink()
                effects = []
                self.queue_file.write_text(self.mod.set_row(BOARD, OTHER, "TODO"), encoding="utf-8")

                def ship(*args, **kwargs):
                    effects.append(args)
                    raise error

                watcher = self.mod.Watcher(str(self.folder), ship=ship, link=None)
                self.assertEqual(watcher.ship_one(ASSET), (ASSET, "UNCERTAIN_IMPORT"))
                watcher.clock = lambda: time.time() + 10 * self.mod.BLOCKED_RETRY_S
                watcher.tick()
                self.assertEqual(len(effects), 1)
                self.assertEqual(self.row()["status"], "SHIPPING")

    def test_unresolved_import_globally_holds_unrelated_ready_after_restart(self):
        effects = []

        def ship(asset, *args, **kwargs):
            effects.append(asset)
            raise EOFError("offline reply lost after first import effect")

        watcher = self.mod.Watcher(str(self.folder), ship=ship, link=None)
        self.assertEqual(watcher.ship_one(ASSET), (ASSET, "UNCERTAIN_IMPORT"))
        reset = self.mod.set_row(self.queue_file.read_text(encoding="utf-8"), ASSET, "READY", "")
        self.queue_file.write_text(reset, encoding="utf-8")
        guard = NoShipping()
        restarted = self.mod.Watcher(str(self.folder), ship=guard, link=None)
        with mock.patch.object(self.mod.wire, "reachable", side_effect=AssertionError("held watcher must not probe editors")) as reachable, \
                mock.patch.object(self.mod.wire, "call", side_effect=AssertionError("held watcher must not call editors")) as call:
            restarted.tick()
            restarted.tick()
        reachable.assert_not_called()
        call.assert_not_called()
        self.assertEqual(effects, [ASSET])
        self.assertEqual(guard.calls, [])
        self.assertEqual(self.row(OTHER)["status"], "READY")
        self.assertEqual(self.row()["notes"], "")
        self.assertIn("reconcil", (self.folder / "STATUS.md").read_text(encoding="utf-8").lower())

    def test_same_tick_simple_ship_uncertainty_stops_unrelated_prepare(self):
        effects = []

        def ship(asset, *args, **kwargs):
            effects.append(asset)
            raise EOFError("offline reply lost after first import effect")

        watcher = self.mod.Watcher(str(self.folder), ship=ship, link=None)
        with mock.patch.object(watcher, "prepare", wraps=watcher.prepare) as prepare:
            result = watcher.tick()
        self.assertIn((ASSET, "UNCERTAIN_IMPORT"), result)
        self.assertEqual(effects, [ASSET])
        self.assertEqual(prepare.call_args_list, [mock.call(ASSET)])
        self.assertEqual(self.row(OTHER)["status"], "READY")
        self.assertIsNone(CLAIM.search(self.row(OTHER)["notes"]))

    def test_known_completed_same_claim_pending_publication_allows_other_preflight(self):
        stored = self.pending()
        token = CLAIM.search(self.row()["notes"]).group(1)
        text = self.queue_file.read_text(encoding="utf-8")
        notes = self.row()["notes"] + " [queue-stage:import-started]"
        self.queue_file.write_text(self.mod.set_row(text, ASSET, "SHIPPING", notes), encoding="utf-8")
        self.assertEqual(stored["_queue_publication"]["claim_token"], token)
        rows, _ = self.mod.parse(self.queue_file.read_text(encoding="utf-8"))
        self.assertEqual(self.watcher.unresolved_imports(rows), set())
        with mock.patch.object(self.watcher, "_change_board", return_value=False), \
                mock.patch.object(self.mod.wire, "reachable", return_value=True) as reachable, \
                mock.patch.object(self.watcher, "ship_one", return_value=(OTHER, "SHIPPED")) as ship_one:
            result = self.watcher.tick()
        self.assertEqual(reachable.call_count, 2)
        ship_one.assert_called_once_with(OTHER)
        self.assertIn((ASSET, "PUBLICATION_PENDING"), result)
        self.assertIn((OTHER, "SHIPPED"), result)
        self.assertEqual(self.shipping.calls, [])

    def test_same_process_sweeps_terminal_pending_report_before_reachability(self):
        self.claim()
        text = self.mod.set_row(self.queue_file.read_text(encoding="utf-8"), OTHER, "TODO")
        self.queue_file.write_text(text, encoding="utf-8")
        save_report = self.watcher._save_report
        rejected_published_save = False

        def save(asset, value):
            nonlocal rejected_published_save
            if value.get("_queue_publication", {}).get("state") == "published" and not rejected_published_save:
                rejected_published_save = True
                raise sharing_error()
            return save_report(asset, value)

        with mock.patch.object(self.watcher, "_save_report", side_effect=save):
            self.watcher.finish(ASSET, "Prop", report())
        self.assertTrue(rejected_published_save)
        self.assertEqual(self.mod.state(self.row()["status"]), "SHIPPED")
        self.assertEqual(json.loads(self.report_file.read_text(encoding="utf-8"))["_queue_publication"]["state"], "pending")
        with mock.patch.object(self.mod.wire, "reachable", side_effect=AssertionError("pending publication must sweep first")) as reachable:
            self.watcher.tick()
        reachable.assert_not_called()
        self.assertEqual(json.loads(self.report_file.read_text(encoding="utf-8"))["_queue_publication"]["state"], "published")
        self.assertEqual(self.shipping.calls, [])

    def test_two_watchers_cannot_both_claim_the_same_asset(self):
        first_token = self.claim()
        second = self.mod.Watcher(str(self.folder), ship=self.shipping, link=None)
        second_succeeded = False
        try:
            prepared = second.prepare(ASSET)
            second_succeeded = isinstance(prepared, (tuple, list)) and len(prepared) == 3
        except Exception:
            pass
        self.assertFalse(second_succeeded)
        self.assertEqual(CLAIM.search(self.row()["notes"]).group(1), first_token)
        self.assertEqual(self.shipping.calls, [])

    def test_ready_revision_superseded_during_claim_retry_is_preserved(self):
        real_replace = os.replace
        injected = False

        def replace(source, destination):
            nonlocal injected
            if Path(destination) == self.queue_file and not injected:
                injected = True
                text = self.mod.set_row(self.queue_file.read_text(encoding="utf-8"), ASSET,
                                        "READY", "producer supplied a newer revision")
                self.queue_file.write_text(text, encoding="utf-8")
                raise sharing_error()
            return real_replace(source, destination)

        with mock.patch.object(self.mod.os, "replace", side_effect=replace), \
                mock.patch.object(self.mod.time, "sleep", return_value=None):
            try:
                self.watcher.prepare(ASSET)
            except Exception:
                pass
        self.assertTrue(injected)
        self.assertEqual(self.row()["status"], "READY")
        self.assertEqual(self.row()["notes"], "producer supplied a newer revision")
        self.assertIsNone(CLAIM.search(self.row()["notes"]))
        self.assertEqual(self.shipping.calls, [])

    def test_exclusive_lease_blocks_unknown_existing_lease_even_when_old(self):
        path = self.folder / ".watcher-admission.json"
        original = b'{"unknown_owner":true,"pid":1}\n'
        path.write_bytes(original)
        os.utime(path, (1, 1))
        lease = self.mod.WatcherLease(str(self.folder))
        blocked = False
        try:
            blocked = lease.acquire() is False
        except (OSError, RuntimeError):
            blocked = True
        self.assertTrue(blocked, "lease age is not evidence that its unknown owner is dead")
        self.assertEqual(path.read_bytes(), original)

    def test_lease_acquire_is_exclusive_and_release_removes_only_own_lease(self):
        path = self.folder / ".watcher-admission.json"
        first = self.mod.WatcherLease(str(self.folder))
        first.acquire()
        self.assertTrue(path.is_file())
        own_bytes = path.read_bytes()
        other = self.mod.WatcherLease(str(self.folder))
        blocked = False
        try:
            blocked = other.acquire() is False
        except (OSError, RuntimeError):
            blocked = True
        self.assertTrue(blocked)
        self.assertEqual(path.read_bytes(), own_bytes)
        first.release()
        self.assertFalse(path.exists())
        first.acquire()
        replacement = b'{"unknown_owner":"a new admission owner"}\n'
        path.write_bytes(replacement)
        first.release()
        self.assertEqual(path.read_bytes(), replacement, "release must not delete another owner's replacement")

    def test_main_once_and_normal_require_admission_before_link_or_editor_work(self):
        path = self.folder / ".watcher-admission.json"
        path.write_text('{"unknown_owner":true}\n', encoding="utf-8")
        for extra in ([], ["--once"]):
            with self.subTest(mode=extra or ["normal"]):
                with mock.patch.object(self.mod.teamlink, "Link", side_effect=AssertionError("link before admission"), create=True) as link, \
                        mock.patch.object(self.mod.wire, "call", side_effect=AssertionError("editor before admission")) as wire:
                    try:
                        result = self.mod.main(["--folder", str(self.folder), *extra])
                    except (OSError, RuntimeError):
                        result = 3
                self.assertNotEqual(result, 0)
                link.assert_not_called()
                wire.assert_not_called()
                self.assertTrue(path.exists())

    def test_main_keyboard_interrupt_releases_lease_unless_producer_is_alive(self):
        for producer_alive in (False, True):
            with self.subTest(producer_alive=producer_alive):
                actions = []

                class FakeLease:
                    def __init__(self, folder):
                        actions.append("lease_construct")

                    def acquire(self):
                        actions.append("acquire")
                        return True

                    def release(self):
                        actions.append("release")

                class FakeWatcher:
                    def __init__(inner, folder, link=None):
                        inner.queue = str(self.queue_file)
                        inner.waiting_on = ""
                        inner._producer = types.SimpleNamespace(is_alive=lambda: producer_alive)

                    def recover(inner):
                        actions.append("recover")
                        return []

                    def tick(inner):
                        actions.append("tick")
                        raise KeyboardInterrupt("offline controlled exit")

                    def event(inner, *args, **kwargs):
                        actions.append("event")

                with mock.patch.object(self.mod, "WatcherLease", FakeLease), \
                        mock.patch.object(self.mod, "Watcher", FakeWatcher):
                    try:
                        self.mod.main(["--folder", str(self.folder), "--no-link"])
                    except KeyboardInterrupt:
                        pass
                self.assertEqual(actions.count("acquire"), 1)
                self.assertLess(actions.index("acquire"), actions.index("recover"))
                self.assertLess(actions.index("acquire"), actions.index("tick"))
                self.assertEqual(actions.count("release"), 0 if producer_alive else 1)

    def test_land_oserror_stops_next_land_and_export_dispatch(self):
        preparing_third = threading.Event()
        release_third = threading.Event()
        failed = threading.Event()
        exported_after_failure = threading.Event()
        exports = []
        lands = []
        assets = ["Prop_Stop_%02d" % i for i in range(8)]

        class FakeShipping:
            def export(inner, asset, *args, **kwargs):
                exports.append((asset, failed.is_set()))
                if failed.is_set():
                    exported_after_failure.set()
                return report(asset)

            def land(inner, value, *args, **kwargs):
                lands.append(value["name"])
                if len(lands) == 1:
                    if not preparing_third.wait(1):
                        raise AssertionError("did not reach the controlled pre-export race")
                    failed.set()
                    raise OSError("offline lost editor transport")
                return value

        watcher = self.mod.Watcher(str(self.folder), ship=FakeShipping(), link=None)

        def prepare(asset):
            if asset == assets[2]:
                preparing_third.set()
                if not release_third.wait(1):
                    raise AssertionError("producer was not released after transport failure")
            return (asset, "Prop", {"objects": [asset], "source": "collection"})

        def block(asset, *args):
            release_third.set()
            # A bad stop order deterministically lets the paused producer dispatch.
            exported_after_failure.wait(0.1)
            return (asset, "BLOCKED")

        watcher.prepare = prepare
        watcher.block = block
        watcher._stage = mock.Mock()  # Fake assets deliberately have no real claims.

        def event(asset, what, **details):
            if what == "error" and failed.is_set():
                release_third.set()
                exported_after_failure.wait(0.1)

        watcher.event = event
        watcher.finish = lambda asset, *args: (asset, "SHIPPED")
        try:
            watcher.ship_overlapped(assets)
            self.assertEqual(lands, [assets[0]])
            self.assertFalse([asset for asset, after_failure in exports if after_failure])
        finally:
            release_third.set()
            producer = getattr(watcher, "_producer", None)
            if producer is not None:
                producer.join(timeout=1)

    def test_consumer_failure_stops_producer_with_full_handoff_queue(self):
        ahead = threading.Event()
        cleanup = threading.Event()
        actual_queue = queue.Queue
        tracked_queues = []
        export_count = 0

        class TrackedQueue(actual_queue):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                tracked_queues.append(self)

            def put(self, item, block=True, timeout=None):
                if timeout is not None or not block:
                    return super().put(item, block, timeout)
                # Preserve blocking behavior, while allowing teardown of a failing
                # legacy candidate so this canary never leaks its daemon thread.
                while not cleanup.is_set():
                    try:
                        return super().put(item, True, 0.02)
                    except queue.Full:
                        pass

        class FakeShipping:
            def export(self, asset, *args, **kwargs):
                nonlocal export_count
                export_count += 1
                if export_count >= 4:
                    ahead.set()
                return report(asset)

            def land(self, value, *args, **kwargs):
                if not ahead.wait(1):
                    raise AssertionError("producer did not exercise the full queue")
                return value

        watcher = self.mod.Watcher(str(self.folder), ship=FakeShipping(), link=None)
        watcher.prepare = lambda asset: (asset, "Prop", {"objects": [asset], "source": "collection"})
        watcher._stage = mock.Mock()  # Isolate lifecycle from durable-claim behavior.
        watcher.finish = mock.Mock(side_effect=RuntimeError("injected publication failure"))
        assets = ["Prop_Cleanup_%02d" % i for i in range(12)]
        old_threads = set(threading.enumerate())
        started = time.monotonic()
        try:
            with mock.patch.object(self.mod._queue, "Queue", TrackedQueue):
                with self.assertRaises(RuntimeError):
                    watcher.ship_overlapped(assets)
            self.assertLess(time.monotonic() - started, 2.5, "cleanup must be bounded")
            self.assertTrue(ahead.is_set())
            self.assertFalse([t for t in threading.enumerate() if t not in old_threads and t.name == "artqueue-blender"],
                             "a failed consumer must not leave its producer alive")
        finally:
            cleanup.set()
            for handoff in tracked_queues:
                while True:
                    try:
                        handoff.get_nowait()
                    except queue.Empty:
                        break
            for thread in threading.enumerate():
                if thread not in old_threads and thread.name == "artqueue-blender":
                    thread.join(timeout=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
