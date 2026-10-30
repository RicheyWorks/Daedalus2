// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.TranslocationPlan.Plan;
import com.daedalus.world.battlefield.TranslocationPlan.Settings;
import java.util.List;
import org.junit.jupiter.api.Test;

class TranslocationPlanTest {

    private static final CraneCohorts FLOCK = CraneCohorts.marsh(CraneCohorts.Settings.DEFAULT, 1);
    private static final Settings D = Settings.DEFAULT;

    private static TranslocationPlan plan(Settings s) {
        return TranslocationPlan.of(FLOCK, s, 7);
    }

    @Test
    void bestBeatsEveryNamedScheduleAndSpendsTheBudget() {
        TranslocationPlan p = plan(D);
        Plan best = p.best();
        assertEquals(D.budget(), best.total());
        assertTrue(best.risk() <= p.risk(p.even()));
        assertTrue(best.risk() <= p.risk(p.frontLoaded()));
        assertTrue(best.risk() <= p.risk(new int[] {0, 0, 0, 4, 6}));
        assertTrue(best.risk() < p.risk(new int[5]), "releasing must help");
    }

    @Test
    void greedyIsNeverBetterThanExactAndCloseToIt() {
        for (int budget : new int[] {4, 10, 16}) {
            TranslocationPlan p = plan(D.withBudget(budget));
            Plan best = p.best();
            Plan greedy = p.greedy();
            assertEquals(budget, greedy.total());
            assertTrue(best.risk() <= greedy.risk() + 1e-12);
            assertTrue(greedy.risk() - best.risk() <= 0.03, budget + ": " + greedy + " vs " + best);
        }
    }

    @Test
    void moreBirdsNeverRaiseTheBestRisk() {
        double prev = 1.01;
        for (int budget = 0; budget <= 20; budget += 4) {
            double r = plan(D.withBudget(budget)).best().risk();
            assertTrue(r <= prev + 1e-12, budget + " " + r);
            prev = r;
        }
        assertTrue(prev < plan(D.withBudget(0)).best().risk());
    }

    @Test
    void aGrowingFlockWantsTheBirdsEarly() {
        Plan best = plan(D).best();
        List<Integer> s = best.schedule();
        assertTrue(s.get(0) + s.get(1) >= s.get(3) + s.get(4), s.toString());
        TranslocationPlan p = plan(D);
        assertTrue(p.risk(p.frontLoaded()) < p.risk(new int[] {0, 0, 0, 4, 6}));
    }

    @Test
    void adultsAreWorthMoreThanChicks() {
        double adults = plan(D).best().risk();
        double chicks = plan(D.withCohort(CraneCohorts.CHICK)).best().risk();
        assertTrue(adults < chicks, adults + " vs " + chicks);
        // Same order as the G194 reproductive values.
        assertEquals(CraneCohorts.ADULT, FLOCK.bestRelease());
    }

    @Test
    void calmYearsMeanNoRiskForABigFlock() {
        TranslocationPlan p = plan(new Settings(40, 4, 4, 2, 30, 10, 0, CraneCohorts.ADULT, 10));
        assertEquals(0, p.best().risk(), 0);
    }

    @Test
    void seededPlansReplay() {
        Plan a = plan(D).best();
        assertEquals(a, plan(D).best());
        assertEquals(a.risk(), plan(D).risk(a.schedule().stream().mapToInt(Integer::intValue).toArray()), 0);
    }

    @Test
    void badInputIsRejected() {
        assertThrows(IllegalArgumentException.class, () -> new Settings(12, 40, 6, 5, 30, 10, 0.2, 3, 100));
        assertThrows(IllegalArgumentException.class, () -> new Settings(12, 10, 6, 5, 3, 10, 0.2, 3, 100));
        assertThrows(IllegalArgumentException.class, () -> new Settings(12, 10, 6, 5, 30, 0, 0.2, 3, 100));
        assertThrows(IllegalArgumentException.class, () -> new Settings(12, 10, 6, 5, 30, 10, 0.2, 4, 100));
        assertThrows(IllegalArgumentException.class, () -> TranslocationPlan.of(null, D, 1));
        TranslocationPlan p = plan(D);
        assertThrows(IllegalArgumentException.class, () -> p.risk(new int[] {1, 2}));
        assertThrows(IllegalArgumentException.class, () -> p.risk(new int[] {7, 0, 0, 0, 3}));
    }
}
