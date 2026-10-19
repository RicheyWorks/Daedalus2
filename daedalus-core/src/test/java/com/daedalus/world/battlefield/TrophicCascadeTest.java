// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.TrophicCascade.Outcome;
import com.daedalus.world.battlefield.TrophicCascade.Report;
import com.daedalus.world.battlefield.TrophicCascade.Settings;
import com.daedalus.world.battlefield.TrophicCascade.Year;
import org.junit.jupiter.api.Test;

class TrophicCascadeTest {

    private static final Settings D = Settings.DEFAULT;

    private static Settings fearless() {
        return new Settings(D.years(), D.reaches(), D.elkStart(), D.elkCap(), D.elkRate(), D.winterNoise(),
                D.attack(), D.handling(), D.conversion(), D.wolfMortality(), D.wolfCap(), D.browse(), 0.0,
                D.willowStart(), D.willowGrowth(), D.sprout(), D.beaverWater(), D.beaverEat(), D.beaverSettle(),
                D.beaverLeave(), D.maxColonies(), D.elkFloor(), D.cascadeWillow(), D.packs(), D.fences());
    }

    private static Report wolves(Settings s, long seed) {
        TrophicCascade t = TrophicCascade.valley(s, seed);
        assertTrue(t.release(0, 6));
        return t.run();
    }

    @Test
    void withoutWolvesTheElkBrowseTheBanksBare() {
        for (long seed = 1; seed <= 3; seed++) {
            Report r = TrophicCascade.valley(D, seed).run();
            assertEquals(Outcome.BROWSED, r.outcome());
            assertTrue(r.elk() > 0.9 * D.elkCap());
            assertEquals(0, r.colonies());
            assertEquals(Vegetation.BARE, r.band(0));
        }
    }

    @Test
    void theArkWolvesBringTheWillowAndTheBeaversBack() {
        for (long seed = 1; seed <= 5; seed++) {
            Report r = wolves(D, seed);
            assertEquals(Outcome.CASCADE, r.outcome(), "seed " + seed);
            assertTrue(r.wolves() >= 1);
            assertTrue(r.elk() >= D.elkFloor() && r.elk() < D.elkCap());
            assertTrue(r.meanWillow() >= D.cascadeWillow());
            assertTrue(r.colonies() >= 1);
            assertEquals(Vegetation.WETLAND, r.band(0), "the first reach to recover gets the first colony");
        }
    }

    @Test
    void itIsTheFearNotTheHeadCount() {
        Report fear = wolves(D, 1);
        Report noFear = wolves(fearless(), 1);
        assertEquals(fear.elk(), noFear.elk(), 1e-9, "fear changes behaviour, not the elk numbers");
        assertEquals(Outcome.BROWSED, noFear.outcome());
        TrophicCascade hunted = TrophicCascade.valley(D, 1);
        assertTrue(hunted.cull(60));
        Report cull = hunted.run();
        assertTrue(cull.elk() < fear.elk(), "hunters leave fewer elk than the wolves do");
        assertEquals(Outcome.BROWSED, cull.outcome(), "and the willow still does not come back");
    }

    @Test
    void wolvesKillWithASaturatingResponse_andTheirNumbersSettle() {
        Report r = wolves(D, 2);
        for (Year y : r.years()) {
            assertTrue(y.wolves() <= D.wolfCap());
            assertTrue(y.kills() <= D.wolfCap() / D.handling(), "no wolf kills faster than 1/h");
        }
        double late = r.years().get(D.years() - 1).wolves();
        double before = r.years().get(D.years() - 6).wolves();
        assertTrue(Math.abs(late - before) < 2, "the pack settles");
    }

