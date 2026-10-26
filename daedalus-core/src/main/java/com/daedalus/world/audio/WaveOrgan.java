// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Wave Organ (contest G109): the sea wall hums when the arks come in on the tide.
 *
 * <p>Waves push air through salvaged pipes set in the sea wall. Each pipe is closed at the sea end and
 * sounds {@code f = c / (4 (L + 0.3 d))} (length plus end correction; {@link #frequency}). A seeded pile of
 * {@link #PILE} pipes hides a triad; the player picks 3 pipes that sound a major or minor triad, each pipe
 * within {@link #TOLERANCE_CENTS} of equal temperament on a common root. Every pitch passes
 * {@link EarRule#check} (they all sit roughly 70-280 Hz).
 */
public final class WaveOrgan {
    /** Pipes in a pile. */
    public static final int PILE = 8;
    /** Speed of sound, m/s. */
    public static final double C = 343.0;
    /** Allowed detuning per pipe, cents. */
    public static final double TOLERANCE_CENTS = 15.0;
    private static final long SALT = 0x574F_5231L; // "WOR1"

    /** A salvaged pipe. */
    public record Pipe(double lengthM, double diameterM) { }

    /** A judged pick. */
    public record Verdict(boolean triad, String chord, double worstCents, String reason) { }

    private final long seed;
    private final List<Pipe> pile;

    private WaveOrgan(long seed, List<Pipe> pile) {
        this.seed = seed;
        this.pile = List.copyOf(pile);
    }

    /** A seeded pile: one hidden triad (root A2-E3) plus decoys, shuffled. */
    public static WaveOrgan seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        int root = 45 + (int) Long.remainderUnsigned(rng.nextLong(), 8);
        int third = (rng.nextLong() & 1) == 0 ? 4 : 3;
        List<Pipe> pile = new ArrayList<>();
        for (int step : new int[] {0, third, 7}) {
            double d = diameter(rng);
            double l = C / (4 * hz(root + step)) - 0.3 * d;
            pile.add(new Pipe(Math.round(l * 1000) / 1000.0, d));
        }
        while (pile.size() < PILE) {
            pile.add(new Pipe((300 + Long.remainderUnsigned(rng.nextLong(), 901)) / 1000.0, diameter(rng)));
        }
        for (int i = pile.size() - 1; i > 0; i--) {
            int j = (int) Long.remainderUnsigned(rng.nextLong(), i + 1);
            Pipe t = pile.get(i);
            pile.set(i, pile.get(j));
            pile.set(j, t);
        }
        return new WaveOrgan(seed, pile);
    }

    private static double diameter(Rng rng) {
        return (50 + Long.remainderUnsigned(rng.nextLong(), 71)) / 1000.0;
    }

    private static double hz(int midi) {
        return 440.0 * Math.pow(2, (midi - 69) / 12.0);
    }

    /** Sounding pitch of a closed pipe (ear-rule checked). */
    public static double frequency(Pipe p) {
        return EarRule.check(C / (4 * (p.lengthM() + 0.3 * p.diameterM())), "wave organ pipe");
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** The pile. */
    public List<Pipe> pile() {
        return pile;
    }

    /** Judge three picked pipe indices. */
    public Verdict judge(List<Integer> pick) {
        if (pick == null || pick.size() != 3 || pick.stream().distinct().count() != 3
                || pick.stream().anyMatch(i -> i < 0 || i >= PILE)) {
            return new Verdict(false, "", 0, "pick 3 different pipes");
        }
        double[] m = new double[3];
        for (int k = 0; k < 3; k++) {
            m[k] = 69 + 12 * Math.log(frequency(pile.get(pick.get(k))) / 440.0) / Math.log(2);
        }
        Arrays.sort(m);
        int root = (int) Math.round(m[0]);
        String best = null;
        double bestWorst = Double.MAX_VALUE;
        for (int third : new int[] {4, 3}) {
            int[] steps = {0, third, 7};
            double worst = 0;
            for (int k = 0; k < 3; k++) {
                worst = Math.max(worst, Math.abs(m[k] - (root + steps[k])) * 100);
            }
            if (worst < bestWorst) {
                bestWorst = worst;
                best = HerbChord.noteName(Math.floorMod(root, 12)) + (third == 4 ? " major" : " minor");
            }
        }
        boolean ok = bestWorst <= TOLERANCE_CENTS;
        return new Verdict(ok, best, bestWorst, ok ? "the sea wall sings " + best : "out of tune by " + Math.round(bestWorst) + " cents");
    }

    /** Every 3-pipe pick that sounds a triad (exhaustive). */
    public List<List<Integer>> solutions() {
        List<List<Integer>> out = new ArrayList<>();
        for (int a = 0; a < PILE; a++) {
            for (int b = a + 1; b < PILE; b++) {
                for (int c = b + 1; c < PILE; c++) {
                    if (judge(List.of(a, b, c)).triad()) {
                        out.add(List.of(a, b, c));
                    }
                }
            }
        }
        return out;
    }
}