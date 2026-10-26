# SPDX-License-Identifier: MIT
"""Tests for G175 Tidemark Chunks (whole-file vs fixed-size vs content-defined chunking, G86 + G39 tie-ins)."""
import copy
import dataclasses
import io
import json
import os
import random
import sys
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tidemark_chunks as tc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "tidemark-chunks-v1.json")
SHOALS = os.path.join(ROOT, "data", "islands", "disk-saver", "compaction-shoals-v1.json")
SPRING = os.path.join(ROOT, "data", "islands", "disk-saver", "byte-spring-v1.json")
SEEDS = (175, 1, 2, 3, 4)
GOLDEN_HASH = 1979599321
GOLDEN_SIZES = [246, 107, 160, 93, 81, 229, 53, 213, 379, 33, 78, 36, 255, 93, 184, 246, 43, 136, 169, 268, 193, 138, 190, 64, 74, 102, 215, 18]
GOLDEN_COST = 39197


def load():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


def cfg(seed=None, **over):
    raw = load()
    if seed is not None:
        raw["seed"] = seed
    raw["chunks"].update(over)
    return tc.validate(raw)


def blob(seed, n):
    rng = random.Random(seed)
    return bytes(rng.randrange(256) for _ in range(n))


class TestTidemarkChunks(unittest.TestCase):
    def test_shipped_cdc_wins_others_fail(self):
        for s in SEEDS:
            c = cfg(s)
            self.assertEqual(tc.run(c, "cdc").status, tc.WON, s)
            for m in ("whole", "fixed"):
                r = tc.run(c, m)
                self.assertEqual((r.status, r.reason), (tc.FAILED, tc.FAIL_QUOTA), (s, m))

    def test_cost_order_cdc_lt_fixed_lt_whole(self):
        for s in SEEDS:
            c = cfg(s)
            w, f, d = (tc.run(c, m).cost for m in ("whole", "fixed", "cdc"))
            self.assertLess(d, f, s)
            self.assertLess(f, w, s)

    def test_rolling_hash_equals_from_scratch(self):
        for w in (2, 5, 16, 48):
            data = blob(w, 600)
            got = list(tc.rolling_hashes(data, w))
            self.assertEqual(len(got), len(data) - w + 1)
            for i, h in got:
                self.assertEqual(h, tc.window_hash(data[i - w + 1:i + 1]), (w, i))

    def test_chunks_rebuild_and_respect_limits(self):
        c = cfg()
        for n in (0, 1, 31, 32, 1000, 5000):
            data = blob(n, n)
            for m in tc.MODES:
                ch = tc.chunk(data, c, m)
                self.assertEqual(b"".join(ch), data, (n, m))
            cd = tc.chunk(data, c, "cdc")
            self.assertTrue(all(len(x) <= c.max_chunk for x in cd))
            self.assertTrue(all(len(x) >= c.min_chunk for x in cd[:-1]))
            self.assertTrue(all(len(x) == c.fixed_size for x in tc.chunk(data, c, "fixed")[:-1]))

    def test_cdc_cuts_depend_only_on_content(self):
        # the same 3 KiB after different prefixes ends in the same chunks once the cuts resync
        c = cfg()
        body = blob(7, 3000)
        a = tc.chunk(blob(8, 400) + body, c, "cdc")
        b = tc.chunk(blob(9, 77) + body, c, "cdc")
        tail = set(a[-5:])
        self.assertEqual(tail, set(b[-5:]))

    def test_front_insert_boundary_shift(self):
        c = cfg()
        for s in SEEDS:
            old = blob(s, 8000)
            new = b"\x2a" + old
            fs, fn = tc.shared_after_edit(old, new, c, "fixed")
            ds, dn = tc.shared_after_edit(old, new, c, "cdc")
            self.assertLessEqual(fs, 1, s)            # every fixed boundary moved by one byte
            self.assertGreaterEqual(ds * 10, dn * 9, s)  # >= 90% of CDC chunks already stored
            self.assertLessEqual(dn - ds, 2, s)       # at most two new chunks around the edit

    def test_mid_insert_fixed_keeps_only_prefix(self):
        c = cfg()
        old = blob(3, 8000)
        pos = 4000
        new = old[:pos] + b"\x00" + old[pos:]
        fs, _ = tc.shared_after_edit(old, new, c, "fixed")
        self.assertEqual(fs, pos // c.fixed_size)

    def test_mean_cdc_chunk_matches_monte_carlo(self):
        for bits, mn in ((6, 16), (7, 32), (8, 8)):
            sizes = []
            for s in range(4):
                sizes += [len(x) for x in tc.chunk_cdc(blob(100 + s, 60000), 16, bits, mn, 1 << 20)[:-1]]
            mean = sum(sizes) / len(sizes)
            expect = mn - 1 + (1 << bits)
            self.assertLess(abs(mean - expect), 0.1 * expect, (bits, mn, mean))

    def test_vault_cost_equals_oracle(self):
        for s in SEEDS[:3]:
            c = cfg(s, versions=5)
            hist = tc.saves(c)
            for m in tc.MODES:
                rec = [tc.chunk(sv, c, m) for ver in hist for sv in ver]
                self.assertEqual(tc.vault_cost(rec, c.ref_bytes)[3], tc.cost_oracle(rec, c.ref_bytes), (s, m))
                self.assertEqual(tc.run(c, m).cost, tc.cost_oracle(rec, c.ref_bytes), (s, m))

    def test_no_edits_store_once(self):
        c = cfg(edits=0)
        for m in tc.MODES:
            r = tc.run(c, m)
            one = tc.run(dataclasses.replace(c, versions=1), m)
            self.assertEqual(r.stored_bytes, one.stored_bytes, m)
            self.assertEqual(r.stored_bytes, r.raw_bytes // r.versions, m)

    def test_seeded_replay_determinism(self):
        for s in SEEDS:
            a = [tc.receipt(cfg(s), tc.run(cfg(s), m)) for m in tc.MODES]
            b = [tc.receipt(cfg(s), tc.run(cfg(s), m)) for m in tc.MODES]
            self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
            self.assertEqual(tc.saves(cfg(s)), tc.saves(cfg(s)))
        self.assertNotEqual(tc.saves(cfg(1)), tc.saves(cfg(2)))

    def test_g86_and_g39_tie_ins(self):
        with open(SHOALS, encoding="utf-8") as fh:
            isl = json.load(fh)["islands"]
        with open(SPRING, encoding="utf-8") as fh:
            cap = json.load(fh)["cistern"]["budget_cap"]
        c = cfg()
        self.assertEqual([(i.id, i.weight) for i in c.islands], [(i["id"], i["weight"]) for i in isl])
        self.assertEqual([len(b) for b in tc.saves(c)[0]], [i["weight"] * c.bytes_per_weight for i in isl])
        self.assertEqual(c.quota, cap * c.byte_unit)

    def test_locked_chunker_constants(self):
        self.assertEqual((tc.BASE, tc.PRIME, tc.WINDOW, tc.MASK_BITS), (257, 2_147_483_647, 16, 7))
        c = cfg()
        self.assertEqual((c.window, c.mask_bits), (tc.WINDOW, tc.MASK_BITS))
        for over in ({"window": 17}, {"mask_bits": 8}):
            raw = load()
            raw["chunks"].update(over)
            with self.assertRaises(tc.ChunkError):
                tc.validate(raw)

    def test_golden_fixture(self):
        # CI fails if the chunker drifts: hash of a fixed window and CDC cut sizes of a fixed blob
        self.assertEqual(tc.window_hash(b"tidemark chunks!"), GOLDEN_HASH)
        sizes = [len(x) for x in tc.chunk_cdc(blob(175, 4096), tc.WINDOW, tc.MASK_BITS, 32, 1024)]
        self.assertEqual(sizes, GOLDEN_SIZES)
        self.assertEqual(tc.receipt(cfg(), tc.run(cfg()))["cost"], GOLDEN_COST)

    def test_validate_rejects_bad_config(self):
        for mut in (lambda r: r.update(v=2), lambda r: r["chunks"].update(mode="hope"),
                    lambda r: r["chunks"].update(max_chunk=8), lambda r: r["chunks"].pop("window"),
                    lambda r: r["npc"]["lines"].pop("win"), lambda r: r.update(extra=1),
                    lambda r: r["chunks"].update(versions=True),
                    lambda r: r["chunks"].update(delete_permille=700)):
            raw = copy.deepcopy(load())
            mut(raw)
            with self.assertRaises(tc.ChunkError):
                tc.validate(raw)

    def test_receipt_and_npc(self):
        c = cfg()
        rc = tc.receipt(c, tc.run(c))
        self.assertEqual(rc["quest"], tc.QUEST_ID)
        self.assertEqual(rc["status"], tc.WON)
        self.assertTrue(tc.npc_say(c, "win").startswith("Tallyman Oro: "))

    def test_cli(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(tc.main([DATA]), 0)
            self.assertEqual(tc.main([DATA, "--mode", "fixed"]), 1)
        self.assertIn('"mode": "cdc"', buf.getvalue())


if __name__ == "__main__":
    unittest.main()
