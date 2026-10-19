# SPDX-License-Identifier: MIT
"""G39 Byte Spring tests. Run: python -m unittest tools/streaming/byte_spring_test.py -v"""
import copy
import hashlib
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import byte_spring as bs  # noqa: E402
import dsb  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data", "islands", "disk-saver", "byte-spring-v1.json")
MANIFEST = os.path.join(ROOT, "data", "islands", "streaming.dsb")


def tiny_cfg(**over):
    base = {
        "v": 1,
        "cistern": {"capacity": 1000, "level": 500, "spring_fill": 350, "leak": 50, "budget_cap": 400},
        "islands": [
            {"id": "cache_a", "cost_kib": 100, "priority": 1},
            {"id": "cache_b", "cost_kib": 200, "priority": 0},
            {"id": "vault", "cost_kib": 250, "priority": 2},
        ],
        "start_residents": ["cache_a", "cache_b"],
        "drought_limit": 3,
        "win_ticks": 5,
    }
    base.update(over)
    return base


def cistern(**over):
    c = dict(tiny_cfg()["cistern"])
    c.update(over)
    return c


def fixture():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


class ValidateTest(unittest.TestCase):
    def bad(self, cfg, msg=None):
        with self.assertRaises(bs.ByteSpringError) as cm:
            bs.validate(cfg)
        if msg:
            self.assertIn(msg, str(cm.exception))

    def test_ok(self):
        c = bs.validate(tiny_cfg())
        self.assertEqual((c.capacity, c.level, c.drought_limit, c.win_ticks), (1000, 500, 3, 5))
        self.assertEqual([i.id for i in c.islands], ["cache_a", "cache_b", "vault"])
        self.assertEqual(c.npc_name, "Spigot")  # default NPC
        self.assertEqual(set(c.npc_lines), set(bs.NPC_KEYS))

    def test_does_not_mutate_input(self):
        cfg = tiny_cfg()
        before = copy.deepcopy(cfg)
        bs.simulate(cfg, [True, False] * 5)
        self.assertEqual(cfg, before)

    def test_version(self):
        self.bad(dict(tiny_cfg(), v=2), "version")
        self.bad(dict(tiny_cfg(), v=True), "version")  # True == 1 in Python
        cfg = tiny_cfg()
        del cfg["v"]
        self.bad(cfg, "version")

    def test_not_an_object(self):
        self.bad([], "object")
        self.bad(None, "object")

    def test_bool_is_not_int(self):
        self.bad(tiny_cfg(cistern=cistern(capacity=True)), "integer")
        self.bad(tiny_cfg(drought_limit=True), "integer")

    def test_ranges(self):
        self.bad(tiny_cfg(cistern=cistern(capacity=0)), "capacity")
        self.bad(tiny_cfg(cistern=cistern(level=-1)), "level")
        self.bad(tiny_cfg(cistern=cistern(level=1001)), "level")
        self.bad(tiny_cfg(cistern=cistern(leak=bs.MAX_UNITS + 1)), "leak")
        self.bad(tiny_cfg(cistern=cistern(spring_fill=1.5)), "integer")
        self.bad(tiny_cfg(drought_limit=0), "drought_limit")
        self.bad(tiny_cfg(win_ticks=0), "win_ticks")
        self.bad(tiny_cfg(dry_permille=1001), "dry_permille")

    def test_unknown_keys(self):
        self.bad(dict(tiny_cfg(), wintick=3), "unknown key")
        self.bad(tiny_cfg(cistern=dict(cistern(), cap=1)), "unknown cistern key")
        self.bad(tiny_cfg(islands=[{"id": "a", "cost_kib": 1, "pri": 1}]), "bad island row")

    def test_quest_id(self):
        self.bad(dict(tiny_cfg(), quest="q_other"), "quest")
        bs.validate(dict(tiny_cfg(), quest="q_byte_spring"))

    def test_islands(self):
        self.bad(tiny_cfg(islands=[], start_residents=[]), "non-empty")
        self.bad(tiny_cfg(islands=[{"id": "bad-id", "cost_kib": 1}], start_residents=[]), "island id")
        self.bad(tiny_cfg(islands=[{"id": "a", "cost_kib": 0}], start_residents=[]), "cost")
        cfg = tiny_cfg()
        cfg["islands"].append({"id": "cache_a", "cost_kib": 10})
        self.bad(cfg, "duplicate island")

    def test_start_residents(self):
        self.bad(tiny_cfg(start_residents=["nope"]), "unknown start resident")
        self.bad(tiny_cfg(start_residents=["cache_a", "cache_a"]), "duplicate start")
        self.bad(tiny_cfg(start_residents="cache_a"), "list")

    def test_keystone(self):
        self.bad(tiny_cfg(keystone="vault"), "start resident")
        self.bad(tiny_cfg(keystone="cache_b", cistern=cistern(budget_cap=150)), "exceeds budget_cap")
        self.assertEqual(bs.validate(tiny_cfg(keystone="cache_a")).keystone, "cache_a")

    def test_npc(self):
        lines = dict(bs.DEFAULT_NPC["lines"])
        del lines["win"]
        self.bad(tiny_cfg(npc={"name": "Spigot", "lines": lines}), "npc line win")
        lines = dict(bs.DEFAULT_NPC["lines"], boast="hi")
        self.bad(tiny_cfg(npc={"name": "Spigot", "lines": lines}), "unknown npc line")
        self.bad(tiny_cfg(npc={"name": " ", "lines": bs.DEFAULT_NPC["lines"]}), "npc name")


