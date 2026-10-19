// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Drum Roll ID (contest G138): dead snags are habitat, and the drummers come back first.
 *
 * <p>Woodpeckers drum on resonant wood to hold territory, and species differ in cadence: beats per second,
 * roll length, steady versus slowing rolls, and broken, stuttering sapsucker-style rolls. A seeded roll
 * (onsets with small timing jitter) is played from the {@link #CARD field card}; the player names the
 * species. {@link #identify(List)} extracts rate, rate trend and irregularity and picks the card.
 *
 * <p>Cadences are illustrative, inspired by real North American drummers, not field-calibrated. Knock pitch
 * is a low wood thump at {@link #KNOCK_HZ} Hz ({@link EarRule#check}).
 */
public final class DrumRollId {
    /** Knock pitch (A2). */
    public static final double KNOCK_HZ = 110.0;
    /** Timing jitter per beat (fraction). */
    public static final double JITTER = 0.03;
    /** The field card. */
    public static final List<Drummer> CARD = List.of(new Drummer("downy woodpecker", 16, 0.8, 1.0, false),
        new Drummer("red-bellied woodpecker", 20, 1.0, 1.0, false), new Drummer("hairy woodpecker", 26, 1.0, 1.0, false),
        new Drummer("pileated woodpecker", 14, 2.5, 1.6, false), new Drummer("sapsucker", 18, 2.0, 1.0, true));
    private static final long SALT = 0x4452_4D31L; // "DRM1"

    /**
     * A card entry.
     *
     * @param rate beats per second at the start of the roll
     * @param seconds typical roll length
     * @param slowing last interval / first interval (1 = steady)
     * @param broken true for a roll that breaks into irregular stutters
     */
    public record Drummer(String name, double rate, double seconds, double slowing, boolean broken) { }

    private final long seed;
    private final Drummer drummer;
    private final List<Integer> onsets;

    private DrumRollId(long seed, Drummer drummer, List<Integer> onsets) {
        this.seed = seed;
        this.drummer = drummer;
        this.onsets = List.copyOf(onsets);
    }

    /** A seeded roll. */
    public static DrumRollId seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        Drummer d = CARD.get((int) Long.remainderUnsigned(rng.nextLong(), CARD.size()));
        double length = d.seconds() * (0.9 + 0.2 * unit(rng));
        double first = 1.0 / d.rate();
        List<Integer> on = new ArrayList<>();
        double t = 0;
        int beat = 0;
        while (t <= length) {
            on.add((int) Math.round(t * 1000));
            double interval = first * (1 + (d.slowing() - 1) * t / length);
            if (d.broken() && beat >= 5) {
                interval *= 1 + 2 * unit(rng);
            }
            interval *= 1 + JITTER * (2 * unit(rng) - 1);
            t += interval;
            beat++;
        }
        return new DrumRollId(seed, d, on);
    }

    private static double unit(Rng rng) {
        return Long.remainderUnsigned(rng.nextLong(), 1_000_001) / 1_000_000.0;
    }

    /** Knock pitch (ear-rule checked). */
    public static double knockHz() {
        return EarRule.check(KNOCK_HZ, "woodpecker knock");
    }

    /** Irregularity cut-off: rolls more irregular than this are broken (sapsucker-style). */
    public static final double BROKEN_CV = 0.25;

    /** Coefficient of variation of a roll's beat intervals (0 = metronomic). */
    public static double irregularity(List<Integer> onsets) {
        int n = onsets.size() - 1;
        double mean = (onsets.get(n) - onsets.get(0)) / (double) n;
        double var = 0;
        for (int i = 0; i < n; i++) {
            double v = onsets.get(i + 1) - onsets.get(i) - mean;
            var += v * v;
        }
        return Math.sqrt(var / n) / mean;
    }

    /** Opening beat rate (beats/s) over the first quarter of the roll's intervals (at least 2). */
    public static double openingRate(List<Integer> onsets) {
        int n = onsets.size() - 1;
        int q = Math.max(2, n / 4);
        return 1000.0 * q / (onsets.get(q) - onsets.get(0));
    }

    /** Identify a roll from its onsets (ms). */
    public static String identify(List<Integer> onsets) {
        if (onsets == null || onsets.size() < 8) {
            throw new IllegalArgumentException("need at least 8 beats");
        }
        int n = onsets.size() - 1;
        double[] iv = new double[n];
        for (int i = 0; i < n; i++) {
            iv[i] = onsets.get(i + 1) - onsets.get(i);
        }
        if (irregularity(onsets) > BROKEN_CV) {
            return byFlag(true);
        }
        int q = Math.max(2, n / 4);
        double early = 0;
        double late = 0;
        for (int i = 0; i < q; i++) {
            early += iv[i];
            late += iv[n - 1 - i];
        }
        if (late / early > 1.25) {
            return "pileated woodpecker";
        }
        double rate = openingRate(onsets);
        Drummer best = null;
        for (Drummer d : CARD) {
            if (!d.broken() && d.slowing() == 1.0 && (best == null || Math.abs(d.rate() - rate) < Math.abs(best.rate() - rate))) {
                best = d;
            }
        }
        return best.name();
    }

    private static String byFlag(boolean broken) {
        for (Drummer d : CARD) {
            if (d.broken() == broken) {
                return d.name();
            }
        }
        throw new IllegalStateException("card has no broken drummer");
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** The roll's beat onsets, ms. */
    public List<Integer> onsets() {
        return onsets;
    }

    /** True when the player named the drummer. */
    public boolean judge(String species) {
        return drummer.name().equals(species);
    }

    /** The drummer (for reveal after judging). */
    public String answer() {
        return drummer.name();
    }
}