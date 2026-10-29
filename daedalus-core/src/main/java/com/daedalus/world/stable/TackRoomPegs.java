// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;

/**
 * G530 Tack Room Pegs (Studio horse lane): every horse's tack (saddle and bridle) hangs on a peg
 * in the tack room. A peg holds at most {@code limit} weight, and the tack of two feuding horses
 * must never share a peg (the smell sets them off). {@link #best} hangs everything on the fewest
 * pegs, exactly, with a dynamic program over subsets of tack (a subset can share one peg when it
 * is light enough and feud-free); {@link #firstFit} (hang each piece on the first peg that takes
 * it) is the habit that ends with one peg too many. Plain int[] API, at most 14 pieces; feuds are
 * an adjacency bitmask per piece.
 */
public final class TackRoomPegs {

    public static final String QUEST_ID = "q_tidy_tack_room";
    public static final int MAX_TACK = 14;

    /** A tack room: number of pegs used and the peg of each piece (pegs numbered from 0). */
    public record Room(int pegs, int[] pegOf) {
        public Room {
            pegOf = pegOf.clone();
        }

        @Override
        public int[] pegOf() {
            return pegOf.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Room r && r.pegs == pegs && Arrays.equals(r.pegOf, pegOf);
        }

        @Override
        public int hashCode() {
            return 31 * pegs + Arrays.hashCode(pegOf);
        }

        @Override
        public String toString() {
            return "Room[" + pegs + ", " + Arrays.toString(pegOf) + "]";
        }
    }

    private TackRoomPegs() { }

    /** Seeded tack weights in [1, limit] for {@code n} pieces. */
    public static int[] weights(long seed, int n, int limit) {
        if (n < 0 || n > MAX_TACK || limit <= 0) {
            throw new IllegalArgumentException("bad tack");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int[] w = new int[n];
        for (int i = 0; i < n; i++) {
            w[i] = 1 + rnd.nextInt(limit);
        }
        return w;
    }

    /** Seeded symmetric feud masks: each pair feuds with probability percent/100. */
    public static int[] feuds(long seed, int n, int percent) {
        if (n < 0 || n > MAX_TACK || percent < 0 || percent > 100) {
            throw new IllegalArgumentException("bad feuds");
        }
        SplittableRandom rnd = new SplittableRandom(seed ^ 0x5DEECE66DL);
        int[] f = new int[n];
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                if (rnd.nextInt(100) < percent) {
                    f[i] |= 1 << j;
                    f[j] |= 1 << i;
                }
            }
        }
        return f;
    }

    /** Fewest pegs that hold all the tack within the limit with no feuding pair together. */
    public static Room best(int[] weight, int[] feud, int limit) {
        check(weight, feud, limit);
        int n = weight.length;
        int states = 1 << n;
        boolean[] ok = new boolean[states];
        int[] load = new int[states];
        ok[0] = true;
        for (int s = 1; s < states; s++) {
            int low = Integer.numberOfTrailingZeros(s);
            int rest = s & (s - 1);
            load[s] = load[rest] + weight[low];
            ok[s] = ok[rest] && load[s] <= limit && (feud[low] & rest) == 0;
        }
        int[] pegs = new int[states];
        int[] pick = new int[states];
        for (int s = 1; s < states; s++) {
            int low = s & -s;
            int rest = s ^ low;
            pegs[s] = Integer.MAX_VALUE;
            for (int t = rest;; t = (t - 1) & rest) {
                int group = t | low;
                if (ok[group] && pegs[s ^ group] + 1 < pegs[s]) {
                    pegs[s] = pegs[s ^ group] + 1;
                    pick[s] = group;
                }
                if (t == 0) {
                    break;
                }
            }
        }
        int[] pegOf = new int[n];
        int s = states - 1;
        int peg = 0;
        while (s != 0) {
            int group = pick[s];
            for (int i = 0; i < n; i++) {
                if ((group & (1 << i)) != 0) {
                    pegOf[i] = peg;
                }
            }
            peg++;
            s ^= group;
        }
        return new Room(pegs[states - 1], pegOf);
    }

    /** Naive first fit in tack order: the first existing peg with room and no feud, else a new peg. */
    public static Room firstFit(int[] weight, int[] feud, int limit) {
        check(weight, feud, limit);
        List<int[]> pegs = new ArrayList<>();
        int[] pegOf = new int[weight.length];
        for (int i = 0; i < weight.length; i++) {
            int chosen = -1;
            for (int p = 0; p < pegs.size() && chosen < 0; p++) {
                int[] peg = pegs.get(p);
                if (peg[0] + weight[i] <= limit && (feud[i] & peg[1]) == 0) {
                    chosen = p;
                }
            }
            if (chosen < 0) {
                pegs.add(new int[2]);
                chosen = pegs.size() - 1;
            }
            int[] peg = pegs.get(chosen);
            peg[0] += weight[i];
            peg[1] |= 1 << i;
            pegOf[i] = chosen;
        }
        return new Room(pegs.size(), pegOf);
    }

    /** Pegs used by a hanging, or -1 when a peg is overloaded, a feud shares a peg or a peg is negative. */
    public static int hang(int[] weight, int[] feud, int limit, int[] pegOf) {
        check(weight, feud, limit);
        if (pegOf.length != weight.length) {
            return -1;
        }
        int n = weight.length;
        int[] load = new int[n];
        int[] members = new int[n];
        int used = 0;
        for (int i = 0; i < n; i++) {
            int p = pegOf[i];
            if (p < 0 || p >= n) {
                return -1;
            }
            if ((feud[i] & members[p]) != 0) {
                return -1;
            }
            if (members[p] == 0) {
                used++;
            }
            load[p] += weight[i];
            members[p] |= 1 << i;
            if (load[p] > limit) {
                return -1;
            }
        }
        return used;
    }

    /** Quest q_tidy_tack_room: the stable hand's hanging is legal and uses the fewest pegs. */
    public static boolean quest(int[] weight, int[] feud, int limit, int[] pegOf) {
        int got = hang(weight, feud, limit, pegOf);
        return got >= 0 && got == best(weight, feud, limit).pegs();
    }

    private static void check(int[] weight, int[] feud, int limit) {
        if (weight.length != feud.length || weight.length > MAX_TACK || limit <= 0) {
            throw new IllegalArgumentException("bad tack room");
        }
        for (int i = 0; i < weight.length; i++) {
            if (weight[i] <= 0 || weight[i] > limit || (feud[i] & (1 << i)) != 0) {
                throw new IllegalArgumentException("bad piece " + i);
            }
            for (int j = 0; j < weight.length; j++) {
                if (((feud[i] >> j) & 1) != ((feud[j] >> i) & 1)) {
                    throw new IllegalArgumentException("feuds must be mutual");
                }
            }
        }
    }
}