class BudgetTest(unittest.TestCase):
    def test_overflow_dumps_lowest_priority(self):
        # 100(p1) + 200(p0) + 250(p2) = 550 > 400: dump cache_b (p0) -> 350 fits
        st = bs.simulate(tiny_cfg(start_residents=["cache_a", "cache_b", "vault"]), [])
        self.assertEqual(st.dumped, ["cache_b"])
        self.assertEqual(sorted(st.resident_ids()), ["cache_a", "vault"])
        self.assertIn("dump", st.last_events)

    def test_tie_break_cost_then_id(self):
        cfg = tiny_cfg(
            islands=[{"id": "b", "cost_kib": 100}, {"id": "a", "cost_kib": 100}, {"id": "c", "cost_kib": 300}],
            start_residents=["a", "b", "c"], cistern=cistern(budget_cap=150))
        st = bs.simulate(cfg, [])
        self.assertEqual(st.dumped, ["c", "a"])  # all p0: highest cost first, then id order
        self.assertEqual(st.resident_ids(), ["b"])

    def test_load_action_overflow_dumps(self):
        cfg = bs.validate(tiny_cfg(keystone="cache_a", islands=[
            {"id": "cache_a", "cost_kib": 100, "priority": 9},
            {"id": "cache_b", "cost_kib": 200, "priority": 0},
            {"id": "vault", "cost_kib": 250, "priority": 2}]))
        st = bs.new_state(cfg)
        bs.tick(st, cfg, False, ("load", "vault"))
        self.assertEqual(st.dumped, ["cache_b"])
        self.assertEqual(st.outcome, bs.RUNNING)
        self.assertIn("act load:vault", st.log[-1])
        self.assertIn("dump cache_b", st.log[-1])

    def test_zero_budget_dumps_everything_but_runs(self):
        st = bs.simulate(tiny_cfg(cistern=cistern(budget_cap=0)), [False] * 5)
        self.assertEqual(st.resident_ids(), [])
        self.assertEqual(st.outcome, bs.WON)  # nothing drinks, spring keeps it wet

    def test_keystone_dumped_at_start_fails(self):
        cfg = tiny_cfg(keystone="cache_b", start_residents=["cache_a", "cache_b", "vault"])
        st = bs.simulate(cfg, [False] * 5)
        self.assertEqual((st.outcome, st.fail_reason, st.ticks), (bs.FAILED, bs.FAIL_KEYSTONE, 0))

    def test_invariants_over_seeds_and_actions(self):
        cfg = bs.load(DATA)
        ids = [i.id for i in cfg.islands]
        for seed in range(150):
            w = bs.weather(seed, 30, cfg.dry_permille)
            st = bs.new_state(cfg)
            for n, dry in enumerate(w, 1):
                if st.outcome != bs.RUNNING:
                    break
                iid = ids[(seed + n) % len(ids)]
                act = None
                if n % 3 == 0 and iid not in st.resident_ids():
                    act = ("load", iid)
                elif n % 4 == 0 and iid in st.resident_ids() and iid != cfg.keystone:
                    act = ("unload", iid)
                bs.tick(st, cfg, dry, act)
                self.assertGreaterEqual(st.level, 0)
                self.assertLessEqual(st.level, cfg.capacity)
                self.assertLessEqual(bs.resident_cost(st.residents), cfg.budget_cap)
                self.assertEqual(len(set(st.resident_ids())), len(st.residents))


