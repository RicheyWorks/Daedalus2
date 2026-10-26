// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;

/**
 * Founder Drift (contest G163, "Studbook"): genetic drift in the sky-crane aviary before the G142 releases.
 *
 * <p>The aviary is founded with {@code founders} cranes (half cocks, half hens), each carrying two alleles at each of
 * {@code loci} neutral loci, all unique. Every generation, keeper Ilsa Marr chooses how many cocks and hens make up the
 * next generation ({@link #breed(int, int, int)}, capped by the aviary). Each chick picks a random father and mother from
 * the generation before and inherits one random allele from each at every locus (Wright-Fisher with separate sexes).
 * Then {@code migrants} chicks a generation are swapped for cranes from other arks, with fresh alleles.
 *
 * <p>Gene diversity H (the chance two random allele copies at a locus differ, averaged over loci) falls by about
 * {@code 1/(2Ne)} a generation, with {@code Ne = 4MF/(M+F)} ({@link #effectiveSize(int, int)}); over generations Ne is
 * the harmonic mean, so one bottleneck dominates. {@link Report#retained()} = H now / H of the founders, and the
 * inbreeding {@code F = 1 − retained} sets the flock's survival on the marsh ({@link Report#survival(double)}), which
 * feeds {@link AlleeRelease}. Every draw is a splitmix hash of (seed, generation, chick, locus, salt).
 */
public final class FounderDrift {

    /** How much of the founders' diversity is left. */
    public enum Outcome { DIVERSE, THINNING, INBRED }

    /** Retained diversity for DIVERSE. */
    public static final double DIVERSE = 0.85;

    /** Retained diversity for THINNING. */
    public static final double THINNING = 0.7;

    /**
     * Aviary tuning.
     *
     * @param founders    founding cranes (cocks are the first half, rounded down)
     * @param capacity    most cranes a generation the aviary holds
     * @param generations generations to breed
     * @param loci        neutral loci tracked
     * @param migrantPool cranes the other arks can lend in total
     * @param lethal      lethal equivalents: survival is scaled by exp(−lethal·F)
     */
    public record Settings(int founders, int capacity, int generations, int loci, int migrantPool, double lethal) {

        /** The default aviary: 20 founders, 20 places, 20 generations, 40 loci, 40 migrants, 0.2 lethal equivalents. */
        public static final Settings DEFAULT = new Settings(20, 20, 20, 40, 40, 0.2);

        /** Rejects tuning that cannot run. */
        public Settings {
            if (founders < 2 || capacity < 2 || generations < 1 || loci < 1 || migrantPool < 0 || !(lethal >= 0)
                    || Double.isInfinite(lethal)) {
                throw new IllegalArgumentException("bad founder-drift settings");
            }
        }
    }

    /** One generation: cocks, hens, migrants in, diversity after, and distinct alleles left. */
    public record Generation(int index, int males, int females, int migrants, double diversity, int alleles) {}

    /** The result. */
    public record Report(Outcome outcome, double founderDiversity, double retained, double expected,
            List<Generation> generations, double lethal) {

        /** Defensive copy. */
        public Report {
            generations = List.copyOf(generations);
        }

        /** Inbreeding F = 1 − retained (never below 0). */
        public double inbreeding() {
            return Math.max(0, 1 - retained);
        }

        /** Marsh survival for these birds: {@code base · exp(−lethal · F)}. */
        public double survival(double base) {
            return base * Math.exp(-lethal * inbreeding());
        }

        /** AlleeRelease tuning with this flock's survival in place of the default. */
        public AlleeRelease.Settings marsh(AlleeRelease.Settings s) {
            return new AlleeRelease.Settings(s.budget(), s.years(), survival(s.survival()), s.mateHalf(), s.fledge(),
                    s.capacity(), s.goal());
        }
    }

    private final Settings s;
    private final long seed;
    private final int[] males;
    private final int[] females;
    private int migrants;

    private FounderDrift(Settings s, long seed) {
        this.s = s;
        this.seed = seed;
        this.males = new int[s.generations()];
        this.females = new int[s.generations()];
        int m = Math.min(s.capacity(), s.founders()) / 2;
        java.util.Arrays.fill(males, m);
        java.util.Arrays.fill(females, Math.min(s.capacity(), s.founders()) - m);
    }

    /** A seeded aviary; every generation defaults to the founders' sex ratio, capped by the aviary. */
    public static FounderDrift aviary(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new FounderDrift(settings, seed);
    }

    /** Sets the cocks and hens raised in generation {@code gen} (1-based). False if out of range or over capacity. */
    public boolean breed(int gen, int cocks, int hens) {
        if (gen < 1 || gen > s.generations() || cocks < 1 || hens < 1 || cocks + hens > s.capacity()) {
            return false;
        }
        males[gen - 1] = cocks;
        females[gen - 1] = hens;
        return true;
    }

