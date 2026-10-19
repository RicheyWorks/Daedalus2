// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Frog Pond Niches (contest G130): regrown wetlands sort themselves by ear.
 *
 * <p>5-7 seeded frog species return to the regrown wetland. A frog's dominant call frequency falls with body
 * size ({@link #dominantHz}: {@code 2400 / sqrt(SVL mm)}, so a 20 mm peeper calls near 540 Hz and a 150 mm
 * bullfrog near 200 Hz), and each call spans a band of +-{@link #BAND} around it. Acoustic niche
 * partitioning: species whose bands overlap mask each other's calls and cannot breed in the same pond. The
 * player assigns every species to one of {@link #PONDS} ponds; the judge names the first masking pair.
 * Seeds are re-drawn until a valid assignment exists ({@link #solution()} backtracks). Every call pitch
 * passes {@link EarRule#check}.
 */
public final class FrogPondNiches {
    /** Ponds in the wetland. */
    public static final int PONDS = 3;
    /** Half-width of a call band, as a fraction of the dominant frequency. */
    public static final double BAND = 0.12;
    private static final List<String> NAMES = List.of("reed peeper", "chorus frog", "leopard frog", "green frog",
        "wood frog", "spadefoot", "tree frog", "bullfrog", "pickerel frog", "cricket frog");
    private static final long SALT = 0x4650_4E31L; // "FPN1"

    /** A returning species: name and snout-vent length (mm). */
    public record Frog(String name, int svlMm) {
        /** Dominant call frequency (ear-rule checked). */
        public double hz() {
            return dominantHz(svlMm);
        }
    }

    /** A judged assignment. */
    public record Verdict(boolean ok, String reason) { }

    private final long seed;
    private final List<Frog> frogs;

    private FrogPondNiches(long seed, List<Frog> frogs) {
        this.seed = seed;
        this.frogs = List.copyOf(frogs);
    }

    /** A seeded wetland with a valid assignment. */
    public static FrogPondNiches seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        while (true) {
            int n = 5 + (int) Long.remainderUnsigned(rng.nextLong(), 3);
            List<String> pool = new ArrayList<>(NAMES);
            List<Frog> frogs = new ArrayList<>();
            for (int i = 0; i < n; i++) {
                String name = pool.remove((int) Long.remainderUnsigned(rng.nextLong(), pool.size()));
                frogs.add(new Frog(name, 20 + (int) Long.remainderUnsigned(rng.nextLong(), 131)));
            }
            FrogPondNiches w = new FrogPondNiches(seed, frogs);
            if (w.solution() != null) {
                return w;
            }
        }
    }

    /** Dominant call frequency of a frog of {@code svlMm} (ear-rule checked). */
    public static double dominantHz(int svlMm) {
        if (svlMm <= 0) {
            throw new IllegalArgumentException("body size must be positive");
        }
        return EarRule.check(2400.0 / Math.sqrt(svlMm), "frog call");
    }

    /** True when two frogs' call bands overlap (they mask each other). */
    public static boolean masks(Frog a, Frog b) {
        double fa = a.hz();
        double fb = b.hz();
        return fa * (1 - BAND) <= fb * (1 + BAND) && fb * (1 - BAND) <= fa * (1 + BAND);
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** The returning species. */
    public List<Frog> frogs() {
        return frogs;
    }

    /** A valid pond per frog, or null when none exists. */
    public List<Integer> solution() {
        int[] pond = new int[frogs.size()];
        if (!place(0, pond)) {
            return null;
        }
        List<Integer> out = new ArrayList<>();
        for (int p : pond) {
            out.add(p);
        }
        return out;
    }

    private boolean place(int i, int[] pond) {
        if (i == frogs.size()) {
            return true;
        }
        for (int p = 0; p < PONDS; p++) {
            boolean free = true;
            for (int j = 0; j < i && free; j++) {
                free = pond[j] != p || !masks(frogs.get(i), frogs.get(j));
            }
            if (free) {
                pond[i] = p;
                if (place(i + 1, pond)) {
                    return true;
                }
            }
        }
        return false;
    }

    /** Judge a pond per frog. */
    public Verdict judge(List<Integer> ponds) {
        if (ponds == null || ponds.size() != frogs.size()) {
            return new Verdict(false, "give every species a pond");
        }
        for (int p : ponds) {
            if (p < 0 || p >= PONDS) {
                return new Verdict(false, "there are only " + PONDS + " ponds");
            }
        }
        for (int i = 0; i < frogs.size(); i++) {
            for (int j = i + 1; j < frogs.size(); j++) {
                if (ponds.get(i).equals(ponds.get(j)) && masks(frogs.get(i), frogs.get(j))) {
                    return new Verdict(false, "the " + frogs.get(i).name() + " masks the " + frogs.get(j).name()
                        + " in pond " + (ponds.get(i) + 1));
                }
            }
        }
        return new Verdict(true, "every pond sings clearly");
    }
}