class ActionTest(unittest.TestCase):
    def setUp(self):
        self.cfg = bs.validate(tiny_cfg(keystone="cache_a"))
        self.st = bs.new_state(self.cfg)

    def assert_refused(self, action, msg):
        snap = copy.deepcopy(self.st)
        with self.assertRaises(bs.ByteSpringError) as cm:
            bs.tick(self.st, self.cfg, False, action)
        self.assertIn(msg, str(cm.exception))
        self.assertEqual(self.st, snap)  # refused actions cost no tick and change nothing

    def test_refusals(self):
        self.assert_refused(("unload", "cache_a"), "keystone")
        self.assert_refused(("unload", "vault"), "not resident")
        self.assert_refused(("load", "cache_b"), "already resident")
        self.assert_refused(("load", "ghost"), "unknown island")
        self.assert_refused(("drop", "cache_b"), "action must be")
        self.assert_refused("load vault", "action must be")

    def test_dry_must_be_bool(self):
        with self.assertRaises(bs.ByteSpringError):
            bs.tick(self.st, self.cfg, 1)

    def test_unload_then_reload(self):
        bs.tick(self.st, self.cfg, True, ("unload", "cache_b"))
        self.assertEqual(self.st.unloaded, ["cache_b"])
        bs.tick(self.st, self.cfg, False, ("load", "cache_b"))
        self.assertEqual(self.st.resident_ids(), ["cache_a", "cache_b"])

    def test_reload_dumped_island(self):
        st = bs.simulate(tiny_cfg(start_residents=["cache_a", "cache_b", "vault"]), [])
        cfg = bs.validate(tiny_cfg())
        bs.tick(st, cfg, False, ("unload", "vault"))
        bs.tick(st, cfg, False, ("load", "cache_b"))
        self.assertIn("cache_b", st.resident_ids())