    /** Migrants swapped in each generation. False if the other arks cannot lend that many over the run. */
    public boolean migrants(int perGeneration) {
        if (perGeneration < 0 || (long) perGeneration * s.generations() > s.migrantPool()) {
            return false;
        }
        migrants = perGeneration;
        return true;
    }

    /** Effective size of one generation of {@code m} cocks and {@code f} hens: 4mf/(m+f). */
    public static double effectiveSize(int m, int f) {
        if (m < 0 || f < 0) {
            throw new IllegalArgumentException("negative breeders");
        }
        return m + f == 0 ? 0 : 4.0 * m * f / (m + f);
    }

    /** Harmonic mean of effective sizes; 0 if any is 0 or the list is empty. */
    public static double harmonicMean(List<Double> sizes) {
        if (sizes == null || sizes.isEmpty()) {
            return 0;
        }
        double inv = 0;
        for (double n : sizes) {
            if (!(n > 0)) {
                return 0;
            }
            inv += 1 / n;
        }
        return sizes.size() / inv;
    }

    /** Expected retained diversity with no migrants: the product of (1 − 1/(2Ne)) over the planned generations. */
    public double expectedRetained() {
        int pm = s.founders() / 2;
        int pf = s.founders() - pm;
        double r = 1;
        for (int g = 0; g < s.generations(); g++) {
            r *= 1 - 1 / (2 * effectiveSize(pm, pf));
            pm = males[g];
            pf = females[g];
        }
        return r;
    }

    /** Runs the studbook. Deterministic in the settings, the seed and the plan. */
    public Report run() {
        int n = s.founders();
        int pm = n / 2;
        int[][] genes = new int[n][2 * s.loci()];
        int next = 0;
        for (int i = 0; i < n; i++) {
            for (int k = 0; k < 2 * s.loci(); k++) {
                genes[i][k] = next++;
            }
        }
        double h0 = diversity(genes);
        List<Generation> log = new ArrayList<>();
        for (int g = 0; g < s.generations(); g++) {
            int pf = genes.length - pm;
            int size = males[g] + females[g];
            int[][] kids = new int[size][2 * s.loci()];
            for (int c = 0; c < size; c++) {
                int dad = (int) (roll(g, c, 0, 1) * pm);
                int mum = pm + (int) (roll(g, c, 0, 2) * pf);
                for (int l = 0; l < s.loci(); l++) {
                    kids[c][2 * l] = genes[dad][2 * l + (roll(g, c, l, 3) < 0.5 ? 0 : 1)];
                    kids[c][2 * l + 1] = genes[mum][2 * l + (roll(g, c, l, 4) < 0.5 ? 0 : 1)];
                }
            }
            int in = Math.min(migrants, size);
            for (int j = 0; j < in; j++) {
                int c = (int) (roll(g, j, 0, 5) * size);
                for (int k = 0; k < 2 * s.loci(); k++) {
                    kids[c][k] = next++;
                }
            }
            genes = kids;
            pm = males[g];
            log.add(new Generation(g + 1, males[g], females[g], in, diversity(genes), distinct(genes)));
        }
        double retained = h0 <= 0 ? 0 : diversity(genes) / h0;
        Outcome o = retained >= DIVERSE ? Outcome.DIVERSE : retained >= THINNING ? Outcome.THINNING : Outcome.INBRED;
        return new Report(o, h0, retained, expectedRetained(), log, s.lethal());
    }

    /** Mean over loci of 1 − Σ p², the chance two random copies differ. */
    private double diversity(int[][] genes) {
        double total = 0;
        int copies = 2 * genes.length;
        for (int l = 0; l < s.loci(); l++) {
            java.util.Map<Integer, Integer> count = new java.util.HashMap<>();
            for (int[] bird : genes) {
                count.merge(bird[2 * l], 1, Integer::sum);
                count.merge(bird[2 * l + 1], 1, Integer::sum);
            }
            double sq = 0;
            for (int c : count.values()) {
                double p = (double) c / copies;
                sq += p * p;
            }
            total += 1 - sq;
        }
        return total / s.loci();
    }

    private static int distinct(int[][] genes) {
        java.util.Set<Integer> seen = new java.util.HashSet<>();
        for (int[] bird : genes) {
            for (int a : bird) {
                seen.add(a);
            }
        }
        return seen.size();
    }

    private double roll(int gen, long chick, int locus, int salt) {
        long z = seed + 0x9E3779B97F4A7C15L * (gen + 1) + 0xBF58476D1CE4E5B9L * (chick + 1)
                + 0x94D049BB133111EBL * (salt + 8L * (locus + 1));
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z = z ^ (z >>> 31);
        return (z >>> 11) * 0x1.0p-53;
    }
}
