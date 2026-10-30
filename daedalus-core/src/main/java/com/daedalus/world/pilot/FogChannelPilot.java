// SPDX-License-Identifier: MIT

package com.daedalus.world.pilot;

import java.util.Arrays;

/**
 * G586 Fog Channel Pilot (Shattered Planet harbour): a ship drifts between {@code channels} buoyed lanes in thick
 * fog, and the harbour pilot only hears one echo per foghorn blast (a dull, a ring or a clang). Every lane change
 * has a drift cost, every lane has an opening cost, and every echo is more or less surprising from each lane; all
 * costs are small integers (penalty points, a log-odds stand-in), so the game stays exact in Java and C++.
 * {@link #best} names the most likely lane for every blast at once (Viterbi, min-sum over integer costs);
 * {@link #loudestEcho} is the dockhand's habit of trusting each echo on its own, which ignores how ships actually
 * drift and can name a zig-zag no ship could sail. Scenarios come from {@link PyStringRandom}, so the seed string
 * builds the same harbour in Python, Java and Unreal (DaedalusPilotFogChannelCore.h).
 */
public final class FogChannelPilot {

    public static final String QUEST_ID = "q_pilot_through_fog";
    public static final int ECHOES = 3;
    public static final int MAX_CHANNELS = 4;
    public static final int MAX_BLASTS = 8;
    public static final int INVALID = -1;

    /** A foggy harbour: opening, drift and echo costs plus the echoes heard, one per blast. */
    public record Harbour(int[] open, int[][] drift, int[][] echo, int[] heard) {
        public Harbour {
            open = open.clone();
            drift = deep(drift);
            echo = deep(echo);
            heard = heard.clone();
            int s = open.length;
            if (s < 1 || s > MAX_CHANNELS || drift.length != s || echo.length != s || heard.length > MAX_BLASTS) {
                throw new IllegalArgumentException("bad harbour");
            }
            for (int i = 0; i < s; i++) {
                if (drift[i].length != s || echo[i].length != ECHOES || open[i] < 0) {
                    throw new IllegalArgumentException("bad channel " + i);
                }
                for (int j = 0; j < s; j++) {
                    if (drift[i][j] < 0) {
                        throw new IllegalArgumentException("negative drift");
                    }
                }
                for (int e : echo[i]) {
                    if (e < 0) {
                        throw new IllegalArgumentException("negative echo cost");
                    }
                }
            }
            for (int h : heard) {
                if (h < 0 || h >= ECHOES) {
                    throw new IllegalArgumentException("unknown echo " + h);
                }
            }
        }

        @Override
        public int[] open() {
            return open.clone();
        }

        @Override
        public int[][] drift() {
            return deep(drift);
        }

        @Override
        public int[][] echo() {
            return deep(echo);
        }

        @Override
        public int[] heard() {
            return heard.clone();
        }

        public int channels() {
            return open.length;
        }

        public int blasts() {
            return heard.length;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Harbour h && Arrays.equals(h.open, open) && Arrays.deepEquals(h.drift, drift)
                    && Arrays.deepEquals(h.echo, echo) && Arrays.equals(h.heard, heard);
        }

        @Override
        public int hashCode() {
            return Arrays.hashCode(new int[] {Arrays.hashCode(open), Arrays.deepHashCode(drift), Arrays.deepHashCode(echo),
                Arrays.hashCode(heard)});
        }

        @Override
        public String toString() {
            return "Harbour[open=" + Arrays.toString(open) + ", drift=" + Arrays.deepToString(drift) + ", echo="
                    + Arrays.deepToString(echo) + ", heard=" + Arrays.toString(heard) + "]";
        }

        private static int[][] deep(int[][] a) {
            int[][] c = new int[a.length][];
            for (int i = 0; i < a.length; i++) {
                c[i] = a[i].clone();
            }
            return c;
        }
    }

    /** A reading of the fog: total cost and the lane named for every blast. */
    public record Track(int cost, int[] lanes) {
        public Track {
            lanes = lanes.clone();
        }

        @Override
        public int[] lanes() {
            return lanes.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Track t && t.cost == cost && Arrays.equals(t.lanes, lanes);
        }

        @Override
        public int hashCode() {
            return 31 * cost + Arrays.hashCode(lanes);
        }

