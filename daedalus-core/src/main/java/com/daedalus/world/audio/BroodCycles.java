// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Brood Cycles (contest G135): the regrown forest's long count.
 *
 * <p>Periodical cicadas emerge together every N years. Seeded predator populations boom on their own
 * 2-6 year cycles, and a predator that keeps meeting the brood can lock its booms onto the brood's phase.
 * The player picks the brood's cycle (10-18 years); each predator is scored at its worst-case phase over one
 * full joint cycle (N x predator years, i.e. predator-cycle-many emergences), counting emergences that meet
 * a boom with {@link BeatCoincidence}. Scores are meetings per {@link #PER_EMERGENCES} emergences, summed
 * over predators, so long and short cycles compare fairly. The best cycle minimises the score. This is the prime-cycle hypothesis: a cycle sharing a factor
 * with a predator's lets it lock on every time, while cycles coprime to every predator (13 and 17 always
 * are) meet each one only once per predator cycle length.
 *
 * <p>Ear rules: the emergence chorus is a low drone at {@link #CHORUS_HZ} Hz (real cicada choruses peak
 * near 1-1.5 kHz; compressed here for Richey's ear rule).
 */
public final class BroodCycles {
    /** Scores are meetings per this many emergences (divisible by every predator cycle 2-6). */
    public static final int PER_EMERGENCES = 60;
    /** Shortest and longest brood cycles on offer. */
    public static final int MIN_CYCLE = 10;
    /** Longest brood cycle on offer. */
    public static final int MAX_CYCLE = 18;
    /** Chorus drone pitch (E3). */
    public static final double CHORUS_HZ = 164.814;
    private static final long SALT = 0x4252_4431L; // "BRD1"

    /** A judged pick. */
    public record Verdict(boolean best, int meetings, int bestMeetings, List<Integer> bestCycles) {
        /** Defensive copy. */
        public Verdict {
            bestCycles = List.copyOf(bestCycles);
        }
    }

    private final long seed;
    private final List<Integer> predators;

    private BroodCycles(long seed, List<Integer> predators) {
        this.seed = seed;
        this.predators = List.copyOf(predators);
    }

    /** A seeded forest: 2-3 predators with distinct 2-6 year boom cycles. */
    public static BroodCycles seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        int n = 2 + (int) Long.remainderUnsigned(rng.nextLong(), 2);
        List<Integer> pool = new ArrayList<>(List.of(2, 3, 4, 5, 6));
        List<Integer> p = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            p.add(pool.remove((int) Long.remainderUnsigned(rng.nextLong(), pool.size())));
        }
        return new BroodCycles(seed, p);
    }

    /** A forest with explicit predator cycles. */
    public static BroodCycles of(List<Integer> predatorCycles) {
        for (int p : predatorCycles) {
            if (p < 2) {
                throw new IllegalArgumentException("predator cycle must be >= 2 years");
            }
        }
        return new BroodCycles(0, predatorCycles);
    }

    /** Chorus pitch (ear-rule checked). */
    public static double chorusHz() {
        return EarRule.check(CHORUS_HZ, "cicada chorus");
    }

    /** Emergences in one joint cycle (years 0, N, ... before N x predator) that meet a predator booming at {@code phase}. */
    public static int meetings(int cycle, int predator, int phase) {
        int[] periods = {cycle, predator};
        int[] offsets = {0, phase};
        int count = 0;
        long y = BeatCoincidence.next(periods, offsets, 0);
        long step = BeatCoincidence.lcm(periods);
        long horizon = (long) cycle * predator;
        while (y >= 0 && y < horizon) {
            count++;
            y += step;
        }
        return count;
    }

    /** Worst-case meetings per {@link #PER_EMERGENCES} emergences, summed over predators. */
    public int score(int cycle) {
        if (cycle < MIN_CYCLE || cycle > MAX_CYCLE) {
            throw new IllegalArgumentException("brood cycle " + MIN_CYCLE + "-" + MAX_CYCLE + " years");
        }
        int total = 0;
        for (int p : predators) {
            int worst = 0;
            for (int phase = 0; phase < p; phase++) {
                worst = Math.max(worst, meetings(cycle, p, phase));
            }
            total += PER_EMERGENCES * worst / p;
        }
        return total;
    }

    /** The seed (0 for authored forests). */
    public long seed() {
        return seed;
    }

    /** Predator boom cycles, years. */
    public List<Integer> predators() {
        return predators;
    }

    /** Every cycle with the fewest meetings. */
    public List<Integer> bestCycles() {
        int best = Integer.MAX_VALUE;
        List<Integer> out = new ArrayList<>();
        for (int n = MIN_CYCLE; n <= MAX_CYCLE; n++) {
            int s = score(n);
            if (s < best) {
                best = s;
                out.clear();
            }
            if (s == best) {
                out.add(n);
            }
        }
        return out;
    }

    /** Judge the player's brood cycle. */
    public Verdict judge(int cycle) {
        List<Integer> best = bestCycles();
        int bestScore = score(best.get(0));
        int s = score(cycle);
        return new Verdict(s == bestScore, s, bestScore, best);
    }
}