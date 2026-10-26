// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import java.util.ArrayDeque;
import java.util.SplittableRandom;

/**
 * Turing coat genetics (contest gap G21). A pet's coat is a Gray-Scott reaction-diffusion field grown from two genes,
 * {@code feed} and {@code kill}, on a small wrapping skin grid. The grown pattern is classified into the coat keys the
 * Kennel Isle {@link TonicBrewer} reads: {@code Spots}, {@code Stripes}, {@code Labyrinth} or {@code None}.
 * Breeding averages the parents' genes and adds a small seeded mutation, so a litter is deterministic per seed.
 * Pure, JDK-only.
 */
public final class TuringCoat {
    public static final double FEED_MIN = 0.010;
    public static final double FEED_MAX = 0.080;
    public static final double KILL_MIN = 0.040;
    public static final double KILL_MAX = 0.075;
    public static final double MUTATION = 0.0015;
    public static final int SIZE = 64;
    public static final int STEPS = 4000;

    /** Coat genes. */
    public record Genes(double feed, double kill) {
        public Genes {
            if (feed < FEED_MIN || feed > FEED_MAX || kill < KILL_MIN || kill > KILL_MAX
                || Double.isNaN(feed) || Double.isNaN(kill)) {
                throw new IllegalArgumentException("coat genes out of range");
            }
        }
    }

    /** Pattern stats behind the classification. */
    public record Coat(String pattern, double coverage, int patches, double largestShare, Genes genes) { }

    /** Starter lines from the Ark kennel book. */
    public static final Genes SPOTTED_LINE = new Genes(0.0367, 0.0649);
    public static final Genes STRIPED_LINE = new Genes(0.0340, 0.0618);
    public static final Genes LABYRINTH_LINE = new Genes(0.0420, 0.0590);
    public static final Genes PLAIN_LINE = new Genes(0.0300, 0.0700);

    private TuringCoat() {
    }

    /** Pup genes: parent mean plus a seeded mutation of up to {@link #MUTATION} per gene, clamped to range. */
    public static Genes breed(Genes mother, Genes father, long seed) {
        SplittableRandom r = new SplittableRandom(seed);
        double f = (mother.feed() + father.feed()) / 2 + (r.nextDouble() * 2 - 1) * MUTATION;
        double k = (mother.kill() + father.kill()) / 2 + (r.nextDouble() * 2 - 1) * MUTATION;
        return new Genes(clamp(f, FEED_MIN, FEED_MAX), clamp(k, KILL_MIN, KILL_MAX));
    }

    /** Grows the field (V concentration) for these genes; the seed places the starting freckles. */
    public static double[] grow(Genes g, long seed) {
        int n = SIZE;
        double[] u = new double[n * n];
        double[] v = new double[n * n];
        java.util.Arrays.fill(u, 1.0);
        SplittableRandom r = new SplittableRandom(seed);
        for (int s = 0; s < 12; s++) {
            int cx = r.nextInt(n);
            int cy = r.nextInt(n);
            for (int dy = -3; dy <= 3; dy++) {
                for (int dx = -3; dx <= 3; dx++) {
                    int i = idx(cx + dx, cy + dy);
                    u[i] = 0.5;
                    v[i] = 0.25 + r.nextDouble() * 0.02;
                }
            }
        }
        double du = 0.16;
        double dv = 0.08;
        double[] u2 = new double[n * n];
        double[] v2 = new double[n * n];
        for (int t = 0; t < STEPS; t++) {
            for (int y = 0; y < n; y++) {
                for (int x = 0; x < n; x++) {
                    int i = y * n + x;
                    double lu = u[idx(x - 1, y)] + u[idx(x + 1, y)] + u[idx(x, y - 1)] + u[idx(x, y + 1)] - 4 * u[i];
                    double lv = v[idx(x - 1, y)] + v[idx(x + 1, y)] + v[idx(x, y - 1)] + v[idx(x, y + 1)] - 4 * v[i];
                    double uvv = u[i] * v[i] * v[i];
                    u2[i] = u[i] + du * lu - uvv + g.feed() * (1 - u[i]);
                    v2[i] = v[i] + dv * lv + uvv - (g.feed() + g.kill()) * v[i];
                }
            }
            double[] tu = u;
            u = u2;
            u2 = tu;
            double[] tv = v;
            v = v2;
            v2 = tv;
        }
        return v;
    }

    /** Grows and classifies a coat. */
    public static Coat coat(Genes g, long seed) {
        return classify(grow(g, seed), g);
    }

    /**
     * Classifies a grown field: pigment where V > 0.2. Under 3% pigment is {@code None}; many small patches
     * (largest under 6% of pigment) is {@code Spots}; one patch holding most pigment is {@code Labyrinth}; else
     * {@code Stripes}.
     */
    public static Coat classify(double[] v, Genes g) {
        int n = SIZE;
        boolean[] on = new boolean[n * n];
        int count = 0;
        for (int i = 0; i < on.length; i++) {
            on[i] = v[i] > 0.2;
            if (on[i]) {
                count++;
            }
        }
        double coverage = count / (double) on.length;
        int[] lab = new int[n * n];
        int patches = 0;
        int largest = 0;
        ArrayDeque<Integer> q = new ArrayDeque<>();
        for (int i = 0; i < on.length; i++) {
            if (!on[i] || lab[i] != 0) {
                continue;
            }
            patches++;
            int size = 0;
            lab[i] = patches;
            q.add(i);
            while (!q.isEmpty()) {
                int c = q.poll();
                size++;
                int x = c % n;
                int y = c / n;
                int[] nb = {idx(x - 1, y), idx(x + 1, y), idx(x, y - 1), idx(x, y + 1)};
                for (int j : nb) {
                    if (on[j] && lab[j] == 0) {
                        lab[j] = patches;
                        q.add(j);
                    }
                }
            }
            largest = Math.max(largest, size);
        }
        double share = count == 0 ? 0 : largest / (double) count;
        String p;
        if (coverage < 0.03) {
            p = "None";
        } else if (share < 0.06) {
            p = "Spots";
        } else if (share > 0.6) {
            p = "Labyrinth";
        } else {
            p = "Stripes";
        }
        return new Coat(p, coverage, patches, share, g);
    }

    private static int idx(int x, int y) {
        int n = SIZE;
        return Math.floorMod(y, n) * n + Math.floorMod(x, n);
    }

    private static double clamp(double x, double lo, double hi) {
        return Math.max(lo, Math.min(hi, x));
    }
}
