// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Canon Herb Cadence (contest G81): the island's canon herbs, pressed in threes, play the homecoming cadence.
 *
 * <p>A seeded hand of 9 island canon herbs ({@link Herb#CANON}, so Doleaf = C ... Tisquill = B; names may
 * repeat) is bundled into 3 bundles of 3. Each bundle sounds through {@link HerbChord#sound(List)}, and the
 * three must form a cadence: every bundle major or minor, each root a fifth below the one before (for
 * example D, G, C). Hands are built from a hidden cadence so every hand is solvable; {@link #solutions()}
 * searches all ordered bundlings exhaustively.
 */
public final class CanonHerbCadence {
    /** Herbs per hand. */
    public static final int HAND = 9;
    private static final long SALT = 0x4348_4331L; // "CHC1"

    /** A judged pressing. */
    public record Verdict(boolean cadence, List<String> chords, String reason) {
        /** Defensive copy. */
        public Verdict {
            chords = List.copyOf(chords);
        }
    }

    private final long seed;
    private final List<String> hand;

    private CanonHerbCadence(long seed, List<String> hand) {
        this.seed = seed;
        this.hand = List.copyOf(hand);
    }

    /** A seeded hand built from a hidden major/minor cadence, shuffled. */
    public static CanonHerbCadence seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        int root = (int) Long.remainderUnsigned(rng.nextLong(), 12);
        List<String> herbs = new ArrayList<>();
        for (int c = 0; c < 3; c++) {
            int r = Math.floorMod(root - 7 * c, 12);
            int third = (rng.nextLong() & 1) == 0 ? 4 : 3;
            for (int step : new int[] {0, third, 7}) {
                herbs.add(Herb.CANON.get((r + step) % 12));
            }
        }
        for (int i = herbs.size() - 1; i > 0; i--) {
            int j = (int) Long.remainderUnsigned(rng.nextLong(), i + 1);
            String t = herbs.get(i);
            herbs.set(i, herbs.get(j));
            herbs.set(j, t);
        }
        return new CanonHerbCadence(seed, herbs);
    }

    /** A hand from explicit canon herb names (authored puzzles, tests). */
    public static CanonHerbCadence of(List<String> hand) {
        if (hand == null || hand.size() != HAND) {
            throw new IllegalArgumentException("hand needs " + HAND + " herbs");
        }
        return new CanonHerbCadence(0, hand);
    }

    /** The seed (0 for authored hands). */
    public long seed() {
        return seed;
    }

    /** The hand. */
    public List<String> hand() {
        return hand;
    }

    private HerbChord.Result press(List<Integer> bundle) {
        List<Herb> herbs = new ArrayList<>();
        for (int i : bundle) {
            herbs.add(new Herb(hand.get(i), 1.0));
        }
        return HerbChord.sound(herbs);
    }

    /** Judge three bundles of hand indices, in playing order. */
    public Verdict judge(List<List<Integer>> bundles) {
        if (bundles == null || bundles.size() != 3) {
            return new Verdict(false, List.of(), "press exactly 3 bundles");
        }
        boolean[] used = new boolean[HAND];
        for (List<Integer> b : bundles) {
            if (b == null || b.size() != 3) {
                return new Verdict(false, List.of(), "each bundle needs 3 herbs");
            }
            for (int i : b) {
                if (i < 0 || i >= HAND || used[i]) {
                    return new Verdict(false, List.of(), "each herb goes in exactly one bundle");
                }
                used[i] = true;
            }
        }
        List<String> names = new ArrayList<>();
        HerbChord.Result prev = null;
        String reason = "cadence";
        for (int k = 0; k < 3; k++) {
            HerbChord.Result r = press(bundles.get(k));
            names.add(HerbChord.noteName(r.root()) + " " + r.quality());
            if (!reason.equals("cadence")) {
                continue;
            }
            if (!r.quality().equals("major") && !r.quality().equals("minor")) {
                reason = "bundle " + (k + 1) + " is " + r.quality() + ", not major or minor";
            } else if (prev != null && Math.floorMod(prev.root() - 7, 12) != r.root()) {
                reason = "bundle " + (k + 1) + " root " + HerbChord.noteName(r.root()) + " is not a fifth below "
                    + HerbChord.noteName(prev.root());
            }
            prev = r;
        }
        return new Verdict(reason.equals("cadence"), names, reason);
    }

    /** Every ordered bundling that makes a cadence (exhaustive). */
    public List<List<List<Integer>>> solutions() {
        List<List<List<Integer>>> out = new ArrayList<>();
        List<List<Integer>> triples = new ArrayList<>();
        for (int a = 0; a < HAND; a++) {
            for (int b = a + 1; b < HAND; b++) {
                for (int c = b + 1; c < HAND; c++) {
                    triples.add(List.of(a, b, c));
                }
            }
        }
        for (List<Integer> x : triples) {
            for (List<Integer> y : triples) {
                if (overlap(x, y)) {
                    continue;
                }
                List<Integer> z = new ArrayList<>();
                for (int i = 0; i < HAND; i++) {
                    if (!x.contains(i) && !y.contains(i)) {
                        z.add(i);
                    }
                }
                List<List<Integer>> cand = List.of(x, y, List.copyOf(z));
                if (judge(cand).cadence()) {
                    out.add(cand);
                }
            }
        }
        return out;
    }

    private static boolean overlap(List<Integer> x, List<Integer> y) {
        for (int i : x) {
            if (y.contains(i)) {
                return true;
            }
        }
        return false;
    }
}