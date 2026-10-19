// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.MarkRecapture.Census;
import com.daedalus.world.battlefield.MarkRecapture.Settings;
import com.daedalus.world.battlefield.MarkRecapture.Verdict;
import org.junit.jupiter.api.Test;

class MarkRecaptureTest {

    private static final Settings D = Settings.DEFAULT;
    private static final int SEEDS = 200;

    private static Census census(Settings s, long seed, int a, int b) {
        MarkRecapture m = MarkRecapture.refuge(s, seed);
        assertTrue(m.plan(a, b));
        return m.run();
    }

    private static double meanChapman(Settings s, int a, int b) {
        double sum = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            sum += census(s, seed, a, b).chapman();
        }
        return sum / SEEDS;
    }

    private static double meanWidth(Settings s, int a, int b) {
        double sum = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            Census c = census(s, seed, a, b);
            sum += c.high() - c.low();
        }
        return sum / SEEDS;
    }

    private static int covered(Settings s) {
        int n = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            Census c = census(s, seed, 30, 30);
            if (c.low() <= c.truth() && c.truth() <= c.high()) {
                n++;
            }
        }
        return n;
    }

    private static int accurate(Settings s) {
        int n = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            if (census(s, seed, 30, 30).verdict() == Verdict.ACCURATE) {
                n++;
            }
        }
        return n;
    }

    @Test
    void theEstimatorsMatchTheTextbook() {
        assertEquals(200.0, MarkRecapture.lincolnPetersen(50, 40, 10), 1e-9);
        assertEquals(51.0 * 41 / 11 - 1, MarkRecapture.chapman(50, 40, 10), 1e-9);
        assertEquals(51.0 * 41 * 40 * 30 / (11.0 * 11 * 12), MarkRecapture.seberVariance(50, 40, 10), 1e-9);
        assertEquals(new Census(50, 40, 10, 200).chapman(), MarkRecapture.chapman(50, 40, 10), 0.0);
    }

    @Test
    void noRecapturesBreaksLincolnPetersenButNotChapman() {
        Census c = new Census(12, 9, 0, 240);
        assertEquals(Double.POSITIVE_INFINITY, c.lincolnPetersen());
        assertEquals(13.0 * 10 - 1, c.chapman(), 1e-9);
        assertTrue(Double.isFinite(c.high()));
        assertTrue(c.low() >= c.handled());
    }

    @Test
    void chapmanBeatsLincolnPetersenOnBiasWhenRecapturesAreFew() {
        Settings thin = new Settings(D.population(), 24, D.perTrap(), 0, 1, 0);
        double lp = 0;
        double ch = 0;
        int n = 0;
        int none = 0;
        for (long seed = 1; seed <= 400; seed++) {
            Census c = census(thin, seed, 12, 12);
            assertTrue(Double.isFinite(c.chapman()));
            if (c.recaptured() == 0) {
                none++;
                assertEquals(Double.POSITIVE_INFINITY, c.lincolnPetersen());
                continue;
            }
            n++;
            lp += c.lincolnPetersen();
            ch += c.chapman();
        }
        double truth = D.population();
        assertTrue(none >= 1, "some census with no recaptures");
        assertTrue(Math.abs(ch / n - truth) * 1.5 < Math.abs(lp / n - truth), "chapman " + ch / n + " lp " + lp / n);
        assertTrue(lp / n > truth * 1.1, "lincoln-petersen overcounts at small R: " + lp / n);
    }

    @Test
    void anHonestCensusIsNearlyUnbiased() {
        double mean = meanChapman(D, 30, 30);
        assertTrue(Math.abs(mean - D.population()) <= 0.05 * D.population(), "mean " + mean);
        assertTrue(accurate(D) >= 110, "accurate " + accurate(D));
    }

    @Test
    void theNinetyFivePercentBandUsuallyHoldsTheTruth() {
        assertTrue(covered(D) >= 165, "covered " + covered(D));
    }

    @Test
    void anEvenSplitGivesTheTightestBand() {
        double even = meanWidth(D, 30, 30);
        assertTrue(even < meanWidth(D, 10, 50), "even vs 10/50");
        assertTrue(even < meanWidth(D, 50, 10), "even vs 50/10");
        Settings poor = new Settings(D.population(), 20, D.perTrap(), 0, 1, 0);
        assertTrue(even < meanWidth(poor, 10, 10) / 2, "60 vs 20 trap-nights");
    }

    @Test
    void lostTagsAndTurnoverInflateTheCount() {
        double n = D.population();
        assertTrue(meanChapman(D.with(0.3, 1, 0), 30, 30) > 1.25 * n, "tag loss");
        assertTrue(meanChapman(D.with(0, 1, 0.3), 30, 30) > 1.25 * n, "turnover");
        assertTrue(accurate(D.with(0.3, 1, 0)) <= 60, "tag loss accurate " + accurate(D.with(0.3, 1, 0)));
    }

    @Test
    void trapShyHaresInflateAndTrapHappyHaresShrinkTheCount() {
        double n = D.population();
        assertTrue(meanChapman(D.with(0, 0.5, 0), 30, 30) > 1.4 * n, "trap-shy");
        assertTrue(meanChapman(D.with(0, 2, 0), 30, 30) < 0.75 * n, "trap-happy");
        assertTrue(covered(D.with(0, 2, 0)) <= 20, "trap-happy hares give a tight, wrong band");
    }

    @Test
    void aQuotaFromTheLowerBoundIsSafeAndOneFromThePointEstimateIsNot() {
        int greedyOver = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            Census c = census(D, seed, 30, 30);
            assertTrue(c.safe(c.quota(0.1), 0.1), "lower-bound quota overharvests, seed " + seed);
            assertEquals(Vegetation.MEADOW, c.band(0.1));
            if (!c.safe(c.greedyQuota(0.1), 0.1)) {
                greedyOver++;
            }
            Census thin = census(new Settings(D.population(), 20, D.perTrap(), 0, 1, 0), seed, 10, 10);
            assertTrue(thin.safe(thin.quota(0.1), 0.1), "thin census lower-bound quota, seed " + seed);
        }
        assertTrue(greedyOver >= 50, "point-estimate quota overharvests " + greedyOver);
        Census biased = census(D.with(0, 0.5, 0), 3, 30, 30);
        assertEquals(biased.safe(biased.quota(0.1), 0.1) ? Vegetation.MEADOW : Vegetation.SCRUB, biased.band(0.1));
    }

    @Test
    void theCountsAreConsistent() {
        for (long seed = 1; seed <= 50; seed++) {
            Census c = census(D.with(0.2, 0.7, 0.1), seed, 25, 35);
            assertTrue(c.recaptured() <= Math.min(c.marked(), c.caught()));
            assertTrue(c.marked() <= D.population() && c.caught() <= D.population());
            assertTrue(c.low() <= c.high());
            assertTrue(c.low() >= c.handled());
        }
    }

    @Test
    void sameSeedSamePlanSameCensus() {
        for (long seed = 1; seed <= 20; seed++) {
            assertEquals(census(D, seed, 30, 30), census(D, seed, 30, 30));
            assertEquals(census(D.with(0.1, 1.5, 0.2), seed, 20, 40), census(D.with(0.1, 1.5, 0.2), seed, 20, 40));
        }
        assertEquals(census(D, 7, 30, 30), MarkRecapture.refuge(D, 7).run());
    }

    @Test
    void badPlansAndSettingsAreRefused() {
        MarkRecapture m = MarkRecapture.refuge(D, 1);
        assertFalse(m.plan(0, 30));
        assertFalse(m.plan(30, 0));
        assertFalse(m.plan(31, 30));
        assertTrue(m.plan(20, 40));
        assertThrows(IllegalArgumentException.class, () -> MarkRecapture.refuge(null, 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(0, 60, 0.012, 0, 1, 0));
        assertThrows(IllegalArgumentException.class, () -> new Settings(240, 60, 1.0, 0, 1, 0));
        assertThrows(IllegalArgumentException.class, () -> new Settings(240, 60, 0.012, 1.5, 1, 0));
        assertThrows(IllegalArgumentException.class, () -> MarkRecapture.chapman(10, 5, 6));
    }
}
