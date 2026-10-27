# SPDX-License-Identifier: MIT
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_closeout as v  # noqa: E402

DEAD = lambda pid: {"state": "absent", "start_utc": None}  # noqa: E731
MINE = lambda broker: {"unreal": {"holder": "boss", "left_s": 9000}, "compute": {"holder": "boss", "left_s": 9000}}  # noqa: E731


def w(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj), encoding="utf-8")


class Fixture:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="closeout-"))
        self.camp = self.root / "camp"
        self.runs = self.root / "runs"
        self.sess = self.runs / "r22-x"
        self.out = self.root / "scratch" / "att.json"
        self.out.parent.mkdir(parents=True)
        rec = self.camp / "NativeReceipts" / "Chunk0003.json"
        world = "/Game/X/R18_C0003/L_C0003"
        chunks = [{"chunk": 1, "range": [101, 110], "receipt": "a"}, {"chunk": 2, "range": [111, 120], "receipt": "b"},
                  {"chunk": 3, "range": [121, 130], "receipt": str(rec)}]
        counts = {"skull": 130, "toter": 130}
        w(self.camp / "ledger.json", {"saved_counts": counts, "source_counts": dict(counts), "completed_chunks": chunks,
                                      "next_index": 131, "last_native_receipt": str(rec), "last_world": world})
        items = {"%s%d" % (k, i): {"source": {"kind": k, "index": i}} for k in v.KINDS for i in range(121, 131)}
        w(rec, {"native": {"world": world + ".L_C0003", "saved": True, "dirty": {"maps": [], "content": []},
                           "play": False, "open_sequence": "None", "import_active": False, "item_records": items}})
        fail = {"stage": "blocked", "owner_pid": 4242, "lease_owner": "boss",
                "error": "<urlopen error [WinError 10061] No connection could be made because the target machine actively refused it>",
                "r22_session": str(self.sess)}
        w(self.camp / "owner.json", {"pid": 4242, "lease_owner": "boss", "r22_session": str(self.sess)})
        w(self.camp / "active-status.json", fail)
        w(self.camp / "owner-terminal.json", {"pid": 4242, "status": fail})
        w(self.sess / "failure.json", fail)
        w(self.sess / "session.json", {"started_utc": "2026-10-26T18:40:05+00:00"})
        w(self.runs / "active-owner.lock", {"pid": 4242, "owner": "boss", "session": str(self.sess)})

    def attest(self, **kw):
        kw.setdefault("process", DEAD)
        kw.setdefault("locks", MINE)
        return v.attest(self.camp, self.sess, self.out, **kw)

    def close(self):
        shutil.rmtree(self.root)