class QuestEdgeTest(unittest.TestCase):
    def test_win_exactly_at_win_ticks(self):
        cfg = bs.validate(tiny_cfg())
        st = bs.new_state(cfg)
        for _ in range(4):
            bs.tick(st, cfg, False)
        self.assertEqual(st.outcome, bs.RUNNING)
        bs.tick(st, cfg, False)
        self.assertEqual((st.outcome, st.ticks), (bs.WON, 5))

    def test_simulate_stops_at_end(self):
        st = bs.simulate(tiny_cfg(), [False] * 50)
        self.assertEqual(st.ticks, 5)
        self.assertEqual(len(st.log), 5)

    def test_finished_quest_is_frozen(self):
        cfg = bs.validate(tiny_cfg())
        st = bs.simulate(cfg, [False] * 5)
        snap = copy.deepcopy(st)
        bs.tick(st, cfg, True, ("load", "vault"))  # ignored, even an action
        self.assertEqual(st, snap)

    def test_drought_fails_after_limit_empty_dry_ticks(self):
        cfg = tiny_cfg(cistern=cistern(capacity=300, level=120, spring_fill=10, leak=40, budget_cap=500),
                       win_ticks=20)
        st = bs.simulate(cfg, [True] * 10)
        self.assertEqual((st.outcome, st.fail_reason), (bs.FAILED, bs.FAIL_DROUGHT))
        self.assertEqual(st.ticks, 3)  # empty on ticks 1, 2, 3
        self.assertEqual(st.empty_streak, 3)

    def test_dry_ticks_with_water_do_not_count(self):
        # big cistern: 3 dry ticks still holding water, empties on the 4th -> streak 1, not 4
        cfg = tiny_cfg(cistern=cistern(capacity=1400, level=1400, budget_cap=500), win_ticks=50)
        st = bs.simulate(cfg, [True] * 4)
        self.assertEqual(st.dry_streak, 4)
        self.assertEqual(st.level, 0)
        self.assertEqual(st.empty_streak, 1)
        self.assertEqual(st.outcome, bs.RUNNING)

    def test_wet_tick_resets_empty_streak_even_if_still_empty(self):
        # spring_fill 10 < drink 300: wet ticks stay empty but break the drought
        cfg = tiny_cfg(cistern=cistern(level=0, spring_fill=10), win_ticks=50)
        st = bs.simulate(cfg, [True, True, False, True, True, False, True, True])
        self.assertEqual(st.level, 0)
        self.assertEqual(st.outcome, bs.RUNNING)
        self.assertEqual(st.empty_streak, 2)

    def test_drought_limit_one(self):
        st = bs.simulate(tiny_cfg(cistern=cistern(level=0), drought_limit=1), [True])
        self.assertEqual((st.outcome, st.ticks), (bs.FAILED, 1))

    def test_overtime_when_empty_at_win_ticks(self):
        # empty at tick win_ticks -> keep playing until it holds water (or droughts)
        cfg = tiny_cfg(cistern=cistern(level=0, spring_fill=200), win_ticks=2, drought_limit=5)
        st = bs.simulate(cfg, [True, True, True])
        self.assertEqual((st.outcome, st.ticks), (bs.RUNNING, 3))
        st = bs.simulate(cfg, [True, True, True, False])
        self.assertEqual((st.outcome, st.ticks), (bs.RUNNING, 4))  # 200 fill - 300 drink = 0
        cfg["cistern"]["spring_fill"] = 350
        st = bs.simulate(cfg, [True, True, True, False])
        self.assertEqual((st.outcome, st.ticks, st.level), (bs.WON, 4, 50))

    def test_keystone_loss_beats_win_on_same_tick(self):
        cfg = bs.validate(tiny_cfg(keystone="cache_b", win_ticks=1))
        st = bs.new_state(cfg)
        bs.tick(st, cfg, False, ("load", "vault"))  # 550 > 400 dumps cache_b (p0) = keystone
        self.assertEqual((st.outcome, st.fail_reason), (bs.FAILED, bs.FAIL_KEYSTONE))
        self.assertGreater(st.level, 0)

    def test_spill_caps_at_capacity(self):
        st = bs.simulate(tiny_cfg(cistern=cistern(level=1000), start_residents=[]), [False])
        self.assertEqual(st.level, 1000)
        self.assertIn("spill", st.last_events)

    def test_too_many_ticks(self):
        with self.assertRaises(bs.ByteSpringError):
            bs.simulate(tiny_cfg(), [False] * (bs.MAX_TICKS + 1))


