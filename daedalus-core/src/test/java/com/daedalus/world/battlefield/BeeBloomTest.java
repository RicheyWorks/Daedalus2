// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.BeeBloom.Day;
import com.daedalus.world.battlefield.BeeBloom.Flora;
import com.daedalus.world.battlefield.BeeBloom.Outcome;
import com.daedalus.world.battlefield.BeeBloom.Report;
import com.daedalus.world.battlefield.BeeBloom.Settings;
import org.junit.jupiter.api.Test;

class BeeBloomTest {

    private static final Settings D = Settings.DEFAULT;

    private static Settings with(double frostChance, int syrupDays) {
        return new Settings(D.days(), D.coldC(), D.peakC(), D.noiseC(), frostChance, D.frostFrom(), D.frostTo(),
                D.baseC(), D.flightC(), D.hiveWakeGdd(), D.visitsPerHive(), D.starveDays(), syrupDays, D.beds(),
                D.hives(), D.thriveSet());
    }

    /** A bloom calendar with no gaps: catkins and crocus early, clover, bramble, heather late. */
    private static BeeBloom calendar(Settings s, long seed, int hives) {
        BeeBloom b = BeeBloom.season(s, seed);
        assertTrue(b.sow(Flora.WILLOW_CATKIN, 1));
        assertTrue(b.sow(Flora.CROCUS, 1));
        assertTrue(b.sow(Flora.CLOVER, 2));
        assertTrue(b.sow(Flora.BRAMBLE, 1));
        assertTrue(b.sow(Flora.HEATHER, 1));
        assertTrue(b.hive(hives));
        return b;
    }

    @Test
    void theSeasonIsAWarmArc_withAtMostOneLateFrost() {
        double[] t = BeeBloom.season(with(1.0, 0), 4).temperatures();
        assertEquals(D.days(), t.length);
        assertTrue(t[75] > t[0] + 10, "midsummer is warm");
        int frosts = 0;
        for (int d = 0; d < t.length; d++) {
            if (t[d] < 0) {
                frosts++;
                assertTrue(d >= D.frostFrom() && d <= D.frostTo());
            }
        }
        assertEquals(1, frosts);
        double[] calm = BeeBloom.season(with(0.0, 0), 4).temperatures();
        for (double c : calm) {
            assertTrue(c >= 0);
        }
    }

    @Test
    void degreeDaysAddUpTheWarmthAboveTheBase() {
        Report r = calendar(with(0.0, 0), 2, 3).run();
        double[] t = BeeBloom.season(with(0.0, 0), 2).temperatures();
        double gdd = 0;
        for (Day d : r.days()) {
            gdd += Math.max(0, t[d.index()] - D.baseC());
            assertEquals(gdd, d.gdd(), 1e-9);
        }
        assertTrue(gdd > Flora.HEATHER.fromGdd(), "the season reaches the late bloom");
    }

    @Test
    void aBloomCalendarWithNoGapsKeepsEveryHiveAlive_andSetsSeed() {
        for (long seed = 1; seed <= 5; seed++) {
            Report r = calendar(with(0.0, 0), seed, 3).run();
            assertEquals(Outcome.THRIVING, r.outcome(), "seed " + seed);
            assertEquals(3, r.hivesAlive());
            assertTrue(r.meanSeedSet() >= D.thriveSet());
        }
    }

    @Test
    void onlyLateFlowers_theHivesStarveBeforeTheyOpen() {
        BeeBloom b = BeeBloom.season(with(0.0, 0), 1);
        b.sow(Flora.HEATHER, 6);
        b.hive(3);
        Report r = b.run();
        assertEquals(Outcome.COLLAPSED, r.outcome());
        assertEquals(0.0, r.seedSet().get(Flora.HEATHER));
    }

    @Test
    void aLateFrostKillsTheOpenBlooms_andTheirSeedStopsThere() {
        Report calm = calendar(with(0.0, 0), 1, 3).run();
        Report frost = calendar(with(1.0, 0), 1, 3).run();
        assertTrue(frost.frostDay() >= 0);
        assertEquals(-1, calm.frostDay());
        assertTrue(frost.meanSeedSet() < calm.meanSeedSet());
        double early = frost.seedSet().get(Flora.WILLOW_CATKIN) + frost.seedSet().get(Flora.CROCUS)
                + frost.seedSet().get(Flora.CLOVER);
        double earlyCalm = calm.seedSet().get(Flora.WILLOW_CATKIN) + calm.seedSet().get(Flora.CROCUS)
                + calm.seedSet().get(Flora.CLOVER);
        assertTrue(early < earlyCalm);
        Day after = frost.days().get(frost.frostDay());
        assertTrue(after.frost());
        assertEquals(0, after.openBeds(), "every open bloom died that day");
    }

    @Test
    void syrupBridgesTheBloomGapAFrostLeaves() {
        int starved = 0;
        int fed = 0;
        for (long seed = 1; seed <= 8; seed++) {
            starved += calendar(with(1.0, 0), seed, 3).run().hivesAlive();
            fed += calendar(with(1.0, 20), seed, 3).run().hivesAlive();
        }
        assertTrue(fed > starved, "fed " + fed + " vs " + starved);
    }

    @Test
    void moreHivesSetMoreSeed() {
        double one = 0;
        double three = 0;
        for (long seed = 1; seed <= 5; seed++) {
            one += calendar(with(0.0, 0), seed, 1).run().meanSeedSet();
            three += calendar(with(0.0, 0), seed, 3).run().meanSeedSet();
        }
        assertTrue(three > one);
    }

    @Test
    void beesFlyOnlyOnWarmDaysAfterTheyWake() {
        Report r = calendar(with(1.0, 0), 3, 3).run();
        int flights = 0;
        for (Day d : r.days()) {
            if (d.flying()) {
                flights++;
                assertTrue(d.tempC() >= D.flightC());
                assertTrue(d.gdd() >= D.hiveWakeGdd());
            }
        }
        assertTrue(flights > 0);
        Report none = BeeBloom.season(D, 3).run();
        assertEquals(Outcome.PATCHY, none.outcome(), "no hives placed, nothing to collapse");
        assertEquals(0.0, none.meanSeedSet());
    }

    @Test
    void noBeesNoSeed() {
        BeeBloom b = BeeBloom.season(with(0.0, 0), 1);
        b.sow(Flora.CLOVER, 3);
        Report r = b.run();
        assertEquals(0.0, r.seedSet().get(Flora.CLOVER));
    }

    @Test
    void sameSeasonSameResult() {
        assertEquals(calendar(D, 9, 3).run(), calendar(D, 9, 3).run());
    }

    @Test
    void bedsAndHivesAreBudgeted_andBadInputIsRefused() {
        BeeBloom b = BeeBloom.season(D, 1);
        assertTrue(b.sow(Flora.CLOVER, 6));
        assertFalse(b.sow(Flora.HEATHER, 1));
        assertEquals(0, b.bedsLeft());
        assertTrue(b.hive(3));
        assertFalse(b.hive(1));
        assertFalse(b.sow(null, 1));
        assertFalse(b.hive(0));
        assertThrows(IllegalArgumentException.class, () -> BeeBloom.season(null, 1));
        assertThrows(IllegalArgumentException.class, () -> with(1.5, 0));
        assertThrows(IllegalArgumentException.class, () -> with(0.5, -1));
    }
}