class Tests(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()

    def tearDown(self):
        self.f.close()

    def snapshot(self):
        return {str(p): p.read_bytes() for p in self.f.root.rglob("*") if p.is_file() and p != self.f.out}

    def test_clean_release_failure_is_admissible_and_check_passes(self):
        reasons, doc = self.f.attest()
        self.assertEqual(reasons, [])
        self.assertTrue(doc["admissible"])
        self.assertEqual(doc["facts"]["next_index"], 131)
        self.assertEqual(v.check(self.f.out, process=DEAD, locks=MINE), [])

    def test_read_only_except_the_attestation(self):
        before = self.snapshot()
        self.f.attest()
        v.check(self.f.out, process=DEAD, locks=MINE)
        self.assertEqual(before, self.snapshot())

    def test_refuses_to_write_inside_campaign_or_runs(self):
        for bad in (self.f.camp / "att.json", self.f.runs / "att.json", self.f.sess / "att.json"):
            reasons, doc = v.attest(self.f.camp, self.f.sess, bad, process=DEAD, locks=MINE)
            self.assertIsNone(doc)
            self.assertFalse(bad.exists())

    def test_flipped_byte_after_attest_is_refused(self):
        self.f.attest()
        rec = self.f.camp / "NativeReceipts" / "Chunk0003.json"
        raw = bytearray(rec.read_bytes())
        raw[-2] = ord(" ") if raw[-2] != ord(" ") else ord("\n")
        rec.write_bytes(bytes(raw))
        self.assertTrue(any("pinned input changed: native" in r for r in v.check(self.f.out, process=DEAD, locks=MINE)))

    def test_tampered_attestation_body_is_refused(self):
        self.f.attest()
        doc = json.loads(self.f.out.read_text())
        doc["facts"]["next_index"] = 999
        self.f.out.write_text(json.dumps(doc))
        self.assertEqual(v.check(self.f.out, process=DEAD, locks=MINE), ["attestation body hash differs"])

    def test_live_owner_is_refused(self):
        live = lambda pid: {"state": "running", "start_utc": "2026-10-26T10:00:00+00:00"}  # noqa: E731
        reasons, _ = self.f.attest(process=live)
        self.assertTrue(any("still running" in r for r in reasons))
        unknown = lambda pid: {"state": "running", "start_utc": None}  # noqa: E731
        self.assertTrue(any("still running" in r for r in self.f.attest(process=unknown)[0]))

    def test_pid_reused_after_session_is_not_the_owner(self):
        reused = lambda pid: {"state": "running", "start_utc": "2026-10-27T19:00:00+00:00"}  # noqa: E731
        reasons, doc = self.f.attest(process=reused)
        self.assertEqual(reasons, [])
        self.assertTrue(doc["facts"]["pid_reused_after_session"])

    def test_owner_coming_back_alive_after_attest_is_refused_by_check(self):
        self.f.attest()
        live = lambda pid: {"state": "running", "start_utc": None}  # noqa: E731
        self.assertTrue(any("still running" in r for r in v.check(self.f.out, process=live, locks=MINE)))

    def test_foreign_lease_and_broker_down_refuse(self):
        foreign = lambda b: {"unreal": {"holder": "someone", "left_s": 5}}  # noqa: E731
        self.assertTrue(any("foreign" in r for r in self.f.attest(locks=foreign)[0]))

        def down(b):
            raise OSError("refused")
        self.assertTrue(any("broker unreadable" in r for r in self.f.attest(locks=down)[0]))

    def test_non_release_failure_is_refused(self):
        p = self.f.sess / "failure.json"
        j = json.loads(p.read_text())
        j["error"] = "native save failed"
        for q in (p, self.f.camp / "active-status.json"):
            w(q, j)
        w(self.f.camp / "owner-terminal.json", {"pid": 4242, "status": j})
        self.assertTrue(any("not a broker-connection" in r for r in self.f.attest()[0]))

    def test_source_ahead_or_count_mismatch_is_refused(self):
        p = self.f.camp / "ledger.json"
        j = json.loads(p.read_text())
        j["source_counts"]["skull"] = 140
        w(p, j)
        self.assertTrue(any("counts disagree" in r for r in self.f.attest()[0]))

    def test_work_past_ledger_is_refused(self):
        (self.f.camp / "SourceChunks" / "Chunk0004").mkdir(parents=True)
        self.assertTrue(any("past the ledger" in r for r in self.f.attest()[0]))

    def test_dirty_native_or_short_item_range_is_refused(self):
        rec = self.f.camp / "NativeReceipts" / "Chunk0003.json"
        j = json.loads(rec.read_text())
        j["native"]["dirty"]["maps"] = ["/Game/X"]
        j["native"]["item_records"].pop("skull121")
        w(rec, j)
        reasons = self.f.attest()[0]
        self.assertTrue(any("saved clean" in r for r in reasons))
        self.assertTrue(any("cover exactly" in r for r in reasons))

    def test_lock_naming_another_producer_is_refused(self):
        w(self.f.runs / "active-owner.lock", {"pid": 1, "owner": "boss", "session": str(self.f.sess)})
        self.assertTrue(any("coordinator lock" in r for r in self.f.attest()[0]))

    def test_cli_exit_codes(self):
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(v.main(["check", "--attestation", str(self.f.root / "nope.json")]), 2)


if __name__ == "__main__":
    unittest.main()
