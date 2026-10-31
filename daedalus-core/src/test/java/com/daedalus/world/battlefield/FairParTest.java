package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class FairParTest {

    private static TranslocationPlan defaultPlan() {
        CraneCohorts flock = CraneCohorts.marsh(CraneCohorts.Settings.DEFAULT, 1);
        return TranslocationPlan.of(flock, TranslocationPlan.Settings.DEFAULT, 7);
    }

    @Test
    void parsSplitTenScoresByPercent() {
        double[] s = {0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0};
        FairPar.Pars p = FairPar.calibrate(s, 0.95);
        assertEquals(0.5, p.bronze());
        assertEquals(0.8, p.silver());
        assertEquals(0.95, p.gold()); // the top bot score beats the optimum cap, so gold is capped
        assertEquals(0.6, p.bronzeHit());
        assertEquals(0.3, p.silverHit());
        assertEquals(0.1, p.goldHit());
        assertEquals(0.5, p.median());
        assertTrue(!p.separated()); // gold equals the optimum
        assertTrue(FairPar.calibrate(new double[] {0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0}, 2).separated());
        assertEquals(FairPar.Tier.NONE, p.tier(0.45));
        assertEquals(FairPar.Tier.BRONZE, p.tier(0.5));
        assertEquals(FairPar.Tier.SILVER, p.tier(0.85));
        assertEquals(FairPar.Tier.PERFECT, p.tier(0.95));
    }

    @Test
    void botAlwaysSpendsTheWholeBudgetWithinTheYearlyCap() {
        for (int run = 0; run < 300; run++) {
            int[] s = FairPar.botSchedule(5, run, 10, 6, 5);
            int total = 0;
            for (int v : s) {
                assertTrue(v >= 0 && v <= 6);
                total += v;
            }
            assertEquals(10, total);
        }
        assertArrayEquals(new int[] {0, 0}, FairPar.botSchedule(5, 0, 0, 3, 2));
        assertThrows(IllegalArgumentException.class, () -> FairPar.botSchedule(5, 0, 11, 2, 5));
        assertThrows(IllegalArgumentException.class, () -> FairPar.calibrate(new double[0], 1));
    }

    @Test
    void translocationParsAreOrderedAndHitTheirShares() {
        FairPar.Pars p = FairPar.translocation(defaultPlan(), 200, 600);
        assertTrue(p.bronze() <= p.silver() && p.silver() <= p.gold() && p.gold() <= p.perfect());
        assertEquals(1 - 0.2025, p.perfect(), 1e-12);
        assertTrue(p.bronzeHit() >= 0.60 && p.silverHit() >= 0.25 && p.goldHit() >= 0.05);
        assertTrue(p.goldHit() < p.bronzeHit());
        // no release (survival 0.47) earns no tier; the exact best earns PERFECT
        assertEquals(FairPar.Tier.NONE, p.tier(0.47));
        assertEquals(FairPar.Tier.PERFECT, p.tier(1 - defaultPlan().best().risk()));
    }

    @Test
    void sameSeedSameParsAndScoresNeverBeatTheOptimum() {
        TranslocationPlan plan = defaultPlan();
        assertEquals(FairPar.translocation(plan, 80, 9), FairPar.translocation(plan, 80, 9));
        double best = 1 - plan.best().risk();
        for (double v : FairPar.translocationScores(plan, 80, 9)) {
            assertTrue(v <= best + 1e-12);
        }
    }

    @Test
    void reedReleaseParsAreOrdered() {
        ReedRelease rr = ReedRelease.of(ReedRelease.Settings.DEFAULT, 23);
        FairPar.Pars p = FairPar.reedRelease(rr, 60, 700);
        assertTrue(p.bronze() <= p.silver() && p.silver() <= p.gold() && p.gold() <= p.perfect());
        assertTrue(p.bronzeHit() >= 0.60);
    }

    @Test
    void marshTableCoversSixCabinetsInOrderWithOrderedPars() {
        var table = FairPar.marshTable();
        assertEquals(FairPar.MARSH_CABINETS, java.util.List.copyOf(table.keySet()));
        for (FairPar.Pars p : table.values()) {
            assertTrue(p.bronze() <= p.silver() && p.silver() <= p.gold() && p.gold() <= p.perfect());
            assertTrue(p.bronzeHit() >= 0.60 && p.silverHit() >= 0.25 && p.goldHit() >= 0.05);
        }
        assertEquals(1.0, table.get("DROUGHT01").perfect());
    }

    @Test
    void cohortOptimumTriesEverySplitAndGuessesScoreAtMostOne() {
        CraneCohorts flock = CraneCohorts.marsh(CraneCohorts.Settings.DEFAULT, 1);
        FairPar.Pars p = FairPar.cohorts(flock, 12, 100, 3);
        assertEquals(flock.adultEquivalents(new int[] {0, 0, 0, 12}), p.perfect()); // adults are worth the most here
        FairPar.Pars d = FairPar.droughtOdds(DroughtOdds.of(DroughtOdds.Settings.DEFAULT), 20, 100, 3);
        assertTrue(d.gold() <= 1 && d.bronze() > 0);
        assertThrows(IllegalArgumentException.class, () -> FairPar.reedCeiling(ReedCeiling.Settings.DEFAULT,
                new double[0], 5, 40, 17, 10, 1));
    }

    /**
     * G607 par regression guard: the marsh par board must equal the hand-kept rows in fair_par_guard.txt, which no
     * tool rewrites. A rule change that moves a par fails here, naming the par; edit the guard row on purpose.
     */
    @Test
    void parGuardHolds() throws IOException {
        Path guard = Path.of("..", "engines", "unreal", "core-test", "fair_par_guard.txt");
        Map<String, FairPar.Pars> table = FairPar.marshTable();
        List<String> moved = new ArrayList<>();
        int rows = 0;
        for (String line : Files.readAllLines(guard, StandardCharsets.UTF_8)) {
            if (!line.startsWith("marsh=")) {
                continue;
            }
            rows++;
            String[] f = line.split(" ");
            String id = f[0].substring("marsh=".length());
            FairPar.Pars p = table.get(id);
            if (p == null) {
                moved.add(id + ": guard row has no cabinet");
                continue;
            }
            double[] got = {p.bronze(), p.silver(), p.gold()};
            for (int t = 0; t < 3; t++) {
                String want = f[t + 1].substring(f[t + 1].indexOf('=') + 1);
                if (!want.equals(Double.toString(got[t]))) {
                    moved.add(id + ": " + f[t + 1].substring(0, f[t + 1].indexOf('=')) + " par moved " + want
                            + " -> " + got[t]);
                }
            }
        }
        assertEquals(FairPar.MARSH_CABINETS.size(), rows, "one guard row per marsh cabinet");
        assertEquals(List.of(), moved, "PAR GUARD (edit fair_par_guard.txt only on purpose)");
    }
}
