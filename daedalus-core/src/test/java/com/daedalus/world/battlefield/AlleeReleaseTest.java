// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.AlleeRelease.Outcome;
import com.daedalus.world.battlefield.AlleeRelease.Report;
import com.daedalus.world.battlefield.AlleeRelease.Settings;
import com.daedalus.world.battlefield.AlleeRelease.Year;
import org.junit.jupiter.api.Test;

class AlleeReleaseTest {

    private static final Settings D = Settings.DEFAULT;

    /** Releases the whole budget in {@code years} equal batches from year 0, and runs it. */
    private static Report spread(long seed, int years) {
        AlleeRelease m = AlleeRelease.marsh(D, seed);
        for (int y = 0; y < years; y++) {
            assertTrue(m.release(y, D.budget() / years));
        }
        return m.run();
    }

    private static int established(int years) {
        int n = 0;
        for (long seed = 1; seed <= 100; seed++) {
            if (spread(seed, years).outcome() == Outcome.ESTABLISHED) {
                n++;
            }
        }
        return n;
    }

    @Test
    void oneBigReleaseUsuallyEstablishes() {
        assertTrue(established(1) >= 85, "one release: " + established(1));
    }

    @Test
    void releasesBelowTheThresholdGoExtinctFarMoreOftenThanReleasesAboveIt() {
        int t = AlleeRelease.marsh(D, 1).threshold();
        int below = t / 2;
        int above = D.budget();
        assertTrue(below < t && above > t);
        int extinctBelow = 0;
        int extinctAbove = 0;
        for (long seed = 1; seed <= 100; seed++) {
            AlleeRelease small = AlleeRelease.marsh(D, seed);
            assertTrue(small.release(0, below));
            if (small.run().outcome() == Outcome.EXTINCT) {
                extinctBelow++;
            }
            AlleeRelease big = AlleeRelease.marsh(D, seed);
            assertTrue(big.release(0, above));
            if (big.run().outcome() == Outcome.EXTINCT) {
                extinctAbove++;
            }
        }
        assertTrue(extinctBelow >= 95, "below threshold extinct " + extinctBelow);
        assertTrue(extinctAbove <= 15, "above threshold extinct " + extinctAbove);
    }

    @Test
    void tricklingTheSameBirdsOutUsuallyFails() {
        int trickle = 0;
        for (long seed = 1; seed <= 100; seed++) {
            if (spread(seed, 20).outcome() == Outcome.EXTINCT) {
                trickle++;
            }
        }
        assertTrue(established(20) <= 35, "20 batches: " + established(20));
        assertTrue(trickle >= 40, "20 batches extinct: " + trickle);
    }

    @Test
    void theThinnerTheBatchesTheWorseTheOdds() {
        int last = Integer.MAX_VALUE;
        for (int years : new int[] {1, 2, 10, 20}) {
            int e = established(years);
            assertTrue(e <= last, years + " batches: " + e);
            last = e;
        }
    }

    @Test
    void growthIsBelowOneUnderTheAlleeThreshold() {
        AlleeRelease m = AlleeRelease.marsh(D, 1);
        int t = m.threshold();
        assertTrue(t > 1 && t < D.budget(), "threshold " + t);
        for (int n = 1; n < t; n++) {
            assertTrue(m.growth(n) < 1, "n=" + n);
        }
        assertTrue(m.growth(t) >= 1);
        assertTrue(m.growth(D.capacity()) < 1);
        assertEquals(0.0, m.growth(0), 0.0);
    }

    @Test
    void noMateFindingMeansNoThreshold() {
        Settings easy = new Settings(D.budget(), D.years(), D.survival(), 0, D.fledge(), D.capacity(), D.goal());
        AlleeRelease m = AlleeRelease.marsh(easy, 1);
        assertEquals(1, m.threshold());
    }

    @Test
    void theFlockNeverOutgrowsWhatTheMarshCanFledge() {
        for (long seed = 1; seed <= 5; seed++) {
            Report r = spread(seed, 1);
            int before = 0;
            for (Year y : r.years()) {
                assertTrue(y.fledged() <= 2 * y.nests());
                assertTrue(y.nests() <= (before + y.released()) / 2);
                before = y.flock();
            }
            assertTrue(r.peak() < 2 * D.capacity());
            assertTrue(r.flock() <= r.peak());
        }
    }

    @Test
    void noBirdsNoFlock() {
        Report r = AlleeRelease.marsh(D, 1).run();
        assertEquals(Outcome.EXTINCT, r.outcome());
        assertEquals(0, r.peak());
        assertEquals(Vegetation.SCRUB, r.band());
    }

    @Test
    void anEstablishedFlockKeepsTheMarshWet() {
        for (long seed = 1; seed <= 20; seed++) {
            Report r = spread(seed, 1);
            assertEquals(r.outcome() == Outcome.ESTABLISHED ? Vegetation.WETLAND : Vegetation.SCRUB, r.band());
        }
    }

    @Test
    void sameScheduleSameSeason() {
        for (long seed = 1; seed <= 10; seed++) {
            assertEquals(spread(seed, 2), spread(seed, 2));
            assertEquals(spread(seed, 10).years(), spread(seed, 10).years());
        }
    }

    @Test
    void theAviaryBudgetAndBadInputAreRefused() {
        AlleeRelease m = AlleeRelease.marsh(D, 1);
        assertTrue(m.release(0, 30));
        assertFalse(m.release(1, 11));
        assertFalse(m.release(D.years(), 1));
        assertFalse(m.release(-1, 1));
        assertFalse(m.release(2, 0));
        assertTrue(m.release(2, 10));
        assertEquals(0, m.left());
        assertThrows(IllegalArgumentException.class, () -> AlleeRelease.marsh(null, 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(40, 40, 1.2, 30, 1.0, 150, 50));
        assertThrows(IllegalArgumentException.class, () -> new Settings(40, 40, 0.75, 30, 1.0, 0, 50));
    }
}
