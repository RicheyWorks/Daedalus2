// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.AshfallRegrowth.Band;
import com.daedalus.world.battlefield.AshfallRegrowth.Outcome;
import com.daedalus.world.battlefield.AshfallRegrowth.Plan;
import com.daedalus.world.battlefield.AshfallRegrowth.Report;
import com.daedalus.world.battlefield.AshfallRegrowth.Settings;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class AshfallRegrowthTest {

    private static final Settings D = Settings.DEFAULT;
    /** Same as the default but no lightning, so growth alone is tested. */
    private static final Settings CALM = with(0.0, D.caches(), D.cacheRadius(), D.herds());

    private static Settings with(double strike, int caches, int cacheRadius, int herds) {
        return new Settings(D.yearsPerSeason(), D.seedReach(), cacheRadius, caches, D.waterPerSeason(), D.waterRadius(),
                D.carryCells(), D.waterBoost(), herds, D.grazeRadius(), strike, D.dryWind(), D.maxFireTicks(),
                D.oldGrowthTarget(), D.scorchedAt(), D.maxSeasons());
    }

    /** 16 x 16 fragment, 1 m cells: a shore of water down the west edge and one spring pool at (8,8). */
    private static BattlefieldEcology fragment() {
        BattlefieldEcology f = new BattlefieldEcology(16, 16, 100, 0, 0, 7);
        for (int j = 0; j < 16; j++) {
            f.set(0, j, Vegetation.WETLAND);
            for (int i = 1; i < 16; i++) {
                f.set(i, j, Vegetation.OAK);   // the forest before the impact; the scorch takes it all
            }
        }
        f.set(8, 8, Vegetation.WETLAND);
        return f;
    }

    private static double c(int cell) { return cell * 100 + 50; }

    private static final Plan SEEDS = (g, s) -> {
        if (s == 0) {
            g.seedCache(c(3), c(3));
            g.seedCache(c(12), c(3));
            g.seedCache(c(3), c(12));
            g.seedCache(c(12), c(12));
        }
    };

    private static final Plan FULL = (g, s) -> {
        SEEDS.before(g, s);
        if (s == 0) {
            g.graze(c(8), c(3));
            g.graze(c(8), c(12));
        }
        g.water(c(2), c(5));
        g.water(c(2), c(10));
        g.water(c(9), c(9));
    };

    private static int count(AshfallRegrowth g, Band b) {
        int n = 0;
        for (int j = 0; j < 16; j++) {
            for (int i = 0; i < 16; i++) {
                if (g.band(i, j) == b) {
                    n++;
                }
            }
        }
        return n;
    }

    @Test
    void theImpactScorchesTheLandToAsh_andLeavesTheWater() {
        BattlefieldEcology f = fragment();
        AshfallRegrowth g = AshfallRegrowth.scorch(f, CALM, 1);
        assertEquals(16 + 1, count(g, Band.WATER));
        assertEquals(256 - 17, count(g, Band.ASH));
        assertEquals(256 - 17, g.land());
        assertEquals(Vegetation.BARE, f.vegetation(5, 5));
        assertEquals(Vegetation.WETLAND, f.vegetation(8, 8));
        assertEquals(0.0, g.fuel(), 1e-12);
    }

    @Test
    void withoutAnArkSeedCacheTheAshStaysSterile() {
        AshfallRegrowth g = AshfallRegrowth.scorch(fragment(), CALM, 1);
        Report r = g.play(null);
        assertEquals(Outcome.GROWING, r.outcome());
        assertEquals(D.maxSeasons(), r.seasons());
        assertEquals(g.land(), r.census().get(Band.ASH));
        assertEquals(0.0, r.oldGrowth(), 1e-12);
    }

    @Test
    void aSeedCachePlantsMeadow_andSeedRainSpreadsOutwardSeasonBySeason() {
        AshfallRegrowth g = AshfallRegrowth.scorch(fragment(), CALM, 1);
        assertEquals(9, g.seedCache(c(12), c(12)));
        assertEquals(Band.MEADOW, g.band(13, 13));
        assertEquals(Band.ASH, g.band(12, 9));
        g.season();
        assertEquals(Band.MEADOW, g.band(12, 9), "3 cells out: within seed reach of the cache");
        assertEquals(Band.ASH, g.band(12, 8), "4 cells out: not yet");
        g.season();
        assertEquals(Band.MEADOW, g.band(12, 8));
        assertEquals(Band.ASH, g.band(3, 3), "far side of the fragment is still bare");
    }

    @Test
    void dryGroundClimbsMeadowBramblePineOak_inOrder() {
        AshfallRegrowth g = AshfallRegrowth.scorch(fragment(), CALM, 1);
        g.seedCache(c(12), c(12));
        List<Band> seen = new ArrayList<>(List.of(g.band(12, 12)));
        for (int s = 0; s < 30; s++) {
            g.season();
            Band b = g.band(12, 12);
            if (b != seen.get(seen.size() - 1)) {
                seen.add(b);
            }
        }
        assertEquals(List.of(Band.MEADOW, Band.BRAMBLE, Band.PINE, Band.OAK), seen);
    }

    @Test
    void besideWaterMeadowGrowsIntoWillow_whichNeverBurns() {
        AshfallRegrowth g = AshfallRegrowth.scorch(fragment(), CALM, 1);
        g.seedCache(c(2), c(5));
        List<Band> seen = new ArrayList<>(List.of(g.band(1, 5)));
        for (int s = 0; s < 10; s++) {
            g.season();
            if (g.band(1, 5) != seen.get(seen.size() - 1)) {
                seen.add(g.band(1, 5));
            }
        }
        assertEquals(List.of(Band.MEADOW, Band.WILLOW), seen);
        assertEquals(0, g.wind(1, 0).strike(c(1), c(5)));
        assertEquals(Band.WILLOW, g.band(1, 5));
    }

    @Test
    void carriedWaterSpeedsGrowth_butOnlyNearASource_andOnlySoManyCarriesASeason() {
        AshfallRegrowth dry = AshfallRegrowth.scorch(fragment(), CALM, 1);
        AshfallRegrowth wet = AshfallRegrowth.scorch(fragment(), CALM, 1);
        dry.seedCache(c(3), c(4));
        wet.seedCache(c(3), c(4));
        int dryPine = -1;
        int wetPine = -1;
        for (int s = 1; s <= 20; s++) {
            assertTrue(wet.water(c(3), c(4)));
            dry.season();
            wet.season();
            if (dryPine < 0 && dry.band(3, 4) == Band.PINE) {
                dryPine = s;
            }
            if (wetPine < 0 && wet.band(3, 4) == Band.PINE) {
                wetPine = s;
            }
        }
        assertTrue(wetPine > 0 && dryPine > wetPine, "watered " + wetPine + " vs dry " + dryPine);

        AshfallRegrowth g = AshfallRegrowth.scorch(fragment(), CALM, 1);
        assertFalse(g.water(c(14), c(14)), "6 cells from the spring: too far to carry");
        assertTrue(g.water(c(2), c(2)));
        assertTrue(g.water(c(2), c(6)));
        assertTrue(g.water(c(2), c(10)));
        assertFalse(g.water(c(2), c(14)), "three carries a season");
        g.season();
        assertTrue(g.water(c(2), c(14)), "carries come back next season");
    }

    @Test
    void grazersHoldTheTurfAtMeadow_andTheCroppedStripStopsAWindDrivenFire() {
        Settings s = with(0.0, 1, 8, 6);
        int[] rightAlive = new int[2];
        for (int herds = 0; herds <= 1; herds++) {
            AshfallRegrowth g = AshfallRegrowth.scorch(new BattlefieldEcology(16, 16, 100, 0, 0, 3), s, 1);
            g.seedCache(c(8), c(8));
            g.season();
            g.season();
            if (herds == 1) {
                for (int j = 1; j <= 16; j += 3) {
                    assertTrue(g.graze(c(8), c(j)));
                }
                assertFalse(g.graze(c(4), c(4)), "six herds only");
            }
            int before = 0;
            for (int j = 0; j < 16; j++) {
                for (int i = 10; i < 16; i++) {
                    before += g.band(i, j) == Band.ASH ? 0 : 1;
                }
            }
            assertEquals(96, before);
            assertTrue(g.wind(1, 0).strike(c(2), c(8)) > 0);
            for (int j = 0; j < 16; j++) {
                for (int i = 10; i < 16; i++) {
                    rightAlive[herds] += g.band(i, j) == Band.ASH ? 0 : 1;
                }
            }
            if (herds == 1) {
                for (int k = 0; k < 10; k++) {
                    g.season();
                }
                assertEquals(Band.MEADOW, g.band(8, 7), "grazed turf never grows into bramble");
                assertTrue(g.grazed(8, 7));
            }
        }
        assertEquals(96, rightAlive[1], "the strip held");
        assertTrue(rightAlive[0] < 96, "without it the fire crossed: " + rightAlive[0]);
    }

    @Test
    void theFuelLoadPeaksInYoungMeadow_andGrazingOrWaterCutsIt() {
        AshfallRegrowth g = AshfallRegrowth.scorch(fragment(), CALM, 1);
        g.seedCache(c(8), c(4));
        g.season();
        g.season();
        g.season();
        double young = g.fuel();
        AshfallRegrowth grazed = AshfallRegrowth.scorch(fragment(), CALM, 1);
        grazed.seedCache(c(8), c(4));
        grazed.season();
        grazed.season();
        grazed.season();
        grazed.graze(c(8), c(4));
        assertTrue(grazed.fuel() < young);
        for (int s = 0; s < 30; s++) {
            g.season();
        }
        assertTrue(g.fuel() < young, "mature oak and willow carry less fire than young meadow and bramble");
    }

    @Test
    void lightningFollowsTheFuel_soBareAshIsNeverStruck() {
        AshfallRegrowth g = AshfallRegrowth.scorch(fragment(), with(1.0, D.caches(), D.cacheRadius(), D.herds()), 5);
        for (int s = 0; s < 40; s++) {
            assertFalse(g.season().struck());
        }
        assertEquals(0, g.report().strikes());
    }

    @Test
    void aPlannedRecoveryRestoresTheFragment_andTheFullToolkitBurnsLess() {
        int restoredFull = 0;
        int restoredSeeds = 0;
        int burntFull = 0;
        int burntSeeds = 0;
        for (long seed = 1; seed <= 20; seed++) {
            Report full = AshfallRegrowth.scorch(fragment(), D, seed).play(FULL);
            Report seeds = AshfallRegrowth.scorch(fragment(), D, seed).play(SEEDS);
            restoredFull += full.outcome() == Outcome.RESTORED ? 1 : 0;
            restoredSeeds += seeds.outcome() == Outcome.RESTORED ? 1 : 0;
            burntFull += full.burnt();
            burntSeeds += seeds.burnt();
            if (full.outcome() == Outcome.RESTORED) {
                assertTrue(full.oldGrowth() >= D.oldGrowthTarget());
                assertTrue(full.seasons() < D.maxSeasons());
            }
        }
        assertTrue(restoredFull >= 19, "full toolkit restored " + restoredFull + "/20");
        assertTrue(restoredFull >= restoredSeeds);
        assertTrue(burntFull < burntSeeds, "burnt " + burntFull + " vs " + burntSeeds);
    }

    @Test
    void wildfireCanScorchTheFragmentAgain() {
        boolean scorched = false;
        for (long seed = 1; seed <= 40 && !scorched; seed++) {
            Report r = AshfallRegrowth.scorch(fragment(), D, seed).play(SEEDS);
            if (r.outcome() == Outcome.SCORCHED) {
                scorched = true;
                assertTrue(r.burnt() >= D.scorchedAt() * (256 - 17));
                assertTrue(r.strikes() > 0);
            }
        }
        assertTrue(scorched, "an unguarded recovery sometimes burns out");
    }

    @Test
    void sameSeedSameRun_differentSeedsDiffer() {
        Report a = AshfallRegrowth.scorch(fragment(), D, 3).play(FULL);
        Report b = AshfallRegrowth.scorch(fragment(), D, 3).play(FULL);
        assertEquals(a, b);
        boolean differs = false;
        for (long seed = 4; seed < 14 && !differs; seed++) {
            differs = !AshfallRegrowth.scorch(fragment(), D, seed).play(FULL).equals(a);
        }
        assertTrue(differs);
    }

    @Test
    void theHostFieldMirrorsTheBands_soCoverAndDbeSnapshotsSeeTheRecovery() {
        BattlefieldEcology f = fragment();
        AshfallRegrowth g = AshfallRegrowth.scorch(f, CALM, 1);
        g.seedCache(c(12), c(12));
        for (int s = 0; s < 12; s++) {
            g.season();
        }
        for (int j = 0; j < 16; j++) {
            for (int i = 0; i < 16; i++) {
                assertEquals(g.band(i, j).vegetation(), f.vegetation(i, j), i + "," + j);
            }
        }
        assertTrue(f.coverAt(c(12), c(12)) > 0);
        assertNotEquals(-1, Dbe.write(f).indexOf("row 12"));
    }

    @Test
    void budgetsAreFinite_andBadInputIsRefused() {
        AshfallRegrowth g = AshfallRegrowth.scorch(fragment(), with(0.0, 1, 1, 1), 1);
        assertTrue(g.seedCache(c(5), c(5)) > 0);
        assertEquals(-1, g.seedCache(c(10), c(10)));
        assertEquals(0, g.cachesLeft());
        assertTrue(g.graze(c(5), c(5)));
        assertFalse(g.graze(c(10), c(10)));
        assertEquals(0, g.herdsLeft());
        assertThrows(IllegalArgumentException.class, () -> AshfallRegrowth.scorch(null, D, 1));
        assertThrows(IllegalArgumentException.class, () -> AshfallRegrowth.scorch(fragment(), null, 1));
        assertThrows(IllegalArgumentException.class, () -> with(1.5, 1, 1, 1));
        assertThrows(IllegalArgumentException.class, () -> with(0.5, -1, 1, 1));
        assertThrows(IndexOutOfBoundsException.class, () -> g.band(16, 0));
    }
}
