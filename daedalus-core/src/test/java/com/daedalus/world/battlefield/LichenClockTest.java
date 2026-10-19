// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.LichenClock.Dating;
import com.daedalus.world.battlefield.LichenClock.Outcome;
import com.daedalus.world.battlefield.LichenClock.Report;
import com.daedalus.world.battlefield.LichenClock.Settings;
import org.junit.jupiter.api.Test;

class LichenClockTest {

    private static final Settings D = Settings.DEFAULT;

    /** Spend the budget evenly: {@code n} thalli on every boulder, date each event by its largest lichen. */
    private static double[] date(LichenClock c, int n) {
        double[] g = new double[D.events()];
        for (int e = 0; e < D.events(); e++) {
            double best = 0;
            for (int b = 0; b < D.boulders(); b++) {
                best = Math.max(best, c.measure(e, b, n));
            }
            g[e] = c.age(best);
        }
        return g;
    }

    private static int[] truth(long seed) {
        Report r = LichenClock.field(D, seed).judge(new double[D.events()]);
        return r.datings().stream().mapToInt(Dating::trueAge).toArray();
    }

    @Test
    void theGrowthCurveHasAFastPhaseThenASlowOne_andAgeInvertsIt() {
        LichenClock c = LichenClock.field(D, 1);
        assertEquals(0.0, c.curve(0));
        assertEquals(D.fastRate() * 20, c.curve(20), 1e-12);
        assertEquals(D.fastRate() * D.fastYears() + D.slowRate() * 30, c.curve(D.fastYears() + 30), 1e-12);
        for (double years : new double[] {5, 49, 50, 51, 180}) {
            assertEquals(years + D.lag(), c.age(c.curve(years)), 1e-9);
        }
        assertEquals(D.lag(), c.age(0), "bare rock reads as no older than the lag");
    }

    @Test
    void carefulSamplingDatesEveryRockfall() {
        int per = D.budget() / (D.events() * D.boulders());
        for (long seed = 1; seed <= 6; seed++) {
            Report r = LichenClock.field(D, seed).judge(date(LichenClock.field(D, seed), per));
            assertEquals(Outcome.DATED, r.outcome(), "seed " + seed);
            assertTrue(r.meanError() < D.tolerance() / 2);
        }
    }

    @Test
    void oneLichenPerBoulderMakesTheFallsLookYounger() {
        int per = D.budget() / (D.events() * D.boulders());
        double hasty = 0;
        double careful = 0;
        double signed = 0;
        for (long seed = 1; seed <= 6; seed++) {
            int[] age = truth(seed);
            double[] quick = date(LichenClock.field(D, seed), 1);
            double[] slow = date(LichenClock.field(D, seed), per);
            for (int e = 0; e < D.events(); e++) {
                hasty += Math.abs(quick[e] - age[e]);
                careful += Math.abs(slow[e] - age[e]);
                signed += quick[e] - age[e];
            }
        }
        assertTrue(hasty > 3 * careful, "hasty " + hasty + " careful " + careful);
        assertTrue(signed < 0, "late colonists bias young");
    }

    @Test
    void theLargestLichenOnlyGrowsWithMoreSampled() {
        double last = 0;
        for (int n = 1; n <= D.thalli(); n += 4) {
            double d = LichenClock.field(D, 2).measure(1, 0, n);
            assertTrue(d >= last);
            last = d;
        }
    }

    @Test
    void theBudgetRunsOut() {
        LichenClock c = LichenClock.field(D, 1);
        for (int i = 0; i < D.budget() / D.thalli(); i++) {
            assertTrue(c.measure(i % D.events(), 0, D.thalli()) >= 0);
        }
        assertEquals(0, c.budgetLeft());
        assertEquals(-1, c.measure(0, 0, 1));
    }

    @Test
    void judging_datedOrderedOrMuddled() {
        int[] age = truth(3);
        double[] exact = new double[age.length];
        double[] late = new double[age.length];
        double[] backwards = new double[age.length];
        for (int e = 0; e < age.length; e++) {
            exact[e] = age[e];
            late[e] = age[e] + 3 * D.tolerance();
            backwards[e] = -age[e];
        }
        assertEquals(Outcome.DATED, LichenClock.field(D, 3).judge(exact).outcome());
        Report off = LichenClock.field(D, 3).judge(late);
        assertEquals(Outcome.ORDERED, off.outcome());
        assertEquals(3 * D.tolerance(), off.meanError(), 1e-9);
        assertEquals(Outcome.MUDDLED, LichenClock.field(D, 3).judge(backwards).outcome());
    }

    @Test
    void eventsFallInsideTheWindow() {
        for (long seed = 1; seed <= 20; seed++) {
            for (int a : truth(seed)) {
                assertTrue(a >= D.minAge() && a <= D.maxAge());
            }
        }
    }

    @Test
    void theFieldPaintsByItsAge() {
        LichenClock c = LichenClock.field(D, 1);
        assertEquals(Vegetation.BARE, c.ground(D.lag() - 1));
        assertEquals(Vegetation.MEADOW, c.ground(D.lag() + 1));
        assertEquals(Vegetation.SCRUB, c.ground(D.lag() + D.fastYears() + 1));
    }

    @Test
    void sameFieldSameLichens() {
        assertEquals(LichenClock.field(D, 7).measure(2, 1, 9), LichenClock.field(D, 7).measure(2, 1, 9));
        assertEquals(D.events(), LichenClock.field(D, 7).events());
    }

    @Test
    void badInputIsRefused() {
        LichenClock c = LichenClock.field(D, 1);
        assertEquals(-1, c.measure(-1, 0, 1));
        assertEquals(-1, c.measure(0, D.boulders(), 1));
        assertEquals(-1, c.measure(0, 0, 0));
        assertEquals(-1, c.measure(0, 0, D.thalli() + 1));
        assertEquals(D.budget(), c.budgetLeft());
        assertThrows(IllegalArgumentException.class, () -> c.judge(new double[1]));
        assertThrows(IllegalArgumentException.class, () -> c.judge(null));
        assertThrows(IllegalArgumentException.class, () -> LichenClock.field(null, 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(1, 1, 1, 50, 40, 8, 25, 0.6, 50, 0.3, 1,
                10, 10));
    }
}