class SeedTest(unittest.TestCase):
    def test_weather_golden(self):
        self.assertEqual([int(x) for x in bs.weather(39, 12, 550)], [1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1])

    def test_weather_extremes_and_validation(self):
        self.assertEqual(bs.weather(7, 20, 0), [False] * 20)
        self.assertEqual(bs.weather(7, 20, 1000), [True] * 20)
        self.assertEqual(bs.weather(7, 0), [])
        for seed in (-1, 2 ** 32, True, "39"):
            with self.assertRaises(bs.ByteSpringError):
                bs.weather(seed, 5)
        self.assertNotEqual(bs.weather(1, 32), bs.weather(2, 32))

    def test_seeded_runs_repeat(self):
        cfg = fixture()
        a = bs.simulate_seeded(cfg, 1234, 40)
        b = bs.simulate_seeded(cfg, 1234, 40)
        self.assertEqual(bs.trace(a), bs.trace(b))
        self.assertEqual(bs.receipt(a, bs.validate(cfg)), bs.receipt(b, bs.validate(cfg)))

    def test_trace_golden(self):
        # pins the rules: a port (Java/C++) must reproduce these bytes
        cfg = bs.load(DATA)
        st = bs.simulate_seeded(cfg, 39, 40)
        self.assertEqual((st.outcome, st.fail_reason, st.ticks), (bs.FAILED, bs.FAIL_DROUGHT, 22))
        self.assertEqual(hashlib.sha256(bs.trace(st).encode()).hexdigest(),
                         "51a6884383b77bf73229f4c9719a09c3860bc7a4e228bbd87bf281e3f3b98a43")
        st = bs.simulate_seeded(cfg, 39, 40, actions={1: ("unload", "cache_north")})
        self.assertEqual((st.outcome, st.ticks, st.level), (bs.WON, 20, 820))
        self.assertEqual(hashlib.sha256(bs.trace(st).encode()).hexdigest(),
                         "d1226d1a34b33343300857238717dc1eeb58795605c34fe9923e4d00ba5ea921")


DSB_TEXT = """DSB 1
island DiskSaver x 0 y 0 ram 25015 disk 25470
island Near x 1000 y 0 ram 10000 disk 2000
island Far x 900000 y 0 ram 100 disk 100
"""


class DsbCompositionTest(unittest.TestCase):
    def test_islands_from_dsb_rounds_up(self):
        rows = dsb.parse(DSB_TEXT)
        isl = bs.islands_from_dsb(rows, 1024, {"DiskSaver": 5})
        self.assertEqual(isl[0], {"id": "DiskSaver", "cost_kib": 50, "priority": 5})  # ceil(50485/1024)
        self.assertEqual(isl[1]["cost_kib"], 12)  # ceil(12000/1024)
        self.assertEqual(isl[2]["cost_kib"], 1)
        self.assertEqual(bs.islands_from_dsb(rows, 1)[0]["cost_kib"], 50485)
        with self.assertRaises(bs.ByteSpringError):
            bs.islands_from_dsb(rows, 0)

    def test_picker_chooses_start_residents(self):
        rows = dsb.parse(DSB_TEXT)
        self.assertEqual(bs.pick_residents(rows, (0, 0), 5000, 6000, 10 ** 6), ["DiskSaver", "Near"])
        self.assertEqual(bs.pick_residents(rows, (0, 0), 5000, 6000, 30000), ["DiskSaver"])  # RAM budget
        self.assertEqual(bs.pick_residents(rows, (900000, 0), 5000, 6000, 10 ** 6), ["Far"])

    def test_config_from_dsb(self):
        base = fixture()
        base["keystone"] = "DiskSaver"
        cfg = bs.config_from_dsb(DSB_TEXT, base, (0, 0), 5000, 6000, 10 ** 6, priorities={"DiskSaver": 9})
        self.assertEqual(cfg.start_residents, ("DiskSaver", "Near"))
        self.assertEqual(cfg.keystone, "DiskSaver")
        self.assertEqual(cfg.island("DiskSaver").cost, 50)
        st = bs.simulate_seeded(cfg, 39, 40)
        self.assertIn(st.outcome, (bs.WON, bs.FAILED))
        # viewer far away: DiskSaver not streamed in -> keystone dropped, quest still valid
        cfg = bs.config_from_dsb(DSB_TEXT, base, (900000, 0), 5000, 6000, 10 ** 6)
        self.assertEqual((cfg.start_residents, cfg.keystone), (("Far",), None))

    def test_bad_manifest_is_rejected(self):
        with self.assertRaises(dsb.DsbError):
            bs.config_from_dsb("DSB 2\n", fixture(), (0, 0), 1, 1, 1)

    def test_real_streaming_manifest(self):
        with open(MANIFEST, encoding="utf-8") as f:
            text = f.read()
        rows = dsb.parse(text)
        ds = [r for r in rows if r[0] == "DiskSaver"]
        self.assertEqual(len(ds), 1)
        base = dict(fixture(), keystone="DiskSaver")
        base["cistern"] = dict(base["cistern"], budget_cap=400)
        cfg = bs.config_from_dsb(text, base, (ds[0][1], ds[0][2]), 3_000_000, 3_500_000, 10 ** 6)
        self.assertIn("DiskSaver", cfg.start_residents)
        self.assertEqual(cfg.keystone, "DiskSaver")
        st = bs.simulate_seeded(cfg, 39, 40, actions=None)
        self.assertLessEqual(bs.resident_cost(st.residents), 400)


