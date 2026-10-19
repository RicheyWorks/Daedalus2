// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Keeper's Call (contest G121): call-and-response memory; the Keeper trains the bell crews by ear.
 *
 * <p>The harbour Keeper rings a seeded phrase on {@link #BELLS} low bells (pitches from
 * {@link DripCaveChorus#hz(int)}, A3 pentatonic) with short or long strokes (lengths from
 * {@link FogBellCallSigns#SHORT_MS} / {@link FogBellCallSigns#LONG_MS}). Round {@code r} plays the first
 * {@code r} strokes; the player echoes them. A wrong bell or a wrong length ends the run. Score is the
 * longest phrase echoed; stars at 6, 9 and 12. Phrases never ring the same bell three times running.
 * Every bell pitch passes {@link EarRule#check}.
 */
public final class KeepersCall {
    /** Bells the Keeper uses. */
    public static final int BELLS = 5;
    /** Longest phrase. */
    public static final int MAX_LENGTH = 16;
    /** Gap between strokes, ms. */
    public static final int GAP_MS = 220;
    private static final long SALT = 0x4B43_4C31L; // "KCL1"

    /** One stroke: which bell, and whether it rang long. */
    public record Stroke(int bell, boolean isLong) {
        /** Validates. */
        public Stroke {
            if (bell < 0 || bell >= BELLS) {
                throw new IllegalArgumentException("bell 0-" + (BELLS - 1));
            }
        }

        /** Stroke length, ms. */
        public int lengthMs() {
            return isLong ? FogBellCallSigns.LONG_MS : FogBellCallSigns.SHORT_MS;
        }

        /** Bell pitch (ear-rule checked). */
        public double hz() {
            return KeepersCall.hz(bell);
        }
    }

    private final long seed;
    private final List<Stroke> phrase;

    private KeepersCall(long seed, List<Stroke> phrase) {
        this.seed = seed;
        this.phrase = List.copyOf(phrase);
    }

    /** A seeded phrase. */
    public static KeepersCall seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        List<Stroke> p = new ArrayList<>();
        while (p.size() < MAX_LENGTH) {
            int bell = (int) Long.remainderUnsigned(rng.nextLong(), BELLS);
            int n = p.size();
            if (n >= 2 && p.get(n - 1).bell() == bell && p.get(n - 2).bell() == bell) {
                continue;
            }
            p.add(new Stroke(bell, (rng.nextLong() & 3) == 0));
        }
        return new KeepersCall(seed, p);
    }

    /** Pitch of bell {@code i} (ear-rule checked). */
    public static double hz(int bell) {
        return EarRule.check(DripCaveChorus.hz(bell), "keeper's bell");
    }

    /** Stars for a score. */
    public static int stars(int score) {
        return score >= 12 ? 3 : score >= 9 ? 2 : score >= 6 ? 1 : 0;
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** The Keeper's call for round {@code r} (1-based). */
    public List<Stroke> call(int round) {
        if (round < 1 || round > MAX_LENGTH) {
            throw new IllegalArgumentException("round 1-" + MAX_LENGTH);
        }
        return phrase.subList(0, round);
    }

    /** Onset of each stroke in a call, ms. */
    public static List<Integer> onsets(List<Stroke> call) {
        List<Integer> out = new ArrayList<>();
        int t = 0;
        for (Stroke s : call) {
            out.add(t);
            t += s.lengthMs() + GAP_MS;
        }
        return out;
    }

    /** Start a run. */
    public Run start() {
        return new Run();
    }

    /** One player's run through the rounds. */
    public final class Run {
        private int round = 1;
        private int score;
        private boolean over;

        private Run() { }

        /** The current round (1-based). */
        public int round() {
            return round;
        }

        /** What the Keeper rings this round. */
        public List<Stroke> call() {
            return KeepersCall.this.call(round);
        }

        /** Echo this round; true when it matched. A miss ends the run. */
        public boolean echo(List<Stroke> answer) {
            if (over) {
                throw new IllegalStateException("run is over");
            }
            if (!call().equals(answer)) {
                over = true;
                return false;
            }
            score = round;
            if (round == MAX_LENGTH) {
                over = true;
            } else {
                round++;
            }
            return true;
        }

        /** True once the run has ended. */
        public boolean over() {
            return over;
        }

        /** Longest phrase echoed. */
        public int score() {
            return score;
        }
    }
}