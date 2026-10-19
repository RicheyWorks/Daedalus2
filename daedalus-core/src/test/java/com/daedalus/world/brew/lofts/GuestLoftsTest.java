// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lofts;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.letters.Destination;
import com.daedalus.world.brew.letters.LettersByArk;
import com.daedalus.world.brew.lofts.GuestLofts.Outcome;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class GuestLoftsTest {

    @Test
    void familiesComeOffTheArkAfterTheVoyage() {
        List<Family> fam = GuestLofts.fromFarIslands(Destination.island(), 7);
        assertEquals(8, fam.size());
        assertEquals(8, new HashSet<>(fam.stream().map(Family::id).toList()).size());
        for (Destination d : Destination.island()) {
            List<Family> mine = fam.stream().filter(f -> f.home().equals(d.id())).toList();
            assertEquals(GuestLofts.FAMILIES_PER_ISLAND, mine.size());
            int voyage = d.route().legs().size() * LettersByArk.DAYS_PER_LEG;
            for (Family f : mine) {
                assertTrue(f.arrive() >= 1 + voyage && f.arrive() <= 1 + voyage + GuestLofts.WAIT_MAX);
                int stay = f.leave() - f.arrive();
                assertTrue(stay >= GuestLofts.STAY_MIN && stay <= GuestLofts.STAY_MAX);
            }
        }
        assertEquals(fam, GuestLofts.fromFarIslands(Destination.island(), 7));
        assertThrows(IllegalArgumentException.class, () -> new Family("x", "h", 3, 3));
    }

    @Test
    void leavingInTheMorningFreesTheLoft() {
        Family a = new Family("a", "h", 1, 4);
        Family b = new Family("b", "h", 4, 6);
        Family c = new Family("c", "h", 2, 5);
        assertFalse(a.overlaps(b));
        assertTrue(a.overlaps(c));
        assertTrue(c.overlaps(b));
        assertEquals(2, GuestLofts.maxOverlap(List.of(a, b, c)));
        GuestLofts g = new GuestLofts(List.of(a, b, c));
        assertEquals(Map.of("a", 1, "c", 2, "b", 1), g.greedyPlan());
        assertThrows(IllegalArgumentException.class, () -> new GuestLofts(List.of(a, a)));
        assertThrows(IllegalArgumentException.class, () -> new GuestLofts(List.of()));
    }

    /** Can these families fit in k lofts? Exhaustive backtracking, independent of the greedy plan. */
    static boolean fits(List<Family> fam, int k, int i, int[] loft) {
        if (i == fam.size()) {
            return true;
        }
        for (int l = 0; l < k; l++) {
            boolean ok = true;
            for (int j = 0; j < i && ok; j++) {
                ok = loft[j] != l || !fam.get(j).overlaps(fam.get(i));
            }
            if (ok) {
                loft[i] = l;
                if (fits(fam, k, i + 1, loft)) {
                    return true;
                }
            }
        }
        return false;
    }

    @Test
    void greedyPlanUsesTheFewestLofts() {
        for (long seed = 0; seed < 40; seed++) {
            List<Family> fam = GuestLofts.fromFarIslands(Destination.island(), seed);
            GuestLofts g = new GuestLofts(fam);
            Map<String, Integer> plan = g.greedyPlan();
            int n = 0;
            for (Map.Entry<String, Integer> e : plan.entrySet()) {
                assertEquals(Outcome.HOUSED, g.assign("p" + n++, e.getKey(), e.getValue()), "seed " + seed);
            }
            assertEquals(g.fewest(), g.aired(), "seed " + seed);
            assertEquals(Outcome.SNUG, g.settle("s"));
            assertFalse(fits(fam, g.fewest() - 1, 0, new int[fam.size()]), "fewest is a true minimum, seed " + seed);
        }
    }

    @Test
    void guards() {
        GuestLofts g = new GuestLofts(List.of(new Family("a", "h", 1, 4), new Family("c", "h", 2, 5)));
        assertEquals(BrineLoftLines.GREETING, g.talk("t0"));
        assertEquals(Outcome.IGNORED, g.assign(" ", "a", 1));
        assertEquals(Outcome.UNKNOWN_FAMILY, g.assign("e0", "zed", 1));
        assertEquals(Outcome.NO_SUCH_LOFT, g.assign("e1", "a", 0));
        assertEquals(Outcome.NO_SUCH_LOFT, g.assign("e2", "a", GuestLofts.LOFTS + 1));
        assertEquals(Outcome.NOT_HOUSED, g.moveOut("e3", "a"));
        assertEquals(Outcome.NOT_EVERYONE, g.settle("e4"));
        assertEquals(Outcome.HOUSED, g.assign("e5", "a", 1));
        assertEquals(Outcome.DUPLICATE, g.assign("e5", "c", 2));
        assertEquals(Outcome.ALREADY_HOUSED, g.assign("e6", "a", 2));
        assertEquals(Outcome.CLASH, g.assign("e7", "c", 1));
        assertEquals(String.format(BrineLoftLines.HOUSING, 1, "y"), g.talk("t1"));
        assertNull(g.settled());
    }

    @Test
    void questSprawlThenSnugThenAuntBrine() {
        List<Family> fam = GuestLofts.fromFarIslands(Destination.island(), 3);
        GuestLofts g = new GuestLofts(fam);
        assertTrue(g.fewest() < fam.size());
        int n = 0;
        for (int i = 0; i < fam.size(); i++) {
            assertEquals(Outcome.HOUSED, g.assign("own" + n++, fam.get(i).id(), i + 1));
        }
        assertEquals(1, g.quest().stepIndex());
        assertEquals(Outcome.SPRAWL, g.settle("s1"));
        assertEquals(String.format(BrineLoftLines.SPRAWL, fam.size(), g.fewest()), g.talk("t1"));
        for (Family f : fam) {
            assertEquals(Outcome.MOVED_OUT, g.moveOut("out" + n++, f.id()));
        }
        for (Map.Entry<String, Integer> e : g.greedyPlan().entrySet()) {
            assertEquals(Outcome.HOUSED, g.assign("plan" + n++, e.getKey(), e.getValue()));
        }
        assertEquals(1, g.quest().stepIndex(), "moving a family back in does not re-count it");
        assertEquals(Outcome.SNUG, g.settle("s2"));
        assertEquals(BrineLoftLines.THANKS, g.talk("brine"));
        assertTrue(g.quest().complete());
        assertEquals(BrineLoftLines.DONE, g.talk("after"));
        assertEquals("q_guest_lofts", GuestLofts.QUEST_ID);
    }
}
