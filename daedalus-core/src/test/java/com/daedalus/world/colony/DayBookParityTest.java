// SPDX-License-Identifier: MIT

package com.daedalus.world.colony;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.junit.jupiter.api.Test;

/** Replays colony_ledger.py's day book (finds, museum, store, charm, requests) day by day for 9 islands. */
class DayBookParityTest {

    static Cast castOf(String roles, String quests) {
        List<Cast.QuestDef> qs = new ArrayList<>();
        if (!quests.equals("-")) {
            for (String q : quests.split("\\|")) {
                String[] g = q.split(":");
                List<String> steps = new ArrayList<>();
                for (int i = 1; i <= Integer.parseInt(g[2]); i++) {
                    steps.add("step " + i);
                }
                qs.add(new Cast.QuestDef(g[1], g[0], steps, ""));
            }
        }
        return new Cast(Fixture.list(roles), qs);
    }

    static String render(List<DayBook.Request> rs) {
        if (rs.isEmpty()) {
            return "-";
        }
        List<String> out = new ArrayList<>();
        for (DayBook.Request r : rs) {
            out.add(r.npc() + ";" + String.join(",", r.wants()) + ";" + r.pays() + ";" + (r.questId() == null ? "-" : r.questId()));
        }
        return String.join("|", out);
    }

    static String store(PlotState p) {
        Map<String, Double> s = new TreeMap<>(p.store());
        if (s.isEmpty()) {
            return "-";
        }
        List<String> out = new ArrayList<>();
        s.forEach((k, v) -> out.add(k + "=" + v));
        return String.join(",", out);
    }

    @Test
    void javaDayBookMatchesPythonForEveryFixtureDay() throws Exception {
        IslandFacts island = null;
        Cast cast = null;
        PlotState plot = null;
        int days = 0;
        int cases = 0;
        int questRequests = 0;
        boolean sawCrater = false;
        for (String[] c : Fixture.rows(null)) {
            if (c[0].equals("CASE")) {
                island = new IslandFacts(Integer.parseInt(c[2]), Fixture.list(c[3]), c[4].equals("1"), Fixture.list(c[5]),
                        new HashSet<>(Fixture.list(c[6])), c[7], Fixture.list(c[8]));
                sawCrater |= island.starmetalCrater();
                cast = castOf(c[9], c[10]);
                plot = new PlotState();
                cases++;
            } else if (c[0].equals("DAY")) {
                String where = "deed " + island.deed() + " day " + c[1];
                DayBook.Day d = DayBook.today(island, plot, cast, Integer.parseInt(c[1]), Integer.parseInt(c[2]),
                        new DayBook.Ecology(Integer.parseInt(c[3]), c[4]));
                assertEquals(Fixture.list(c[5]), d.finds(), where + " finds");
                assertEquals(Fixture.list(c[6]), d.newInCollection(), where + " new");
                assertEquals(Double.parseDouble(c[7]), d.bonus(), where + " bonus");
                assertEquals(c[8], render(d.requests()), where + " requests");
                assertEquals(c[9], store(plot), where + " store");
                assertEquals(Double.parseDouble(c[10]), plot.charm(), 1e-9, where + " charm");
                questRequests += (int) d.requests().stream().filter(r -> r.questId() != null).count();
                days++;
            }
        }
        assertEquals(9, cases);
        assertEquals(72, days);
        assertTrue(sawCrater, "fixture covers a starmetal crater island");
        assertTrue(questRequests > 0, "fixture covers PORT09 quest-giver requests");
    }

    @Test
    void noFishAtNoonAndNoFruitInWinter() {
        IslandFacts island = new IslandFacts(240, List.of("rillperch"), false, List.of("apple"), Set_of("apple"), "ORE", List.of("iron"));
        DayBook.Day noon = DayBook.today(island, new PlotState(), Cast.NONE, 1, 12, new DayBook.Ecology(0, "winter"));
        assertTrue(!noon.finds().contains("rillperch") && !noon.finds().contains("apple"), noon.finds().toString());
        DayBook.Day dawn = DayBook.today(island, new PlotState(), Cast.NONE, 1, 7, new DayBook.Ecology(0, "summer"));
        assertTrue(dawn.finds().contains("rillperch") && dawn.finds().contains("apple"), dawn.finds().toString());
    }

    @Test
    void secondDayOfTheSameFindsHasNoMuseumBonus() {
        IslandFacts island = new IslandFacts(43, List.of(), true, List.of(), Set_of(), "ORE", List.of("iron"));
        PlotState p = new PlotState();
        DayBook.Day one = DayBook.today(island, p, Cast.NONE, 1, 12, new DayBook.Ecology(2, "winter"));
        DayBook.Day two = DayBook.today(island, p, Cast.NONE, 1, 12, new DayBook.Ecology(2, "winter"));
        assertTrue(one.bonus() > 0);
        assertEquals(0.0, two.bonus());
        assertEquals(one.finds(), two.finds(), "same deed+day = same finds");
        assertEquals(2.0, p.count(one.finds().get(0)));
    }

    @Test
    void requestsNeverAskForWhatTheIslandCannotMakeUnlessNothingFits() {
        IslandFacts island = new IslandFacts(9, List.of(), false, List.of(), Set_of("plank"), "ORE", List.of("gold", "iron", "plank"));
        for (DayBook.Request r : DayBook.requests(island, new PlotState(), new Cast(List.of("Carpenter", "Miner", "Smith"), List.of()), 3)) {
            List<String> all = ColonyTables.NPC_WANTS.get(r.npc());
            assertTrue(r.wants().equals(List.of("plank")) || r.wants().equals(List.of(all.get(0))), r.toString());
            assertTrue(List.of("gold", "iron").contains(r.pays()), "pays in an ORE line the island lacks: " + r);
        }
    }

    private static java.util.Set<String> Set_of(String... xs) {
        return java.util.Set.of(xs);
    }
}
