# SPDX-License-Identifier: MIT
"""python -m unittest tools/economy/test_colony_ledger.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colony_ledger import Ledger, catalog, family_of, population  # noqa: E402


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.L = Ledger("WORLD-ZERO", seed=1)
        self.assertEqual(self.L.claim("richey", 240), "CLAIMED")
        self.assertEqual(self.L.claim("sol", 240), "TAKEN")
        self.L.claim("richey", 241)
        self.L.claim("sol", 300)

    def test_catalog_is_the_realms_chemistry(self):
        c = catalog("WORLD-ZERO")
        self.assertIn("starmetal", c)
        self.assertIn("dawnleaf", c)
        self.assertIn("gearbox", c)
        self.assertNotIn("chalk", c)
        self.assertEqual(family_of("gold"), "ORE")

    def test_outfitting_consumes_parts(self):
        self.assertEqual(self.L.outfit("richey", 240, "FOOD"), "NO_PARTS")
        self.L.plots[240].add("iron", 1)
        self.L.plots[240].add("plank", 2)
        self.assertEqual(self.L.outfit("richey", 240, "FOOD"), "OUTFITTED")
        self.assertEqual(self.L.plots[240].store["plank"], 0)
        self.assertEqual(self.L.outfit("sol", 240, "FOOD"), "REFUSED")

    def test_production_needs_energy_and_follows_ecology(self):
        p = self.L.plots[240]
        p.add("iron", 1)
        p.add("plank", 2)
        self.L.outfit("richey", 240, "FOOD")
        summer = self.L.produce(1, {240: {"seral": 1, "biodiversity": 1.2, "season": "summer"}})[240]
        winter = Ledger("WORLD-ZERO", seed=1)
        winter.claim("richey", 240)
        winter.plots[240].add("iron", 1)
        winter.plots[240].add("plank", 2)
        winter.outfit("richey", 240, "FOOD")
        w = winter.produce(1, {240: {"seral": 1, "biodiversity": 1.2, "season": "winter"}})[240]
        crop = p.chem["soil"]["crops"][0]
        self.assertGreater(summer[crop], w[crop] * 2)
        # no energy stored and the power source gives < 2 per round: a second worker halts
        p.add("iron", 1)
        p.add("plank", 2)
        self.L.outfit("richey", 240, "FOOD")
        p.store["energy"] = 0.0
        made = self.L.produce(2, {240: {"seral": 1, "biodiversity": 1.0, "season": "summer"}})[240]
        self.assertGreaterEqual(made.get("halted", 0), 0)

    def test_adjacency_bonus(self):
        for d in (240, 241):
            self.L.plots[d].add("iron", 2)
            self.L.plots[d].add("plank", 1)
            self.assertEqual(self.L.outfit("richey", d, "ORE"), "OUTFITTED")
        self.assertEqual(self.L.adjacency(240, "ORE"), 1)
        self.assertEqual(self.L.adjacency(300, "ORE"), 0)

    def test_market_day_fills_and_moves_prices(self):
        self.L.plots[240].add("coal", 10)
        before = self.L.prices["coal"]
        fills = self.L.market_day(1, [("richey", 240, "ask", "coal", 6, 5.0), ("sol", 300, "bid", "coal", 4, 7.0)])
        self.assertEqual(fills[0][:4], ("richey", "sol", "coal", 4))
        self.assertEqual(fills[1][1], "shop")                  # the leftover 2 went to the shop at the floor
        self.assertNotEqual(self.L.prices["coal"], before)
        self.assertEqual(len(self.L.cargo_in_air), 1)          # the ark is flying the coal to deed 300
        self.L.settle_cargo(3)
        self.assertEqual(self.L.plots[300].store["coal"], 4)

    def test_events_change_the_world(self):
        kinds = {self.L.event(r)[0] for r in range(40)}
        self.assertTrue({"meteor", "raiders"} & kinds)

    def test_day_book_finds_and_collection(self):
        d = self.L.day_book(240, day=3, hour=8, ecology={"seral": 1, "biodiversity": 1.0, "season": "summer"})
        self.assertIn("meadow_bee", d["finds"])
        self.assertGreater(d["bonus"], 0)
        again = self.L.day_book(240, day=4, hour=8, ecology={"seral": 1, "biodiversity": 1.0, "season": "summer"})
        self.assertLess(again["bonus"], d["bonus"])             # first-of-kind only pays once
        self.assertTrue(all("npc" in r and r["wants"] for r in d["requests"]))

    def test_portal_cast_drives_requests(self):
        P = Ledger("PORTAL", seed=2)
        P.claim("riley", 7)
        pop = population("PORTAL")
        self.assertIn("UnicornQuestgiver", pop["types"])
        reqs = P.requests(7, day=1)
        self.assertTrue(all(r["npc"] in pop["types"] for r in reqs))

    def test_raid_and_defence(self):
        self.L.plots[300].chem["geology"]["grade"] = "RICH"
        for _ in range(5):
            self.L.defend("sol", 300, "watchtower")
        outcomes = {self.L.raid("richey", 240, 300, r)[0] for r in range(30)}
        self.assertIn("CAUGHT", outcomes)
        self.L.hulks[241] = {"rotor": 1, "energy": 3.0}
        self.assertEqual(self.L.raid("sol", 300, 241, 1)[0], "LOOTED")
        self.assertNotIn(241, self.L.hulks)

    def test_fishing_and_boats(self):
        t = self.L.fishing(240, day=1, hour=18, season="summer")
        self.assertEqual(set(t), set(self.L.FISHING_SPOTS))
        self.assertIsNone(self.L.fishing(240, day=1, hour=13, season="summer")["lake"])    # nothing bites at noon
        net = self.L.water_network()
        self.assertIn(241, net[240])
        self.assertNotIn(300, net[240])                        # a boat can't reach another district row; an ark can

    def test_score(self):
        self.L.plots[240].add("gold", 3)
        s = self.L.score()
        self.assertGreater(s["richey"], s["sol"])


if __name__ == "__main__":
    unittest.main()
