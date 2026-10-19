// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.HerdOutbreak.Generation;
import com.daedalus.world.battlefield.HerdOutbreak.Outcome;
import com.daedalus.world.battlefield.HerdOutbreak.Report;
import com.daedalus.world.battlefield.HerdOutbreak.Settings;
import org.junit.jupiter.api.Test;

class HerdOutbreakTest {

    private static final Settings D = Settings.DEFAULT;
    private static final int SEEDS = 400;

    private static Report run(long seed, int vaccinate, int fenceAt) {
        HerdOutbreak h = HerdOutbreak.herd(D, seed);
        assertTrue(h.vaccinate(vaccinate));
        if (fenceAt >= 0) {
            assertTrue(h.fence(fenceAt, 0.3));
        }
        return h.run();
    }

    private static int count(int vaccinate, int fenceAt, Outcome o) {
        int n = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            if (run(seed, vaccinate, fenceAt).outcome() == o) {
                n++;
            }
        }
        return n;
    }

    private static double meanShare(int vaccinate) {
        double sum = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            sum += run(seed, vaccinate, -1).share();
        }
        return sum / SEEDS;
    }

    /** Mean share among major outbreaks (more than 10% of the herd sick). */
    private static double majorShare(int vaccinate) {
        double sum = 0;
        int n = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            Report r = run(seed, vaccinate, -1);
            if (r.share() > HerdOutbreak.CONTAINED) {
                sum += r.share();
                n++;
            }
        }
        return n == 0 ? 0 : sum / n;
    }

    @Test
    void finalSizeAndThresholdMatchTheTextbook() {
        double z = HerdOutbreak.finalSize(2.5);
        assertEquals(1 - Math.exp(-2.5 * z), z, 1e-12);
        assertEquals(0.8926, z, 1e-3);
        assertEquals(0.0, HerdOutbreak.finalSize(0.9), 0.0);
        assertEquals(0.6, HerdOutbreak.herd(D, 1).threshold(), 1e-12);
    }

    @Test
    void anUnvaccinatedHerdUsuallyGetsTheFullEpidemic() {
        assertTrue(count(0, -1, Outcome.EPIDEMIC) >= 320, "epidemics " + count(0, -1, Outcome.EPIDEMIC));
        assertEquals(HerdOutbreak.finalSize(D.r0()), majorShare(0), 0.03);
    }

    @Test
    void vaccinatingPastTheHerdImmunityThresholdStopsTheBlight() {
        int doses = (int) Math.ceil(0.75 * D.herd());
        assertTrue((double) doses / D.herd() > HerdOutbreak.herd(D, 1).threshold());
        assertEquals(SEEDS, count(doses, -1, Outcome.CONTAINED));
        assertTrue(count(40, -1, Outcome.EPIDEMIC) >= 250, "20% vaccinated");
    }

    @Test
    void vaccinationShrinksTheOutbreakToTheEffectiveRFinalSize() {
        int v = 80;
        double unprotected = (double) (D.herd() - v) / D.herd();
        double expected = HerdOutbreak.finalSize(D.r0() * unprotected) * unprotected;
        assertEquals(expected, majorShare(v), 0.05);
    }

    @Test
    void moreDosesNeverMeanMoreSickAnimals() {
        double last = Double.MAX_VALUE;
        for (int v : new int[] {0, 40, 80, 100, 120, 150}) {
            double m = meanShare(v);
            assertTrue(m <= last, v + " doses: " + m);
            last = m;
        }
    }

    @Test
    void anEarlyFenceBeatsALateOne() {
        int early = count(0, 1, Outcome.CONTAINED);
        int late = count(0, 3, Outcome.CONTAINED);
        int none = count(0, -1, Outcome.CONTAINED);
        assertTrue(early > late && late > none, early + " > " + late + " > " + none);
        assertTrue(early >= 300, "fence at generation 1: " + early);
    }

    @Test
    void theLedgerAddsUp() {
        for (long seed = 1; seed <= 30; seed++) {
            Report r = run(seed, 60, 4);
            int sick = 1;
            int last = D.herd();
            for (Generation g : r.generations()) {
                sick += g.sick();
                assertTrue(g.susceptible() <= last);
                last = g.susceptible();
            }
            assertEquals(r.sick(), sick);
            assertTrue(r.sick() <= D.herd() - r.vaccinated());
            assertEquals(r.outcome() == Outcome.CONTAINED ? Vegetation.MEADOW : Vegetation.SCRUB, r.band());
        }
    }

    @Test
    void sameSeedSamePlanSameBlight() {
        for (long seed = 1; seed <= 10; seed++) {
            assertEquals(run(seed, 50, 2), run(seed, 50, 2));
            assertEquals(run(seed, 0, -1), HerdOutbreak.herd(D, seed).run());
        }
    }

    @Test
    void badPlansAndSettingsAreRefused() {
        HerdOutbreak h = HerdOutbreak.herd(D, 1);
        assertFalse(h.vaccinate(D.doses() + 1));
        assertFalse(h.vaccinate(-1));
        assertFalse(h.fence(-1, 0.5));
        assertFalse(h.fence(2, 1.5));
        assertTrue(h.vaccinate(D.doses()));
        Settings tiny = new Settings(10, 2, 50, 10);
        assertFalse(HerdOutbreak.herd(tiny, 1).vaccinate(10));
        assertThrows(IllegalArgumentException.class, () -> HerdOutbreak.herd(null, 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(1, 2.5, 10, 10));
        assertThrows(IllegalArgumentException.class, () -> new Settings(200, -1, 10, 10));
    }
}
