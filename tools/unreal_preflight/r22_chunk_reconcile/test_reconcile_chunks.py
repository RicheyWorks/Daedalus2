# SPDX-License-Identifier: MIT
"""Synthetic tests for the PROPOSED R22 chunk reconciliation checker. No live files are read."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import reconcile_chunks as rc


def ledger(last=314, per_chunk=10, first_start=101, deadline="2026-10-27T18:40:05.709034+00:00"):
    """Synthetic R22 ledger: chunk 1 starts at 101 (after the historical 100-per-kind prefix)."""
    chunks, lo = [], first_start
    for n in range(1, last + 1):
        chunks.append({"chunk": n, "range": [lo, lo + per_chunk - 1], "receipt": "C:/x/NativeReceipts/Chunk%04d.json" % n})
        lo += per_chunk
    end = chunks[-1]["range"][1]
    return {"saved_counts": {"skull": end, "toter": end}, "source_counts": {"skull": end, "toter": end},
            "next_index": end + 1, "completed_chunks": chunks, "last_native_receipt": chunks[-1]["receipt"],
            "campaign_deadline_utc": deadline}


def extend(before, sizes, deadline="2026-10-28T23:00:00+00:00"):
    after = copy.deepcopy(before)
    for size in sizes:
        last = after["completed_chunks"][-1]
        n, lo = last["chunk"] + 1, last["range"][1] + 1
        after["completed_chunks"].append({"chunk": n, "range": [lo, lo + size - 1], "receipt": "C:/x/NativeReceipts/Chunk%04d.json" % n})
    end = after["completed_chunks"][-1]["range"][1]
    after.update(saved_counts={"skull": end, "toter": end}, source_counts={"skull": end, "toter": end}, next_index=end + 1,
                 last_native_receipt=after["completed_chunks"][-1]["receipt"], campaign_deadline_utc=deadline)
    return after


class Before(unittest.TestCase):
    def test_current_shape_314_3240_3241_is_consistent(self):
        b = ledger()
        self.assertEqual(b["completed_chunks"][-1]["range"], [3231, 3240])
        self.assertEqual(rc.check_before(b), [])

    def test_rolled_back_ledger_refused(self):
        # e.g. someone restores before-ledger.json (a session-start snapshot) as the live ledger
        self.assertTrue(rc.check_before(ledger(last=198)))

    def test_source_ahead_or_stale_next_index_refused(self):
        b = ledger()
        b["source_counts"] = {"skull": 3250, "toter": 3250}
        self.assertTrue(any("counts" in r for r in rc.check_before(b)))
        b = ledger()
        b["next_index"] = 3231  # would replay chunk 314
        self.assertTrue(any("next_index" in r for r in rc.check_before(b)))


class Across(unittest.TestCase):
    def test_clean_continuation_at_3241_passes(self):
        b = ledger()
        self.assertEqual(rc.check_across(b, extend(b, [20, 20])), [])

    def test_replayed_chunk_314_is_double_count(self):
        b = ledger()
        a = copy.deepcopy(b)
        a["completed_chunks"].append({"chunk": 315, "range": [3231, 3250], "receipt": "C:/x/NativeReceipts/Chunk0315.json"})
        a.update(saved_counts={"skull": 3250, "toter": 3250}, source_counts={"skull": 3250, "toter": 3250}, next_index=3251,
                 campaign_deadline_utc="new")
        reasons = rc.check_across(b, a)
        self.assertTrue(any("double count" in r or "counted in chunks" in r for r in reasons))

    def test_gap_is_loss(self):
        b = ledger()
        a = extend(b, [20])
        a["completed_chunks"][-1]["range"] = [3251, 3270]
        self.assertTrue(any("loss" in r or "starts at" in r for r in rc.check_across(b, a)))

    def test_rewritten_history_is_loss(self):
        b = ledger()
        a = extend(b, [20])
        a["completed_chunks"][313]["receipt"] = "C:/x/NativeReceipts/Chunk0314-redo.json"
        self.assertTrue(any("changed or truncated" in r for r in rc.check_across(b, a)))

    def test_counts_must_equal_ranges(self):
        b = ledger()
        a = extend(b, [20])
        a["saved_counts"] = {"skull": 3280, "toter": 3280}
        self.assertTrue(any("saved_counts" in r for r in rc.check_across(b, a)))

    def test_old_deadline_reused_for_new_chunks_refused(self):
        b = ledger()
        a = extend(b, [20], deadline=b["campaign_deadline_utc"])
        self.assertTrue(any("deadline" in r for r in rc.check_across(b, a)))

    def test_same_receipt_for_two_chunks_refused(self):
        b = ledger()
        a = extend(b, [20])
        a["completed_chunks"][-1]["receipt"] = b["completed_chunks"][-1]["receipt"]
        self.assertTrue(any("more than one chunk" in r for r in rc.check_across(b, a)))


class Session(unittest.TestCase):
    def test_failed_session_shape(self):
        ok = ["session.json", "failure.json", "adopted-current-state-r10.json", "before-ledger.json"]
        self.assertEqual(rc.check_session(ok), [])
        self.assertTrue(rc.check_session(ok + ["normal-lease-release.json"]))
        self.assertTrue(rc.check_session(ok + ["released-producer-lock.json"]))
        self.assertTrue(rc.check_session(["session.json"]))


class Cli(unittest.TestCase):
    def test_cli_reads_only_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            b, a = tmp / "before.json", tmp / "after.json"
            b.write_text(json.dumps(ledger()), encoding="utf-8")
            a.write_text(json.dumps(extend(ledger(), [20])), encoding="utf-8")
            snap = {p.name: p.read_bytes() for p in tmp.iterdir()}
            self.assertEqual(rc.main(["before", "--ledger", str(b)]), 0)
            self.assertEqual(rc.main(["across", "--before", str(b), "--after", str(a)]), 0)
            self.assertEqual(rc.main(["across", "--before", str(a), "--after", str(b)]), 1)
            self.assertEqual(rc.main(["before", "--ledger", str(tmp / "missing.json")]), 2)
            self.assertEqual(snap, {p.name: p.read_bytes() for p in tmp.iterdir()})


if __name__ == "__main__":
    unittest.main()