class NpcReceiptTest(unittest.TestCase):
    def test_npc_lines_follow_state(self):
        cfg = bs.validate(tiny_cfg(keystone="cache_b"))
        st = bs.new_state(cfg)
        self.assertEqual(bs.npc_say(st, cfg)[0], "start")
        bs.tick(st, cfg, True)
        self.assertEqual(bs.npc_say(st, cfg)[0], "low")  # 500-50-300 = 150 <= 1000/4
        st = bs.simulate(cfg, [False] * 5)
        self.assertEqual(bs.npc_say(st, cfg), ("win", cfg.npc_lines["win"]))
        st = bs.new_state(cfg)
        bs.tick(st, cfg, False, ("load", "vault"))
        self.assertEqual(bs.npc_say(st, cfg)[0], "fail_keystone")
        st = bs.simulate(tiny_cfg(cistern=cistern(level=0), drought_limit=1), [True])
        self.assertEqual(bs.npc_say(st, bs.validate(tiny_cfg()))[0], "fail_drought")

    def test_receipt(self):
        cfg = bs.load(DATA)
        won = bs.simulate_seeded(cfg, 39, 40, actions={1: ("unload", "cache_north")})
        r = bs.receipt(won, cfg)
        self.assertEqual((r["quest"], r["outcome"], r["score"]), ("q_byte_spring", "won", 410))
        self.assertEqual(r["unloaded"], ["cache_north"])
        json.dumps(r)
        lost = bs.receipt(bs.simulate_seeded(cfg, 39, 40), cfg)
        self.assertEqual((lost["outcome"], lost["fail_reason"], lost["score"]), ("failed", "drought", 0))


class FixtureTest(unittest.TestCase):
    def test_fixture_is_a_real_game(self):
        cfg = bs.load(DATA)
        self.assertEqual(fixture()["quest"], bs.QUEST_ID)
        self.assertEqual(cfg.keystone, "disk_saver_home")
        idle = sum(bs.simulate_seeded(cfg, s, 40).won for s in range(200))
        smart = sum(bs.simulate_seeded(cfg, s, 40, {1: ("unload", "cache_north")}).won for s in range(200))
        self.assertTrue(40 <= idle <= 180, idle)  # winnable and losable without play
        self.assertGreater(smart, idle)  # unloading a cache in the dry season helps

    def test_cli(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = bs.main([DATA, "--seed", "39", "--ticks", "40"])
        self.assertEqual(code, 1)
        lines = out.getvalue().splitlines()
        self.assertTrue(lines[-2].startswith("Spigot: "))
        self.assertEqual(json.loads(lines[-1])["outcome"], "failed")
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            self.assertEqual(bs.main([os.path.join(HERE, "no-such.json")]), 2)


if __name__ == "__main__":
    unittest.main()
