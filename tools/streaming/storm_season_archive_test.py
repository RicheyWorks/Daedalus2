# SPDX-License-Identifier: MIT
"""Tests for G136 The Storm Season Archive."""
import copy
import hashlib
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import storm_season_archive as s  # noqa: E402

DD = os.path.join(ROOT, "data", "islands", "disk-saver")
DATA = os.path.join(DD, "storm-season-archive-v1.json")
SHOALS = os.path.join(DD, "compaction-shoals-v1.json")


def raw():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


def landed_files():
    out = []
    for gap, mod, data, _ in s.ACTS.values():
        out += [os.path.join(HERE, mod + ".py"), os.path.join(DD, data)]
    return out


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = s.validate(raw())
        cls.gold = s.play(cls.c)


class ValidateTest(unittest.TestCase):
    def test_shipped_config_valid(self):
        c = s.validate(raw())
        self.assertEqual(c.npc_name, "Archivist Maren")
        self.assertEqual(tuple(a.id for a in c.acts), s.ACT_ORDER)
        self.assertEqual(sum(a.stake for a in c.acts), 1200)

    def test_rejects_bad_configs(self):
        for mut in (lambda d: d.update(v=2), lambda d: d.update(extra=1),
                    lambda d: d.update(quest="q_other"),
                    lambda d: d["season"].update(pass_permille=1001),
                    lambda d: d["season"].pop("session_id"),
                    lambda d: d["acts"].reverse(),
                    lambda d: d["acts"].pop(),
                    lambda d: d["acts"][0].update(stake=900),
                    lambda d: d["acts"][1].update(stake=True),
                    lambda d: d["keeper"].update(kind="NPC"),
                    lambda d: d["islands"].append({"id": "cache_north"}),
                    lambda d: d["npc"]["lines"].pop("audit")):
            d = raw()
            mut(d)
            with self.assertRaises(s.ArchiveError):
                s.validate(d)


class ActsTest(Base):
    def test_acts_are_the_landed_games(self):
        self.assertEqual([s.ACTS[a][0] for a in s.ACT_ORDER],
                         ["G99", "G105", "G110", "G113", "G120", "G123", "G126"])
        for r in self.gold.records:
            self.assertEqual(r["quest"], "q_" + r["act"])

    def test_every_trap_loses_its_act(self):
        for act in s.ACT_ORDER:
            self.assertEqual(s.run_act(act, s.TUNED)["status"], "won", act)
            rec = s.run_act(act, s.TRAP)
            self.assertEqual(rec["status"], "failed", act)
            self.assertTrue(rec["reason"], act)

    def test_landed_games_read_only(self):
        before = {p: sha(p) for p in landed_files()}
        s.play(self.c, s.ACT_ORDER)
        self.assertEqual(before, {p: sha(p) for p in landed_files()})
        with self.assertRaises(s.ArchiveError):
            s.run_act("lifeboat_drift", s.TUNED)


class AuditTest(Base):
    def test_all_tuned_is_gold(self):
        a = s.audit(self.c, self.gold)
        self.assertEqual((a.grade, a.acts_won, a.lost, a.survived_permille), (s.GOLD, 7, 0, 1000))
        self.assertTrue(a.chain_ok and a.accounted)

    def test_one_trap_passes_two_fail(self):
        a = s.audit(self.c, s.play(self.c, ["quorum_quays"]))
        self.assertEqual((a.grade, a.lost, a.survived), (s.PASS, 180, 1020))
        self.assertEqual(a.lost_by_act["quorum_quays"], 180)
        b = s.audit(self.c, s.play(self.c, ["quorum_quays", "breakwater_queue"]))
        self.assertEqual((b.grade, b.lost, b.survived_permille), (s.FAIL, 340, 716))

    def test_deal_is_disjoint_and_complete(self):
        stakes, harbour = s.deal(self.c)
        flat = [k for ks in stakes.values() for k in ks] + harbour
        self.assertEqual(len(flat), len(set(flat)))
        self.assertEqual(sorted(flat), sorted(s.keys_for(self.c)))
        self.assertEqual([len(stakes[a.id]) for a in self.c.acts], [a.stake for a in self.c.acts])

    def test_tampered_act_breaks_chain(self):
        bad = copy.deepcopy(self.gold)
        trapped = s.play(self.c, ["snapshot_shells"])
        bad.records[3] = dict(trapped.records[3], status="won", reason=None)  # rewrite a lost act
        self.assertFalse(s.verify_chain(bad.records, bad.chain))
        a = s.audit(self.c, bad)
        self.assertEqual((a.chain_ok, a.grade), (False, s.FAIL))
        swapped = copy.deepcopy(self.gold)
        swapped.records[0], swapped.records[1] = swapped.records[1], swapped.records[0]
        self.assertFalse(s.verify_chain(swapped.records, swapped.chain))

    def test_chain_links_every_act(self):
        self.assertEqual(len(self.gold.chain), 7)
        self.assertTrue(s.verify_chain(self.gold.records, self.gold.chain))
        self.assertNotEqual(s.play(self.c, ["garbage_gulls"]).chain[-1], self.gold.chain[-1])
        self.assertEqual(s.play(self.c, ["garbage_gulls"]).chain[:4], self.gold.chain[:4])


class ReceiptTest(Base):
    def test_g12_wire_order_and_outcome(self):
        rc = s.g12_receipt(self.c, self.gold, s.audit(self.c, self.gold))
        self.assertEqual(list(rc), ["schema", "resultId", "sessionId", "activityId", "definitionRevision",
                                    "mode", "issuer", "verificationRef", "outcome", "participants",
                                    "measures", "sourceEventRefs", "clockBoundaryMs"])
        self.assertEqual((rc["schema"], rc["outcome"], rc["mode"]), ("activity-result-v1", "COMPLETED", "AUTHORITATIVE"))
        self.assertEqual(rc["measures"], {"acts_won": 7, "saves_lost": 0, "saves_survived": 1200,
                                          "survived_permille": 1000})
        self.assertEqual(len(rc["sourceEventRefs"]), 7)
        failed = s.play(self.c, ["bloom_buoys", "prefetch_pelicans"])
        self.assertEqual(s.g12_receipt(self.c, failed, s.audit(self.c, failed))["outcome"], "FAILED")

    def test_digest_deterministic(self):
        rc = s.g12_receipt(self.c, self.gold, s.audit(self.c, self.gold))
        self.assertEqual(s.receipt_digest(rc), hashlib.sha256(s.receipt_json(rc).encode()).hexdigest())
        again = s.play(self.c)
        self.assertEqual(s.receipt_digest(s.g12_receipt(self.c, again, s.audit(self.c, again))),
                         s.receipt_digest(rc))


class TieInTest(unittest.TestCase):
    def test_islands_and_keys_match_g86(self):
        with open(SHOALS, encoding="utf-8") as fh:
            isl, kpi = s.islands_from_shoals(json.load(fh))
        c = s.validate(raw())
        self.assertEqual(tuple(i["id"] for i in isl), c.islands)
        self.assertEqual(kpi, c.keys_per_island)


class CliTest(unittest.TestCase):
    def test_cli_grades(self):
        self.assertEqual(s.main([DATA]), 0)
        self.assertEqual(s.main([DATA, "--trap", "hash_ring_atolls"]), 0)
        self.assertEqual(s.main([DATA, "--trap", "hash_ring_atolls", "--trap", "garbage_gulls"]), 1)


if __name__ == "__main__":
    unittest.main()