    @Test
    void fencedReachesRecoverOnTheirOwn() {
        TrophicCascade t = TrophicCascade.valley(D, 1);
        assertTrue(t.fence(3));
        assertTrue(t.fence(7));
        Report r = t.run();
        assertEquals(Outcome.PARTIAL, r.outcome());
        assertTrue(r.willow().get(3) >= D.beaverSettle());
        assertTrue(r.willow().get(7) >= D.beaverSettle());
        assertEquals(0.0, r.willow().get(0), 1e-9);
        assertEquals(Vegetation.BARE, r.band(0));
    }

    @Test
    void wolvesAndHuntersTogetherCrashTheElk() {
        TrophicCascade t = TrophicCascade.valley(D, 1);
        assertTrue(t.release(0, 12));
        assertTrue(t.cull(200));
        Report r = t.run();
        assertEquals(Outcome.CRASHED, r.outcome());
        assertTrue(r.elk() < D.elkFloor());
    }

    @Test
    void releasedWolvesThatDieOutAreACrash() {
        Settings starving = new Settings(D.years(), D.reaches(), D.elkStart(), D.elkCap(), D.elkRate(),
                D.winterNoise(), 0.0, D.handling(), D.conversion(), D.wolfMortality(), D.wolfCap(), D.browse(),
                D.fear(), D.willowStart(), D.willowGrowth(), D.sprout(), D.beaverWater(), D.beaverEat(),
                D.beaverSettle(), D.beaverLeave(), D.maxColonies(), D.elkFloor(), D.cascadeWillow(), D.packs(),
                D.fences());
        Report r = wolves(starving, 1);
        assertEquals(0.0, r.wolves());
        assertEquals(Outcome.CRASHED, r.outcome());
    }

    @Test
    void bandsFollowTheWillowCover() {
        Report r = wolves(D, 3);
        for (int i = 0; i < D.reaches(); i++) {
            Vegetation v = r.band(i);
            if (r.beaver().get(i)) {
                assertEquals(Vegetation.WETLAND, v);
            } else if (r.willow().get(i) >= 0.5) {
                assertEquals(Vegetation.SCRUB, v);
            }
        }
        assertEquals(D.years(), r.years().size());
        assertEquals(r.colonies(), r.years().get(D.years() - 1).colonies());
    }

    @Test
    void sameValleySameResult_andWintersDifferBySeed() {
        assertEquals(wolves(D, 4), wolves(D, 4));
        assertTrue(wolves(D, 4).elk() != wolves(D, 5).elk());
    }

    @Test
    void wolvesAndFencesAreBudgeted_andBadInputIsRefused() {
        TrophicCascade t = TrophicCascade.valley(D, 1);
        assertTrue(t.release(0, 8));
        assertFalse(t.release(5, 5));
        assertTrue(t.release(5, 4));
        assertEquals(0, t.wolvesLeft());
        assertFalse(t.release(D.years(), 1));
        assertFalse(t.release(-1, 1));
        assertTrue(t.fence(0));
        assertFalse(t.fence(0));
        assertTrue(t.fence(1));
        assertTrue(t.fence(2));
        assertFalse(t.fence(3));
        assertEquals(0, t.fencesLeft());
        assertFalse(t.fence(-1));
        assertFalse(t.cull(-1));
        assertFalse(t.cull(Double.NaN));
        assertFalse(t.cull(Double.POSITIVE_INFINITY));
        assertThrows(IllegalArgumentException.class, () -> TrophicCascade.valley(null, 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(0, 10, 700, 800, 0.3, 0.3, 0.02, 0.05,
                0.05, 0.35, 30, 0.0015, 0.3, 0.15, 0.35, 0.02, 0.05, 0.03, 0.6, 0.2, 4, 50, 0.6, 12, 3));
        assertThrows(IllegalArgumentException.class, () -> new Settings(30, 2, 700, 800, 0.3, 0.3, 0.02, 0.05,
                0.05, 0.35, 30, 0.0015, 0.3, 0.15, 0.35, 0.02, 0.05, 0.03, 0.6, 0.2, 4, 50, 0.6, 12, 3));
    }
}
