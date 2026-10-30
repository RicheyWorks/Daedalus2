// SPDX-License-Identifier: MIT

package com.daedalus.world.pilot;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

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
    /** Longest fog a harbour may hold (the pea-soup tier reaches it). */
    public static final int MAX_BLASTS = 16;
    /** Blast cap of the classic {@link #harbour(String)} draw, kept at 8 so the G586 parity seeds never move. */
    public static final int CLASSIC_BLASTS = 8;
    /** A blast whose echo never came back: it costs nothing in any lane, so it tells the pilot nothing. */
    public static final int MISSED = ECHOES;
    public static final int INVALID = -1;
    /** A reading within this many points of par still earns two stars. */
    public static final int PAR_SLACK = 2;
    /** Display names of the echo kinds, by index. */
    public static final List<String> ECHO_NAMES = List.of("dull", "ring", "clang", "silence");

    /**
     * Difficulty tiers for {@link #harbour(String, Tier)}: how many blasts, how sharply the echo costs separate lanes
     * (a wide spread means telling echoes) and the percent chance a blast's echo is lost in the fog. Greedy-loss
     * rates over seeds 1..300 (pinned by FogChannelPilotTest): CALM 146, FOG 233, PEA_SOUP 264 (classic 182).
     */
    public enum Tier {
        CALM(2, 5, 14, 0), FOG(4, 10, 7, 10), PEA_SOUP(8, 16, 4, 30);

        private final int minBlasts;
        private final int maxBlasts;
        private final int echoSpread;
        private final int missPercent;

        Tier(int minBlasts, int maxBlasts, int echoSpread, int missPercent) {
            this.minBlasts = minBlasts;
            this.maxBlasts = maxBlasts;
            this.echoSpread = echoSpread;
            this.missPercent = missPercent;
        }

        public int minBlasts() {
            return minBlasts;
        }

        public int maxBlasts() {
            return maxBlasts;
        }

        public int echoSpread() {
            return echoSpread;
        }

        public int missPercent() {
            return missPercent;
        }

        /** Seed prefix used by the tests and parity files, e.g. "pea-soup-". */
        public String seedPrefix() {
            return name().toLowerCase(java.util.Locale.ROOT).replace('_', '-') + "-";
        }
    }

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
                if (h < 0 || h > MISSED) {
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
        int t = 1 + rnd.below(CLASSIC_BLASTS);
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

    /**
     * Tiered harbour from {@code random.Random(seed)}: channels in [2, 4], blasts in the tier's range, opening and
     * drift costs as in {@link #harbour(String)}, echo costs below the tier's spread, then for every blast one
     * draw below 100 (under missPercent: the echo is missed) and, if heard, the echo kind.
     */
    public static Harbour harbour(String seed, Tier tier) {
        PyStringRandom rnd = new PyStringRandom(seed);
        int s = 2 + rnd.below(3);
        int t = tier.minBlasts() + rnd.below(tier.maxBlasts() - tier.minBlasts() + 1);
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
                echo[i][o] = rnd.below(tier.echoSpread());
            }
        }
        int[] heard = new int[t];
        for (int k = 0; k < t; k++) {
            heard[k] = rnd.below(100) < tier.missPercent() ? MISSED : rnd.below(ECHOES);
        }
        return new Harbour(open, drift, echo, heard);
    }

    /** Echo cost of blast {@code k} from lane {@code l}; a missed echo costs nothing anywhere. */
    private static int echoCost(Harbour h, int l, int k) {
        int e = h.heard[k];
        return e == MISSED ? 0 : h.echo[l][e];
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
            cost[0][i] = h.open[i] + echoCost(h, i, 0);
        }
        for (int k = 1; k < t; k++) {
            for (int j = 0; j < s; j++) {
                int bestPrev = 0;
                for (int i = 1; i < s; i++) {
                    if (cost[k - 1][i] + h.drift[i][j] < cost[k - 1][bestPrev] + h.drift[bestPrev][j]) {
                        bestPrev = i;
                    }
                }
                cost[k][j] = cost[k - 1][bestPrev] + h.drift[bestPrev][j] + echoCost(h, j, k);
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

    /**
     * The dockhand's habit: each blast on its own, the lane its echo surprises least (lower lane on ties); when an
     * echo is missed the dockhand holds the last lane (lane 0 before any echo).
     */
    public static Track loudestEcho(Harbour h) {
        int[] lanes = new int[h.blasts()];
        for (int k = 0; k < lanes.length; k++) {
            if (h.heard[k] == MISSED) {
                lanes[k] = k == 0 ? 0 : lanes[k - 1];
                continue;
            }
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
            total += (k == 0 ? h.open[l] : h.drift[lanes[k - 1]][l]) + echoCost(h, l, k);
        }
        return total;
    }

    /** Quest q_pilot_through_fog: the pilot's reading is a real track and no track explains the fog better. */
    public static boolean quest(Harbour h, int[] lanes) {
        int got = cost(h, lanes);
        return got != INVALID && got == best(h).cost();
    }

    /** How a reading scores against par (the best possible cost): stars 3 at par, 2 within PAR_SLACK, 1 otherwise, 0 invalid. */
    public record Judgement(int cost, int par, int stars, boolean questDone) { }

    /** Par for a harbour: the cost of the best reading. */
    public static int par(Harbour h) {
        return best(h).cost();
    }

    /** Scores a reading for the host (stars, par, quest flag) without the host re-running the solver. */
    public static Judgement judge(Harbour h, int[] lanes) {
        int got = cost(h, lanes);
        int p = par(h);
        int stars = got == INVALID ? 0 : got == p ? 3 : got <= p + PAR_SLACK ? 2 : 1;
        return new Judgement(got, p, stars, stars == 3);
    }

    /** One blast of the best reading: the lane, what was heard, what it cost and what the echo alone suggested. */
    public record Step(int blast, int lane, int heard, int moveCost, int echoCost, int greedyLane) {
        /** Plain words for the step, identical to FogExplain in the C++ core. */
        public String text(int previousLane) {
            String move = blast == 0 ? "open" : lane == previousLane ? "hold" : "drift";
            String why = blast == 0 ? "open" : lane == previousLane ? "stay" : "drift";
            return "blast " + (blast + 1) + ": heard " + ECHO_NAMES.get(heard) + ", " + move + " lane " + lane + " (+" + moveCost
                    + " " + why + ", +" + echoCost + " echo)" + (greedyLane != lane ? "; the echo alone says lane " + greedyLane : "");
        }
    }

    /** Why the pilot chose each lane: the best reading step by step, against the trust-each-echo lane. */
    public static List<Step> explain(Harbour h) {
        int[] b = best(h).lanes();
        int[] g = loudestEcho(h).lanes();
        List<Step> out = new ArrayList<>();
        for (int k = 0; k < b.length; k++) {
            int l = b[k];
            int move = k == 0 ? h.open[l] : h.drift[b[k - 1]][l];
            out.add(new Step(k, l, h.heard[k], move, echoCost(h, l, k), g[k]));
        }
        return out;
    }

    /** The explanation as text, one line per blast. */
    public static List<String> explainText(Harbour h) {
        List<Step> steps = explain(h);
        List<String> out = new ArrayList<>();
        for (int k = 0; k < steps.size(); k++) {
            out.add(steps.get(k).text(k == 0 ? -1 : steps.get(k - 1).lane()));
        }
        return out;
    }
}
