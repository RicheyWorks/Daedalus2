# SPDX-License-Identifier: MIT
"""Tests for G171 Lighthouse Leases (no lease vs naive vs drift guard vs fencing tokens, G86 tie-in)."""
import copy
import dataclasses
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lighthouse_leases as ll  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "lighthouse-leases-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")
SEEDS = (171, 1, 2, 3, 4)


def load():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


def cfg(seed=None, **over):
    raw = load()
    if seed is not None:
        raw["seed"] = seed
    raw["leases"].update(over)
    return ll.validate(raw)


class TestLighthouseLeases(unittest.TestCase):
    def test_shipped_fenced_wins(self):
        r = ll.run(cfg())
        self.assertEqual(r.status, ll.WON)
        self.assertGreater(r.rejected, 0)

    def test_none_and_naive_fail_on_every_seed(self):
        for s in SEEDS:
            for m in ("none", "naive"):
                r = ll.run(cfg(s), m)
                self.assertEqual(r.status, ll.FAILED, (s, m))
                self.assertEqual(r.reason, ll.FAIL_STALE)

    def test_guard_fails_with_pauses_fenced_wins(self):
        for s in SEEDS:
            self.assertGreater(ll.run(cfg(s), "guard").stale_accepted, 0, s)
            r = ll.run(cfg(s), "fenced")
            self.assertEqual(r.stale_accepted, 0, s)
            # fencing turns away exactly what the guard alone let through
            self.assertEqual(r.rejected, ll.run(cfg(s), "guard").stale_accepted, s)

    def test_drift_bound_equals_brute_force(self):
        for lease in (2, 7, 20, 64):
            for d in (0, 1, 50, 150, 333, 500):
                brute = next(g for g in range(lease + 1)
                             if all(e < lease for e in range(lease * 3)
                                    if ll.local_elapsed(e, -d) < lease - g))
                self.assertEqual(ll.drift_bound(lease, d), brute, (lease, d))

    def test_no_pause_guard_at_bound_zero_overlap(self):
        c = cfg(pause_permille=0)
        g = ll.drift_bound(c.lease, c.max_drift_permille)
        for s in SEEDS:
            r = ll.run(dataclasses.replace(c, seed=s, guard=g), "guard")
            self.assertEqual((r.stale_accepted, r.outside_lease), (0, 0), s)

    def test_no_pause_guard_below_bound_can_overrun(self):
        c = cfg(pause_permille=0, max_drift_permille=300)
        g = ll.drift_bound(c.lease, c.max_drift_permille)
        overruns = sum(ll.run(dataclasses.replace(c, seed=s, guard=0), "guard").outside_lease for s in SEEDS)
        self.assertGreater(g, 0)
        self.assertGreater(overruns, 0)

    def test_perfect_clocks_naive_wins(self):
        for s in SEEDS:
            r = ll.run(cfg(s, pause_permille=0, max_drift_permille=0), "naive")
            self.assertEqual(r.status, ll.WON, s)

    def test_stale_count_equals_oracle(self):
        for s in SEEDS:
            for m in ll.MODES:
                r = ll.run(cfg(s), m)
                self.assertEqual(r.stale_accepted, ll.stale_oracle(r.log), (s, m))

    def test_fenced_log_tokens_never_go_down(self):
        for s in SEEDS:
            toks = [w.token for w, ok in ll.run(cfg(s), "fenced").log if ok]
            self.assertEqual(toks, sorted(toks), s)

    def test_seeded_replay_determinism(self):
        for s in SEEDS:
            a = [ll.receipt(cfg(s), ll.run(cfg(s), m)) for m in ll.MODES]
            b = [ll.receipt(cfg(s), ll.run(cfg(s), m)) for m in ll.MODES]
            self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
            self.assertEqual([w for w, _ in ll.run(cfg(s)).log], [w for w, _ in ll.run(cfg(s)).log])

    def test_g86_tie_in_keepers(self):
        with open(SHOALS, encoding="utf-8") as fh:
            ids = [i["id"] for i in json.load(fh)["islands"]]
        self.assertEqual(list(cfg().keepers), ids)
        self.assertEqual({w.keeper for w, _ in ll.run(cfg()).log} <= set(range(len(ids))), True)

    def test_validate_rejects_bad_config(self):
        for mut in (lambda r: r.update(v=2), lambda r: r["leases"].update(mode="hope"),
                    lambda r: r["leases"].update(guard=20), lambda r: r["leases"].pop("lease"),
                    lambda r: r["npc"]["lines"].pop("win"), lambda r: r.update(extra=1),
                    lambda r: r["leases"].update(epochs=True)):
            raw = copy.deepcopy(load())
            mut(raw)
            with self.assertRaises(ll.LeaseError):
                ll.validate(raw)

    def test_receipt_and_npc(self):
        c = cfg()
        rc = ll.receipt(c, ll.run(c))
        self.assertEqual(rc["quest"], ll.QUEST_ID)
        self.assertEqual(rc["status"], ll.WON)
        self.assertTrue(ll.npc_say(c, "win").startswith("Keeper Ines: "))

    def test_cli(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(ll.main([DATA]), 0)
            self.assertEqual(ll.main([DATA, "--mode", "naive"]), 1)
        self.assertIn('"stale_accepted": 0', buf.getvalue())


if __name__ == "__main__":
    unittest.main()
