// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Dawn Chorus Census (contest G124): regrowth is heard before it is seen.
 *
 * <p>The regrown meadow's dawn chorus comes from a seeded habitat: {@link #SPECIES} each have 0-6
 * individuals, and every individual calls once per its species' period, at its own phase, through a
 * {@link #LISTEN_MS} ms dawn. The player listens to the soundscape ({@link #soundscape()}: onset + pitch)
 * and names the most abundant species (by individuals, not calls) and the one species missing this season.
 * Periods divide the minute, so individuals = calls x period / 60 s exactly. All call pitches are low-mid
 * and pass {@link EarRule#check}.
 */
public final class DawnChorusCensus {
    /** Length of the dawn listened to, ms. */
    public static final int LISTEN_MS = 60_000;
    /** The meadow's species: name, call pitch (Hz), call period (s). */
    public static final List<Species> SPECIES = List.of(new Species("frog", 130.813, 3), new Species("heron", 164.814, 6),
        new Species("owl", 195.998, 10), new Species("dove", 246.942, 5), new Species("cricket", 329.628, 2),
        new Species("wren", 391.995, 4));
    private static final long SALT = 0x4443_4E31L; // "DCN1"

    /** A meadow species. */
    public record Species(String name, double hz, int periodS) { }

    /** One heard call. */
    public record Call(int onsetMs, double hz) { }

    /** A judged census. */
    public record Verdict(boolean correct, boolean rightLoudest, boolean rightMissing, String loudest, String missing) { }

    private final long seed;
    private final int[] counts;
    private final List<Call> calls;

    private DawnChorusCensus(long seed, int[] counts, List<Call> calls) {
        this.seed = seed;
        this.counts = counts.clone();
        this.calls = List.copyOf(calls);
    }

    /** A seeded dawn: one species missing, one clearly most abundant. */
    public static DawnChorusCensus seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        int n = SPECIES.size();
        int[] counts = new int[n];
        int missing = (int) Long.remainderUnsigned(rng.nextLong(), n);
        int top = (int) Long.remainderUnsigned(rng.nextLong(), n - 1);
        if (top >= missing) {
            top++;
        }
        for (int i = 0; i < n; i++) {
            counts[i] = i == missing ? 0 : 1 + (int) Long.remainderUnsigned(rng.nextLong(), 4);
        }
        counts[top] = 5 + (int) Long.remainderUnsigned(rng.nextLong(), 2);
        List<Call> calls = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            Species s = SPECIES.get(i);
            double hz = EarRule.check(s.hz(), s.name() + " call");
            int period = s.periodS() * 1000;
            for (int j = 0; j < counts[i]; j++) {
                int phase = (int) Long.remainderUnsigned(rng.nextLong(), period);
                for (int t = phase; t < LISTEN_MS; t += period) {
                    calls.add(new Call(t, hz));
                }
            }
        }
        calls.sort(Comparator.comparingInt(Call::onsetMs).thenComparingDouble(Call::hz));
        return new DawnChorusCensus(seed, counts, calls);
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** Every call heard at dawn, in time order. */
    public List<Call> soundscape() {
        return calls;
    }

    /** Individuals per species counted from a soundscape (calls x period / 60 s). */
    public static List<Integer> census(List<Call> heard) {
        List<Integer> out = new ArrayList<>();
        for (Species s : SPECIES) {
            long n = heard.stream().filter(c -> c.hz() == s.hz()).count();
            out.add((int) (n * s.periodS() * 1000 / LISTEN_MS));
        }
        return out;
    }

    /** The answer: {most abundant, missing} species names. */
    public List<String> solution() {
        List<Integer> c = census(calls);
        int top = 0;
        int missing = 0;
        for (int i = 0; i < c.size(); i++) {
            if (c.get(i) > c.get(top)) {
                top = i;
            }
            if (c.get(i) == 0) {
                missing = i;
            }
        }
        return List.of(SPECIES.get(top).name(), SPECIES.get(missing).name());
    }

    /** Judge the player's census. */
    public Verdict judge(String loudest, String missing) {
        int top = 0;
        int gone = 0;
        for (int i = 0; i < counts.length; i++) {
            if (counts[i] > counts[top]) {
                top = i;
            }
            if (counts[i] == 0) {
                gone = i;
            }
        }
        String t = SPECIES.get(top).name();
        String g = SPECIES.get(gone).name();
        boolean a = t.equals(loudest);
        boolean b = g.equals(missing);
        return new Verdict(a && b, a, b, t, g);
    }
}