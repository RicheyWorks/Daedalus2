// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * G504 The Trotting Ring (Studio horse lane): a show ring is split into segments and the judge
 * calls a tempo for each one: walk, trot or canter. The rider picks one gait per segment. A gait
 * that matches the call scores 2, one step off scores 1, two steps off scores 0. Trot costs the
 * horse 1 stamina, canter costs 2, and walk gives back 1 (up to the horse's maximum). A gait the
 * horse cannot pay for is not allowed. {@link #best} plans the highest-scoring round with a
 * small dynamic program over (segment, stamina); {@link #eager} (always obey the judge when the
 * horse can afford it) is the habit that leaves the horse spent before the final canter. Plain
 * int[] API: gaits are {@link #WALK}, {@link #TROT}, {@link #CANTER}.
 */
public final class TrottingRing {

    public static final String QUEST_ID = "q_blue_rosette";
    public static final int WALK = 0;
    public static final int TROT = 1;
    public static final int CANTER = 2;

    /** A planned round: total score and the gait chosen for every segment. */
    public record Round(int score, int[] gaits) {
        public Round {
            gaits = gaits.clone();
        }

        @Override
        public int[] gaits() {
            return gaits.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Round r && r.score == score && Arrays.equals(r.gaits, gaits);
        }

        @Override
        public int hashCode() {
            return 31 * score + Arrays.hashCode(gaits);
        }

        @Override
        public String toString() {
            return "Round[" + score + ", " + Arrays.toString(gaits) + "]";
        }
    }

    private TrottingRing() { }

    /** Seeded judge calls for {@code n} segments, each WALK, TROT or CANTER. */
    public static int[] calls(long seed, int n) {
        if (n < 0) {
            throw new IllegalArgumentException("bad ring");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int[] c = new int[n];
        for (int i = 0; i < n; i++) {
            c[i] = rnd.nextInt(3);
        }
        return c;
    }

    /** Stamina cost of a gait: walk -1 (recovery), trot 1, canter 2. */
    public static int cost(int gait) {
        checkGait(gait);
        return gait == WALK ? -1 : gait;
    }

    /** Points for riding {@code gait} when the judge called {@code call}. */
    public static int points(int call, int gait) {
        checkGait(call);
        checkGait(gait);
        return 2 - Math.abs(call - gait);
    }

    /** Highest-scoring legal round for a horse that starts with full stamina {@code maxStamina}. */
    public static Round best(int[] calls, int maxStamina) {
        checkStamina(maxStamina);
        int n = calls.length;
        int neg = Integer.MIN_VALUE / 2;
        // score[i][s]: best score from segment i onward with stamina s.
        int[][] score = new int[n + 1][maxStamina + 1];
        int[][] pick = new int[n][maxStamina + 1];
        for (int i = n - 1; i >= 0; i--) {
            for (int s = 0; s <= maxStamina; s++) {
                int bestScore = neg;
                int bestGait = WALK;
                for (int g = WALK; g <= CANTER; g++) {
                    int next = s - cost(g);
                    if (next < 0) {
                        continue;
                    }
                    next = Math.min(next, maxStamina);
                    int v = points(calls[i], g) + score[i + 1][next];
                    if (v > bestScore) {
                        bestScore = v;
                        bestGait = g;
                    }
                }
                score[i][s] = bestScore;
                pick[i][s] = bestGait;
            }
        }
        int[] gaits = new int[n];
        int s = maxStamina;
        for (int i = 0; i < n; i++) {
            gaits[i] = pick[i][s];
            s = Math.min(s - cost(gaits[i]), maxStamina);
        }
        return new Round(n == 0 ? 0 : score[0][maxStamina], gaits);
    }

    /** Naive: ride the called gait whenever affordable, otherwise the fastest affordable one. */
    public static Round eager(int[] calls, int maxStamina) {
        checkStamina(maxStamina);
        int[] gaits = new int[calls.length];
        int s = maxStamina;
        int total = 0;
        for (int i = 0; i < calls.length; i++) {
            int g = calls[i];
            while (s - cost(g) < 0) {
                g--;
            }
            gaits[i] = g;
            total += points(calls[i], g);
            s = Math.min(s - cost(g), maxStamina);
        }
        return new Round(total, gaits);
    }

    /** Score of a rider's plan, or -1 when the plan is the wrong length or tires the horse out. */
    public static int score(int[] calls, int[] gaits, int maxStamina) {
        checkStamina(maxStamina);
        if (gaits.length != calls.length) {
            return -1;
        }
        int s = maxStamina;
        int total = 0;
        for (int i = 0; i < calls.length; i++) {
            if (gaits[i] < WALK || gaits[i] > CANTER) {
                return -1;
            }
            int next = s - cost(gaits[i]);
            if (next < 0) {
                return -1;
            }
            s = Math.min(next, maxStamina);
            total += points(calls[i], gaits[i]);
        }
        return total;
    }

    /** Quest q_blue_rosette: the rider's round is legal and earns the best possible score. */
    public static boolean quest(int[] calls, int[] riderGaits, int maxStamina) {
        int got = score(calls, riderGaits, maxStamina);
        return got >= 0 && got == best(calls, maxStamina).score();
    }

    private static void checkGait(int gait) {
        if (gait < WALK || gait > CANTER) {
            throw new IllegalArgumentException("bad gait " + gait);
        }
    }

    private static void checkStamina(int maxStamina) {
        if (maxStamina < 0) {
            throw new IllegalArgumentException("bad stamina");
        }
    }
}