        @Override
        public String toString() {
            return "Track[" + cost + ", " + Arrays.toString(lanes) + "]";
        }
    }

    private FogChannelPilot() { }

    /**
     * Seeded harbour, drawn in a fixed order from {@code random.Random(seed)}: channels in [2, 4], blasts in [1, 8],
     * opening costs, drift costs row by row (staying put is cheap, changing lanes dear), echo costs row by row, then
     * the echoes heard.
     */
    public static Harbour harbour(String seed) {
        PyStringRandom rnd = new PyStringRandom(seed);
        int s = 2 + rnd.below(3);
        int t = 1 + rnd.below(MAX_BLASTS);
        int[] open = new int[s];
        for (int i = 0; i < s; i++) {
            open[i] = rnd.below(6);
        }
        int[][] drift = new int[s][s];
        for (int i = 0; i < s; i++) {
            for (int j = 0; j < s; j++) {
                drift[i][j] = i == j ? rnd.below(3) : 2 + rnd.below(8);
            }
        }
        int[][] echo = new int[s][ECHOES];
        for (int i = 0; i < s; i++) {
            for (int o = 0; o < ECHOES; o++) {
                echo[i][o] = rnd.below(7);
            }
        }
        int[] heard = new int[t];
        for (int k = 0; k < t; k++) {
            heard[k] = rnd.below(ECHOES);
        }
        return new Harbour(open, drift, echo, heard);
    }

    /** Cheapest lane sequence for all blasts at once (Viterbi); ties go to the lower lane, earlier and later. */
    public static Track best(Harbour h) {
        int s = h.channels();
        int t = h.blasts();
        if (t == 0) {
            return new Track(0, new int[0]);
        }
        int[][] cost = new int[t][s];
        int[][] from = new int[t][s];
        for (int i = 0; i < s; i++) {
            cost[0][i] = h.open[i] + h.echo[i][h.heard[0]];
        }
        for (int k = 1; k < t; k++) {
            for (int j = 0; j < s; j++) {
                int bestPrev = 0;
                for (int i = 1; i < s; i++) {
                    if (cost[k - 1][i] + h.drift[i][j] < cost[k - 1][bestPrev] + h.drift[bestPrev][j]) {
                        bestPrev = i;
                    }
                }
                cost[k][j] = cost[k - 1][bestPrev] + h.drift[bestPrev][j] + h.echo[j][h.heard[k]];
                from[k][j] = bestPrev;
            }
        }
        int last = 0;
        for (int i = 1; i < s; i++) {
            if (cost[t - 1][i] < cost[t - 1][last]) {
                last = i;
            }
        }
        int[] lanes = new int[t];
        lanes[t - 1] = last;
        for (int k = t - 1; k > 0; k--) {
            lanes[k - 1] = from[k][lanes[k]];
        }
        return new Track(cost[t - 1][last], lanes);
    }

    /** The dockhand's habit: each blast on its own, the lane its echo surprises least (lower lane on ties). */
    public static Track loudestEcho(Harbour h) {
        int[] lanes = new int[h.blasts()];
        for (int k = 0; k < lanes.length; k++) {
            int pick = 0;
            for (int i = 1; i < h.channels(); i++) {
                if (h.echo[i][h.heard[k]] < h.echo[pick][h.heard[k]]) {
                    pick = i;
                }
            }
            lanes[k] = pick;
        }
        return new Track(cost(h, lanes), lanes);
    }

    /** Total cost of a lane sequence, or INVALID when it is the wrong length or names a missing lane. */
    public static int cost(Harbour h, int[] lanes) {
        if (lanes.length != h.blasts()) {
            return INVALID;
        }
        int total = 0;
        for (int k = 0; k < lanes.length; k++) {
            int l = lanes[k];
            if (l < 0 || l >= h.channels()) {
                return INVALID;
            }
            total += (k == 0 ? h.open[l] : h.drift[lanes[k - 1]][l]) + h.echo[l][h.heard[k]];
        }
        return total;
    }

    /** Quest q_pilot_through_fog: the pilot's reading is a real track and no track explains the fog better. */
    public static boolean quest(Harbour h, int[] lanes) {
        int got = cost(h, lanes);
        return got != INVALID && got == best(h).cost();
    }
}
