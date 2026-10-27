// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Rivet Change (contest gap G191): a hull seam scarred in the void ({@link VoidCrossing}) needs a patch of exact
 * length, and the forge casts rivet plates in a kit of sizes that always includes 1. Use the fewest plates.
 *
 * <p>The solver is plain: a kit is an {@code int[]} of distinct positive sizes. {@link #fewest} is the exact
 * change-making DP, {@link #ways} counts every distinct multiset of plates, {@link #greedy} takes the largest plate
 * that fits, and {@link #canonical} says whether greedy is always optimal for the kit by checking every length below
 * the two largest sizes summed (Kozen and Zaks). Any project can use it for currency, ammo stacks or tile runs.
 */
public final class RivetChange {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_rivet_change";

    /** How a patch compares with the fewest plates. */
    public enum Grade { FLUSH, LUMPY, NO_FIT }

    private RivetChange() {
    }

    /** A seeded kit: 1 plus {@code extra} distinct sizes in [2, maxSize], ascending. Same seed, same kit. */
    public static int[] kit(long seed, int extra, int maxSize) {
        if (extra < 0 || extra > maxSize - 1) {
            throw new IllegalArgumentException("cannot draw " + extra + " sizes up to " + maxSize);
        }
        SplittableRandom r = new SplittableRandom(seed);
        boolean[] used = new boolean[maxSize + 1];
        used[1] = true;
        int n = 0;
        while (n < extra) {
            int s = 2 + r.nextInt(maxSize - 1);
            if (!used[s]) {
                used[s] = true;
                n++;
            }
        }
        int[] k = new int[extra + 1];
        int j = 0;
        for (int s = 1; s <= maxSize; s++) {
            if (used[s]) {
                k[j++] = s;
            }
        }
        return k;
    }

    /** Fewest plates summing to {@code length} (plates ascending), or an empty list if none does and length > 0. */
    public static List<Integer> fewest(int[] kit, int length) {
        check(kit, length);
        int inf = Integer.MAX_VALUE;
        int[] f = new int[length + 1];
        int[] last = new int[length + 1];
        Arrays.fill(f, inf);
        f[0] = 0;
        for (int v = 1; v <= length; v++) {
            for (int s : kit) {
                if (s <= v && f[v - s] != inf && f[v - s] + 1 < f[v]) {
                    f[v] = f[v - s] + 1;
                    last[v] = s;
                }
            }
        }
        if (f[length] == inf) {
            return List.of();
        }
        List<Integer> plates = new ArrayList<>();
        for (int v = length; v > 0; v -= last[v]) {
            plates.add(last[v]);
        }
        plates.sort(null);
        return plates;
    }

    /** Largest plate that fits, repeatedly; empty list if it gets stuck (only possible without a size-1 plate). */
    public static List<Integer> greedy(int[] kit, int length) {
        check(kit, length);
        int[] k = kit.clone();
        Arrays.sort(k);
        List<Integer> plates = new ArrayList<>();
        int left = length;
        for (int i = k.length - 1; i >= 0 && left > 0; i--) {
            while (k[i] <= left) {
                plates.add(k[i]);
                left -= k[i];
            }
        }
        if (left > 0) {
            return List.of();
        }
        plates.sort(null);
        return plates;
    }

    /** Number of distinct multisets of plates summing to {@code length}. */
    public static long ways(int[] kit, int length) {
        check(kit, length);
        long[] w = new long[length + 1];
        w[0] = 1;
        for (int s : kit) {
            for (int v = s; v <= length; v++) {
                w[v] += w[v - s];
            }
        }
        return w[length];
    }

    /** True if greedy is optimal for every length; the smallest counterexample lies below the two largest summed. */
    public static boolean canonical(int[] kit) {
        return counterexample(kit) < 0;
    }

    /** Smallest length where greedy uses more plates than the fewest, or -1 if the kit is canonical. */
    public static int counterexample(int[] kit) {
        check(kit, 0);
        int[] k = kit.clone();
        Arrays.sort(k);
        if (k.length < 3) {
            return k[0] == 1 ? -1 : smallestGap(k, 2 * k[k.length - 1]);
        }
        return smallestGap(k, k[k.length - 1] + k[k.length - 2]);
    }

    private static int smallestGap(int[] k, int below) {
        for (int v = 1; v < below; v++) {
            List<Integer> g = greedy(k, v);
            List<Integer> f = fewest(k, v);
            if (!f.isEmpty() && (g.isEmpty() || g.size() > f.size())) {
                return v;
            }
        }
        return -1;
    }

    /** FLUSH at the fewest, LUMPY above it, NO_FIT if the plates do not make the length. */
    public static Grade grade(int[] kit, int length, List<Integer> plates) {
        check(kit, length);
        int sum = 0;
        for (int p : plates) {
            boolean in = false;
            for (int s : kit) {
                in |= s == p;
            }
            if (!in) {
                return Grade.NO_FIT;
            }
            sum += p;
        }
        if (sum != length) {
            return Grade.NO_FIT;
        }
        return plates.size() == fewest(kit, length).size() ? Grade.FLUSH : Grade.LUMPY;
    }

    /** The Forgemaster's line for a patch. */
    public static String forgemasterLine(Grade g, int plates) {
        return switch (g) {
            case FLUSH -> "Forgemaster: " + plates + " plates, flush as glass. She will hold.";
            case LUMPY -> "Forgemaster: " + plates + " plates. It holds, but it rattles. Fewer would do.";
            case NO_FIT -> "Forgemaster: that patch does not close the seam. Measure again.";
        };
    }

    private static void check(int[] kit, int length) {
        if (kit.length == 0 || length < 0) {
            throw new IllegalArgumentException("need a non-empty kit and a non-negative length");
        }
        for (int s : kit) {
            if (s <= 0) {
                throw new IllegalArgumentException("plate size must be positive: " + s);
            }
        }
    }
}
