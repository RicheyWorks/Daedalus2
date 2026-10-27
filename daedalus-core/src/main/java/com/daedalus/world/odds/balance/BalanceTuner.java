// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;

/**
 * Seeded, bounded grid search over a {@link TunableGame}'s knobs. Every grid point is scored with the same
 * {@code searchTrials} seeded sessions (common random numbers, trial {@code t} uses {@link OddsRng#forTrial}), so the
 * search is deterministic and points are compared on equal luck. Then, softest mode first, it picks the in-band point
 * nearest the shipped values (or, for a mode the game lacks, nearest the previous mode's pick), requires its 95%
 * Wilson interval to sit wholly inside the mode's band and wholly below the softer mode's interval (strict
 * easy &gt; normal &gt; hard), and re-confirms it on a fresh seed with {@code confirmTrials} sessions.
 */
public final class BalanceTuner {

    /** How many ranked candidates per mode get a confirming run before the mode is reported as not found. */
    static final int CONFIRM_TRIES = 8;

    private final BalanceCheck check;
    private final int searchTrials;
    private final int confirmTrials;
    private final long maxSessions;

    public BalanceTuner(BalanceCheck check, int searchTrials, int confirmTrials, long maxSessions) {
        if (searchTrials < 1 || confirmTrials < 1 || maxSessions < 1) {
            throw new IllegalArgumentException("trials and session cap must be >= 1");
        }
        this.check = check;
        this.searchTrials = searchTrials;
        this.confirmTrials = confirmTrials;
        this.maxSessions = maxSessions;
    }

    /** Every knob combination, first knob slowest. */
    static List<int[]> grid(List<Knob> knobs) {
        List<int[]> out = new ArrayList<>();
        out.add(new int[0]);
        for (Knob k : knobs) {
            List<int[]> next = new ArrayList<>();
            for (int[] prefix : out) {
                for (int i = 0; i < k.size(); i++) {
                    int[] p = Arrays.copyOf(prefix, prefix.length + 1);
                    p[prefix.length] = k.value(i);
                    next.add(p);
                }
            }
            out = next;
        }
        return out;
    }

    /** Plays {@code trials} seeded sessions at one setting. */
    static ModeResult measure(TunableGame game, String difficulty, int[] knobs, long seed, int trials) {
        int wins = 0;
        double scoreSum = 0;
        for (int t = 0; t < trials; t++) {
            SessionOutcome o = game.play(knobs, OddsRng.forTrial(seed, t));
            if (o.won()) {
                wins++;
            }
            scoreSum += o.score();
        }
        return new ModeResult(game.id(), difficulty, trials, wins, scoreSum / trials, Intervals.wilson(wins, trials));
    }

    private boolean inBand(ModeResult r, String difficulty) {
        BalanceBand b = check.bandFor(difficulty);
        return r.low() >= b.floor() && r.high() <= b.ceiling();
    }

    private static boolean below(ModeResult harder, ModeResult softer) {
        return softer == null || harder.high() < softer.low();
    }

    static double distance(int[] a, int[] anchor, List<Knob> knobs) {
        if (anchor == null) {
            return 0;
        }
        double d = 0;
        for (int i = 0; i < a.length; i++) {
            d += Math.abs(a[i] - anchor[i]) / (double) knobs.get(i).step();
        }
        return d;
    }

    /** Suggestions for every difficulty of {@code game}, softest first. */
    public List<Suggestion> tune(TunableGame game, long seed) {
        List<Knob> knobs = game.knobs();
        List<int[]> points = grid(knobs);
        long sessions = (long) points.size() * searchTrials
                + (long) game.difficulties().size() * CONFIRM_TRIES * confirmTrials;
        if (sessions > maxSessions) {
            throw new IllegalArgumentException(game.id() + ": " + sessions + " sessions exceeds cap " + maxSessions);
        }
        List<ModeResult> scored = new ArrayList<>(points.size());
        for (int[] p : points) {
            scored.add(measure(game, "grid", p, seed, searchTrials));
        }
        List<Suggestion> out = new ArrayList<>();
        ModeResult softer = null;
        int[] previous = null;
        long confirmSeed = seed ^ 0x5DEECE66DL;
        for (String d : game.difficulties()) {
            int[] shipped = game.shipped(d);
            int[] anchor = shipped != null ? shipped : previous;
            BalanceBand band = check.bandFor(d);
            double mid = (band.floor() + band.ceiling()) / 2;
            List<Integer> ok = new ArrayList<>();
            for (int i = 0; i < points.size(); i++) {
                ModeResult r = scored.get(i);
                if (inBand(r, d) && below(r, softer)) {
                    ok.add(i);
                }
            }
            ok.sort(Comparator.<Integer>comparingDouble(i -> distance(points.get(i), anchor, knobs))
                    .thenComparingDouble(i -> Math.abs(scored.get(i).winRate() - mid)).thenComparingInt(i -> i));
            Suggestion s = new Suggestion(game.id(), d, shipped, null, null, ok.size());
            for (int k = 0; k < Math.min(CONFIRM_TRIES, ok.size()); k++) {
                int[] p = points.get(ok.get(k));
                ModeResult c = measure(game, d, p, confirmSeed, confirmTrials);
                if (inBand(c, d) && below(c, softer)) {
                    s = new Suggestion(game.id(), d, shipped, p, c, ok.size());
                    break;
                }
            }
            if (s.found()) {
                softer = s.confirm();
                previous = s.suggested();
            }
            out.add(s);
        }
        return out;
    }

    /** True if every result's interval sits wholly below the one before it (strictly easier first). */
    public static boolean monotonic(List<ModeResult> softestFirst) {
        for (int i = 1; i < softestFirst.size(); i++) {
            if (!(softestFirst.get(i).high() < softestFirst.get(i - 1).low())) {
                return false;
            }
        }
        return true;
    }
}
