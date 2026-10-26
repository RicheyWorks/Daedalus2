// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.battlefield.FounderDrift.Generation;
import com.daedalus.world.battlefield.FounderDrift.Outcome;
import com.daedalus.world.battlefield.FounderDrift.Report;
import com.daedalus.world.battlefield.FounderDrift.Settings;
import java.util.List;
import java.util.function.Consumer;
import org.junit.jupiter.api.Test;

class FounderDriftTest {

    private static final Settings D = Settings.DEFAULT;
    private static final int SEEDS = 100;

    private static Report run(long seed, Consumer<FounderDrift> plan) {
        FounderDrift f = FounderDrift.aviary(D, seed);
        plan.accept(f);
        return f.run();
    }

    private static double meanRetained(Consumer<FounderDrift> plan) {
        double sum = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            sum += run(seed, plan).retained();
        }
        return sum / SEEDS;
    }

    private static int count(Consumer<FounderDrift> plan, Outcome o) {
        int n = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            if (run(seed, plan).outcome() == o) {
                n++;
            }
        }
        return n;
    }

    private static int established(Consumer<FounderDrift> plan) {
        int n = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            AlleeRelease m = AlleeRelease.marsh(run(seed, plan).marsh(AlleeRelease.Settings.DEFAULT), seed);
            assertTrue(m.release(0, 40));
            if (m.run().outcome() == AlleeRelease.Outcome.ESTABLISHED) {
                n++;
            }
        }
        return n;
    }

    private static final Consumer<FounderDrift> PLAIN = f -> { };
    private static final Consumer<FounderDrift> SKEW = f -> {
        for (int g = 1; g <= D.generations(); g++) {
            assertTrue(f.breed(g, 2, 18));
        }
    };
    private static final Consumer<FounderDrift> BOTTLENECK = f -> assertTrue(f.breed(5, 1, 1));
    private static final Consumer<FounderDrift> ONE_MIGRANT = f -> assertTrue(f.migrants(1));
    private static final Consumer<FounderDrift> TWO_MIGRANTS = f -> assertTrue(f.migrants(2));

    @Test
    void effectiveSizeAndHarmonicMeanMatchTheTextbook() {
        assertEquals(20.0, FounderDrift.effectiveSize(10, 10), 1e-12);
        assertEquals(7.2, FounderDrift.effectiveSize(2, 18), 1e-12);
        assertEquals(0.0, FounderDrift.effectiveSize(0, 5), 0.0);
        assertEquals(5.0, FounderDrift.harmonicMean(List.of(20.0, 20.0, 2.0)), 1e-12);
        assertEquals(0.0, FounderDrift.harmonicMean(List.of()), 0.0);
        assertEquals(Math.pow(1 - 1 / 40.0, 20), FounderDrift.aviary(D, 1).expectedRetained(), 1e-12);
    }

    @Test
    void foundersStartWithAllAllelesUnique() {
        Report r = run(1, PLAIN);
        assertEquals(1 - 1.0 / (2 * D.founders()), r.founderDiversity(), 1e-12);
        assertEquals(D.generations(), r.generations().size());
        assertTrue(r.generations().get(0).alleles() <= 2 * D.founders() * D.loci());
    }

    @Test
    void driftTracksTheOneOverTwoNeLaw() {
        for (Consumer<FounderDrift> plan : List.of(PLAIN, SKEW, BOTTLENECK)) {
            FounderDrift f = FounderDrift.aviary(D, 1);
            plan.accept(f);
            double expected = f.expectedRetained();
            double mean = meanRetained(plan);
            assertTrue(Math.abs(mean - expected) <= 0.05, "mean " + mean + " expected " + expected);
        }
    }

    @Test
    void aSkewedSexRatioOrOneBottleneckCostsDiversity() {
        double plain = meanRetained(PLAIN);
        assertTrue(meanRetained(SKEW) < plain - 0.2, "2 cocks : 18 hens");
        assertTrue(meanRetained(BOTTLENECK) < plain - 0.08, "one pair in generation 5");
        assertEquals(SEEDS, count(PLAIN, Outcome.INBRED));
    }

    @Test
    void migrantsFromOtherArksHoldDiversityUp() {
        assertTrue(meanRetained(ONE_MIGRANT) > meanRetained(PLAIN) + 0.15);
        assertEquals(0, count(ONE_MIGRANT, Outcome.INBRED));
        assertTrue(count(TWO_MIGRANTS, Outcome.DIVERSE) >= 90, "two migrants");
    }

    @Test
    void withoutMigrantsAllelesAreOnlyLost() {
        for (long seed = 1; seed <= 10; seed++) {
            int last = 2 * D.founders() * D.loci();
            for (Generation g : run(seed, SKEW).generations()) {
                assertTrue(g.alleles() <= last);
                assertEquals(0, g.migrants());
                last = g.alleles();
            }
        }
    }

    @Test
    void anInbredFlockFailsOnTheMarsh() {
        int plain = established(PLAIN);
        int two = established(TWO_MIGRANTS);
        assertTrue(plain <= 10, "inbred flock established " + plain);
        assertTrue(two >= 60, "two-migrant flock established " + two);
        assertTrue(established(ONE_MIGRANT) > plain);
    }

    @Test
    void survivalFallsWithInbreedingAndOnlySurvivalChanges() {
        Report inbred = run(1, PLAIN);
        Report diverse = run(1, TWO_MIGRANTS);
        assertTrue(inbred.inbreeding() > diverse.inbreeding());
        assertTrue(inbred.survival(0.75) < diverse.survival(0.75));
        assertTrue(diverse.survival(0.75) <= 0.75);
        AlleeRelease.Settings a = AlleeRelease.Settings.DEFAULT;
        AlleeRelease.Settings b = inbred.marsh(a);
        assertEquals(new AlleeRelease.Settings(a.budget(), a.years(), inbred.survival(a.survival()), a.mateHalf(),
                a.fledge(), a.capacity(), a.goal()), b);
    }

    @Test
    void sameSeedSamePlanSameStudbook() {
        for (long seed = 1; seed <= 5; seed++) {
            assertEquals(run(seed, ONE_MIGRANT), run(seed, ONE_MIGRANT));
            assertEquals(run(seed, SKEW).generations(), run(seed, SKEW).generations());
        }
    }

    @Test
    void theAviaryAndTheMigrantPoolAreRefusedWhenOverdrawn() {
        FounderDrift f = FounderDrift.aviary(D, 1);
        assertFalse(f.breed(0, 5, 5));
        assertFalse(f.breed(D.generations() + 1, 5, 5));
        assertFalse(f.breed(3, 11, 10));
        assertFalse(f.breed(3, 0, 10));
        assertTrue(f.breed(3, 5, 15));
        assertFalse(f.migrants(3));
        assertFalse(f.migrants(-1));
        assertTrue(f.migrants(2));
        assertThrows(IllegalArgumentException.class, () -> FounderDrift.aviary(null, 1));
        assertThrows(IllegalArgumentException.class, () -> new Settings(1, 20, 20, 40, 40, 0.2));
        assertThrows(IllegalArgumentException.class, () -> new Settings(20, 20, 20, 40, 40, -1));
        assertThrows(IllegalArgumentException.class, () -> FounderDrift.effectiveSize(-1, 3));
    }
}
