// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

/**
 * Hull Knock Survey (contest G101): arks must be sound before they carry life off the planet.
 *
 * <p>A seeded hull has 8-12 plates, each with a thickness (4/5/6/8 mm) and a length (0.60-1.20 m). A sound
 * plate rings at {@code f = K * t / L^2} ({@link #expectedHz}), all between 50 and 400 Hz (Richey's ear rule:
 * low-mid, nothing piercing), give or take {@link #JITTER} for the workshop's uneven bolts. 1-3 cracked
 * plates ring 10-20% low and short. The player marks the cracked plates; the judge counts hits, misses and
 * false alarms. Anything heard more than {@link #CRACK_THRESHOLD} below its expected pitch is cracked.
 *
 * <p>Ear rules: knock gain {@link #GAIN}; sound plates ring {@link #SOUND_RING_MS} ms, cracked plates
 * {@link #CRACK_RING_MS} ms.
 */
public final class HullKnockSurvey {
    /** Plate constant (Hz * m^2 / mm): t = 8 mm, L = 0.6 m rings at 400 Hz. */
    public static final double K = 18.0;
    /** Max detuning of a sound plate (fraction). */
    public static final double JITTER = 0.015;
    /** Drop below expected pitch that marks a crack (fraction). */
    public static final double CRACK_THRESHOLD = 0.05;
    /** Knock gain. */
    public static final double GAIN = 0.35;
    /** Ring of a sound plate, ms. */
    public static final int SOUND_RING_MS = 1800;
    /** Ring of a cracked plate, ms. */
    public static final int CRACK_RING_MS = 400;
    private static final int[] THICK = {4, 5, 6, 8};
    private static final long SALT = 0x484B_5331L; // "HKS1"

    /** One plate as knocked. */
    public record Plate(int thicknessMm, double lengthM, double heardHz, int ringMs) { }

    /** A judged survey. */
    public record Verdict(boolean perfect, int hits, int misses, int falseAlarms, Set<Integer> cracked) {
        /** Defensive copy. */
        public Verdict {
            cracked = Set.copyOf(cracked);
        }
    }

    private final long seed;
    private final List<Plate> plates;
    private final Set<Integer> cracked;

    private HullKnockSurvey(long seed, List<Plate> plates, Set<Integer> cracked) {
        this.seed = seed;
        this.plates = List.copyOf(plates);
        this.cracked = Set.copyOf(cracked);
    }

    /** A seeded hull. */
    public static HullKnockSurvey seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        int n = 8 + (int) Long.remainderUnsigned(rng.nextLong(), 5);
        int k = 1 + (int) Long.remainderUnsigned(rng.nextLong(), 3);
        Set<Integer> cracked = new TreeSet<>();
        while (cracked.size() < k) {
            cracked.add((int) Long.remainderUnsigned(rng.nextLong(), n));
        }
        List<Plate> plates = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            int t = THICK[(int) Long.remainderUnsigned(rng.nextLong(), THICK.length)];
            double l = (60 + Long.remainderUnsigned(rng.nextLong(), 61)) / 100.0;
            double f = expectedHz(t, l);
            double u = Long.remainderUnsigned(rng.nextLong(), 2001) / 1000.0 - 1.0; // -1..1
            boolean bad = cracked.contains(i);
            double heard = bad ? f * (1 - (0.10 + 0.10 * (u + 1) / 2)) : f * (1 + JITTER * u);
            plates.add(new Plate(t, l, Math.round(heard * 10) / 10.0, bad ? CRACK_RING_MS : SOUND_RING_MS));
        }
        return new HullKnockSurvey(seed, plates, cracked);
    }

    /** Pitch of a sound plate. */
    public static double expectedHz(int thicknessMm, double lengthM) {
        return K * thicknessMm / (lengthM * lengthM);
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** The plates, bow to stern. */
    public List<Plate> plates() {
        return plates;
    }

    /** Plates judged cracked from what was heard. */
    public Set<Integer> solution() {
        Set<Integer> out = new TreeSet<>();
        for (int i = 0; i < plates.size(); i++) {
            Plate p = plates.get(i);
            if (p.heardHz() < expectedHz(p.thicknessMm(), p.lengthM()) * (1 - CRACK_THRESHOLD)) {
                out.add(i);
            }
        }
        return out;
    }

    /** Judge the plates the player marked. */
    public Verdict judge(Set<Integer> marked) {
        Set<Integer> m = marked == null ? Set.of() : marked;
        int hits = 0;
        int falseAlarms = 0;
        for (int i : m) {
            if (cracked.contains(i)) {
                hits++;
            } else {
                falseAlarms++;
            }
        }
        int misses = cracked.size() - hits;
        return new Verdict(misses == 0 && falseAlarms == 0, hits, misses, falseAlarms, cracked);
    }
}