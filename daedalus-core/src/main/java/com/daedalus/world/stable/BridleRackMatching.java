// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * G537 Bridle Rack Matching (Studio horse lane): before the ride every horse needs its own groom.
 * A groom may tack a horse only when the groom's skill is at least the horse's temperament, and
 * each allowed pair has a seeded tacking time. All grooms start together, so the ride leaves when
 * the slowest pair is done. {@link #best} pairs every horse so the last one is ready earliest
 * (bottleneck assignment with compatibility): try each threshold in rising order and keep the first
 * one whose fast-enough allowed pairs contain a perfect matching (augmenting paths).
 * {@link #cheapestFirst} (take the quickest free pair each time) can leave a slow pair to last or
 * a nervous horse with no skilled groom free. Plain int[] API, at most 10 horses; the algorithm is
 * small and pure so it can be ported to C++ for Unreal.
 */
public final class BridleRackMatching {

    public static final String QUEST_ID = "q_all_tacked";
    public static final int MAX_HORSES = 10;
    public static final int INFEASIBLE = -1;

    /** A pairing: the time the last horse is ready and the groom of each horse (empty when infeasible). */
    public record Pairing(int ready, int[] groomOf) {
        public Pairing {
            groomOf = groomOf.clone();
        }

        @Override
        public int[] groomOf() {
            return groomOf.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Pairing p && p.ready == ready && Arrays.equals(p.groomOf, groomOf);
        }

        @Override
        public int hashCode() {
            return 31 * ready + Arrays.hashCode(groomOf);
        }

        @Override
        public String toString() {
            return "Pairing[" + ready + ", " + Arrays.toString(groomOf) + "]";
        }
    }

    private BridleRackMatching() { }

    /** Seeded horse temperaments in [1, 5]. */
    public static int[] temperaments(long seed, int n) {
        if (n < 0 || n > MAX_HORSES) {
            throw new IllegalArgumentException("bad horse count");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int[] t = new int[n];
        for (int i = 0; i < n; i++) {
            t[i] = 1 + rnd.nextInt(5);
        }
        return t;
    }

    /** Seeded groom skills: a shuffled copy of the temperaments, each raised by 0-1, so a pairing exists. */
    public static int[] skills(long seed, int[] temperament) {
        SplittableRandom rnd = new SplittableRandom(seed ^ 0x2545F4914F6CDD1DL);
        int n = temperament.length;
        int[] s = new int[n];
        for (int i = 0; i < n; i++) {
            s[i] = temperament[i] + rnd.nextInt(2);
        }
        for (int i = n - 1; i > 0; i--) {
            int j = rnd.nextInt(i + 1);
            int t = s[i];
            s[i] = s[j];
            s[j] = t;
        }
        return s;
    }

    /** Seeded tacking times time[groom][horse] in [1, 20]. */
    public static int[][] times(long seed, int n) {
        SplittableRandom rnd = new SplittableRandom(seed ^ 0x6A09E667F3BCC909L);
        int[][] t = new int[n][n];
        for (int g = 0; g < n; g++) {
            for (int h = 0; h < n; h++) {
                t[g][h] = 1 + rnd.nextInt(20);
            }
        }
        return t;
    }

    /** Earliest moment every horse is tacked by its own allowed groom. */
    public static Pairing best(int[] skill, int[] temperament, int[][] time) {
        check(skill, temperament, time);
        int n = skill.length;
        if (n == 0) {
            return new Pairing(0, new int[0]);
        }
        int[] cand = new int[n * n];
        int c = 0;
        for (int g = 0; g < n; g++) {
            for (int h = 0; h < n; h++) {
                if (skill[g] >= temperament[h]) {
                    cand[c++] = time[g][h];
                }
            }
        }
        int[] limits = Arrays.copyOf(cand, c);
        Arrays.sort(limits);
        for (int k = 0; k < limits.length; k++) {
            if (k > 0 && limits[k] == limits[k - 1]) {
                continue;
            }
            int[] horseOf = new int[n];
            Arrays.fill(horseOf, -1);
            int[] groomOf = new int[n];
            Arrays.fill(groomOf, -1);
            int matched = 0;
            for (int h = 0; h < n; h++) {
                if (augment(skill, temperament, time, limits[k], h, new boolean[n], horseOf, groomOf)) {
                    matched++;
                }
            }
            if (matched == n) {
                return new Pairing(limits[k], groomOf);
            }
        }
        return new Pairing(INFEASIBLE, new int[0]);
    }

    private static boolean augment(int[] skill, int[] temperament, int[][] time, int limit, int h,
            boolean[] seen, int[] horseOf, int[] groomOf) {
        for (int g = 0; g < skill.length; g++) {
            if (!seen[g] && skill[g] >= temperament[h] && time[g][h] <= limit) {
                seen[g] = true;
                if (horseOf[g] < 0 || augment(skill, temperament, time, limit, horseOf[g], seen, horseOf, groomOf)) {
                    horseOf[g] = h;
                    groomOf[h] = g;
                    return true;
                }
            }
        }
        return false;
    }

    /** Naive habit: repeatedly take the quickest allowed pair of a free groom and an untacked horse. */
    public static Pairing cheapestFirst(int[] skill, int[] temperament, int[][] time) {
        check(skill, temperament, time);
        int n = skill.length;
        boolean[] busy = new boolean[n];
        int[] groomOf = new int[n];
        Arrays.fill(groomOf, -1);
        int ready = 0;
        for (int step = 0; step < n; step++) {
            int bg = -1;
            int bh = -1;
            for (int h = 0; h < n; h++) {
                for (int g = 0; g < n; g++) {
                    if (groomOf[h] < 0 && !busy[g] && skill[g] >= temperament[h]
                            && (bg < 0 || time[g][h] < time[bg][bh])) {
                        bg = g;
                        bh = h;
                    }
                }
            }
            if (bg < 0) {
                return new Pairing(INFEASIBLE, new int[0]);
            }
            busy[bg] = true;
            groomOf[bh] = bg;
            ready = Math.max(ready, time[bg][bh]);
        }
        return new Pairing(ready, groomOf);
    }

    /** Ready time of a pairing, or INFEASIBLE when a groom is reused, out of range or not skilled enough. */
    public static int ready(int[] skill, int[] temperament, int[][] time, int[] groomOf) {
        check(skill, temperament, time);
        int n = skill.length;
        if (groomOf.length != n) {
            return INFEASIBLE;
        }
        boolean[] used = new boolean[n];
        int ready = 0;
        for (int h = 0; h < n; h++) {
            int g = groomOf[h];
            if (g < 0 || g >= n || used[g] || skill[g] < temperament[h]) {
                return INFEASIBLE;
            }
            used[g] = true;
            ready = Math.max(ready, time[g][h]);
        }
        return ready;
    }

    /** Quest q_all_tacked: every horse has an allowed groom and the ride leaves as early as possible. */
    public static boolean quest(int[] skill, int[] temperament, int[][] time, int[] groomOf) {
        int got = ready(skill, temperament, time, groomOf);
        return got != INFEASIBLE && got == best(skill, temperament, time).ready();
    }

    private static void check(int[] skill, int[] temperament, int[][] time) {
        int n = skill.length;
        if (n > MAX_HORSES || temperament.length != n || time.length != n) {
            throw new IllegalArgumentException("bad stable");
        }
        for (int[] row : time) {
            if (row.length != n) {
                throw new IllegalArgumentException("bad time table");
            }
            for (int t : row) {
                if (t < 0) {
                    throw new IllegalArgumentException("negative time");
                }
            }
        }
    }
}
