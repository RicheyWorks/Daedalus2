// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Buzz Garden (contest G145): the regrown garden needs its buzzers.
 *
 * <p>Some flowers (blueberry, tomato, potato, eggplant, shooting star) keep their pollen in pored anthers
 * that only release it when a bee grips the flower and buzzes at the right frequency (buzz pollination, or
 * sonication, roughly 200-400 Hz). A seeded garden has {@link #PAIRS} flowers, each with a best buzz
 * frequency, and {@link #PAIRS} bees, each buzzing at its own pitch. The player matches bees to flowers one
 * to one; pollen released per pair falls off with the mismatch ({@link #pollen}). {@link #best()} checks all
 * 24 matchings. Values are illustrative, chosen inside published sonication ranges, not species-calibrated.
 * Buzz pitches sit naturally in the low band and pass {@link EarRule#check}.
 */
public final class BuzzGarden {
    /** Bees and flowers per garden. */
    public static final int PAIRS = 4;
    /** Mismatch scale, Hz (pollen halves-ish beyond about 30 Hz off). */
    public static final double WIDTH_HZ = 25.0;
    private static final List<String> FLOWER_NAMES = List.of("blueberry", "tomato", "potato", "eggplant", "shooting star");
    private static final double[] FLOWER_HZ = {360, 320, 290, 250, 220};
    private static final List<String> BEE_NAMES = List.of("bumblebee queen", "bumblebee worker", "carpenter bee",
        "sweat bee", "mining bee");
    private static final long SALT = 0x425A_4731L; // "BZG1"

    /** A flower and its best buzz frequency. */
    public record Flower(String name, double bestHz) { }

    /** A bee and its buzz frequency. */
    public record Bee(String name, double buzzHz) {
        /** Buzz pitch (ear-rule checked). */
        public double hz() {
            return EarRule.check(buzzHz, name + " buzz");
        }
    }

    /** A judged matching. */
    public record Verdict(boolean best, int pollen, int bestPollen) { }

    private final long seed;
    private final List<Flower> flowers;
    private final List<Bee> bees;

    private BuzzGarden(long seed, List<Flower> flowers, List<Bee> bees) {
        this.seed = seed;
        this.flowers = List.copyOf(flowers);
        this.bees = List.copyOf(bees);
    }

    /** A seeded garden. */
    public static BuzzGarden seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        List<Integer> fi = pick(rng, FLOWER_NAMES.size());
        List<Integer> bi = pick(rng, BEE_NAMES.size());
        List<Flower> flowers = new ArrayList<>();
        List<Bee> bees = new ArrayList<>();
        for (int k = 0; k < PAIRS; k++) {
            int f = fi.get(k);
            double best = FLOWER_HZ[f] + jitter(rng, 10);
            flowers.add(new Flower(FLOWER_NAMES.get(f), round1(best)));
        }
        List<Integer> order = pick(rng, PAIRS);
        for (int k = 0; k < PAIRS; k++) {
            double buzz = flowers.get(order.get(k)).bestHz() + jitter(rng, 15);
            bees.add(new Bee(BEE_NAMES.get(bi.get(k)), round1(buzz)));
        }
        return new BuzzGarden(seed, flowers, bees);
    }

    private static List<Integer> pick(Rng rng, int n) {
        List<Integer> pool = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            pool.add(i);
        }
        List<Integer> out = new ArrayList<>();
        for (int k = 0; k < PAIRS; k++) {
            out.add(pool.remove((int) Long.remainderUnsigned(rng.nextLong(), pool.size())));
        }
        return out;
    }

    private static double jitter(Rng rng, double amp) {
        return amp * (Long.remainderUnsigned(rng.nextLong(), 2001) / 1000.0 - 1.0);
    }

    private static double round1(double v) {
        return Math.round(v * 10) / 10.0;
    }

    /** Pollen (0-100) a bee buzzing at {@code buzzHz} releases from a flower that wants {@code bestHz}. */
    public static int pollen(double buzzHz, double bestHz) {
        double d = (buzzHz - bestHz) / WIDTH_HZ;
        return (int) Math.round(100 * Math.exp(-d * d / 2));
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** The flowers. */
    public List<Flower> flowers() {
        return flowers;
    }

    /** The bees. */
    public List<Bee> bees() {
        return bees;
    }

    /** Total pollen for a matching (flower index per bee), or -1 if it is not one-to-one. */
    public int total(List<Integer> flowerOfBee) {
        if (flowerOfBee == null || flowerOfBee.size() != PAIRS || flowerOfBee.stream().distinct().count() != PAIRS
                || flowerOfBee.stream().anyMatch(f -> f < 0 || f >= PAIRS)) {
            return -1;
        }
        int sum = 0;
        for (int b = 0; b < PAIRS; b++) {
            sum += pollen(bees.get(b).hz(), flowers.get(flowerOfBee.get(b)).bestHz());
        }
        return sum;
    }

    /** The best matching (flower index per bee) over all 24; ties keep the first in generation order (deterministic). */
    public List<Integer> best() {
        List<Integer> bestM = null;
        int bestScore = -1;
        for (List<Integer> m : perms(PAIRS)) {
            int s = total(m);
            if (s > bestScore) {
                bestScore = s;
                bestM = m;
            }
        }
        return bestM;
    }

    private static List<List<Integer>> perms(int n) {
        List<List<Integer>> out = new ArrayList<>();
        if (n == 0) {
            out.add(new ArrayList<>());
            return out;
        }
        for (List<Integer> p : perms(n - 1)) {
            for (int k = 0; k <= p.size(); k++) {
                List<Integer> q = new ArrayList<>(p);
                q.add(k, n - 1);
                out.add(q);
            }
        }
        return out;
    }

    /** Judge a matching. */
    public Verdict judge(List<Integer> flowerOfBee) {
        int b = total(best());
        int s = total(flowerOfBee);
        return new Verdict(s == b, s, b);
    }
}