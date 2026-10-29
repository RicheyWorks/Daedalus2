// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Spark Census (contest gap G276): sparks fly off the anvil in a stream of unknown length. The census keeper may hold
 * only {@code k} sparks at a time, yet must end with a fair sample of all of them.
 *
 * <p>The tool is plain: an Algorithm R reservoir ({@link #offer} one item at a time, O(k) memory, seeded) and
 * {@link #weighted}, an Efraimidis-Spirakis weighted reservoir in one pass. Any project can use it for fair sampling
 * from streams.
 */
public final class SparkCensus {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_spark_census";

    /** How a claim about the odds went. */
    public enum Grade { FAIR, BIASED }

    private final int[] held;
    private final SplittableRandom rng;
    private long seen;

    /** A census keeper holding at most {@code k} sparks, drawing from {@code seed}. */
    public SparkCensus(int k, long seed) {
        if (k < 1) {
            throw new IllegalArgumentException("need k >= 1");
        }
        held = new int[k];
        rng = new SplittableRandom(seed);
    }

    /** Offers the next spark from the stream. */
    public void offer(int spark) {
        if (seen < held.length) {
            held[(int) seen] = spark;
        } else {
            long j = rng.nextLong(seen + 1);
            if (j < held.length) {
                held[(int) j] = spark;
            }
        }
        seen++;
    }

    /** Sparks seen so far. */
    public long seen() {
        return seen;
    }

    /** The current sample (all sparks if fewer than k have been seen). */
    public int[] sample() {
        return Arrays.copyOf(held, (int) Math.min(seen, held.length));
    }

    /** One-pass uniform sample of {@code k} sparks from {@code stream}. Same seed, same sample. */
    public static int[] sample(int[] stream, int k, long seed) {
        SparkCensus c = new SparkCensus(k, seed);
        for (int s : stream) {
            c.offer(s);
        }
        return c.sample();
    }

    /**
     * One-pass weighted sample of up to {@code k} indices: index i is kept with key u^(1/w[i]), the k largest keys win.
     * Zero-weight items are never chosen.
     */
    public static int[] weighted(double[] w, int k, long seed) {
        if (k < 1) {
            throw new IllegalArgumentException("need k >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] idx = new int[k];
        double[] key = new double[k];
        int size = 0;
        for (int i = 0; i < w.length; i++) {
            if (!(w[i] >= 0) || Double.isInfinite(w[i])) {
                throw new IllegalArgumentException("weights must be finite and >= 0");
            }
            if (w[i] <= 0) {
                continue;
            }
            double kv = Math.pow(r.nextDouble(), 1.0 / w[i]);
            if (size < k) {
                idx[size] = i;
                key[size++] = kv;
            } else {
                int min = 0;
                for (int j = 1; j < k; j++) {
                    if (key[j] < key[min]) {
                        min = j;
                    }
                }
                if (kv > key[min]) {
                    idx[min] = i;
                    key[min] = kv;
                }
            }
        }
        int[] out = Arrays.copyOf(idx, size);
        Arrays.sort(out);
        return out;
    }

    /** Chance each of n sparks ends up in a k-sample: min(1, k/n). */
    public static double inclusionChance(long n, int k) {
        if (n < 1 || k < 1) {
            throw new IllegalArgumentException("need n >= 1 and k >= 1");
        }
        return Math.min(1.0, (double) k / n);
    }

    /** FAIR only if the claimed inclusion chance matches k/n within 1e-9. */
    public static Grade grade(long n, int k, double claimed) {
        return Math.abs(inclusionChance(n, k) - claimed) <= 1e-9 ? Grade.FAIR : Grade.BIASED;
    }

    /** The Forgemaster's line for a claim. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case FAIR -> "Forgemaster: every spark had its fair chance, first to last. A true census.";
            case BIASED -> "Forgemaster: your count favours some sparks over others. Keep the tally fair.";
        };
    }
}
