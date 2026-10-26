// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Herb Chord Garden: an island planting puzzle on top of the HRB herb-chord system ({@link HerbChord}).
 *
 * <p>A seeded hand of nine blooming herbs goes into a 3x3 bed. Every line of three (3 rows, 3 columns,
 * 2 diagonals) sounds as a chord when the wind passes, and each chord grants its effect (major = HEAL,
 * minor = CALM, sus = FOCUS, fifth/unison = STEADY...). A villager's commission asks for one effect;
 * the bed fills the commission when as many lines as possible sound it. The target is the true best for
 * that hand, found by an exhaustive solver over all 9! plantings, so every commission is solvable and
 * a perfect bed is provable.
 *
 * <p>Ear rules: line chords play an octave below HerbChord's frequencies (so the bed hums around
 * 130-250 Hz), at gain 0.3 per line, rolled across the bed one line at a time.
 */
public final class HerbChordGarden {
    /** Herbs that grow on the islands (pitch classes come from {@link Herb#pitchClass()}). */
    public static final List<String> CATALOG = List.of("mint", "yarrow", "sage", "thyme", "basil", "rosemary",
            "lavender", "chamomile", "fennel", "dill", "tarragon", "sorrel", "lovage", "borage", "comfrey",
            "valerian", "lemonbalm", "hyssop", "marjoram", "chervil");
    /** Effects a commission may ask for (consonant chords only). */
    public static final List<HerbChord.Effect> COMMISSIONS = List.of(HerbChord.Effect.HEAL, HerbChord.Effect.CALM,
            HerbChord.Effect.FOCUS, HerbChord.Effect.STEADY);
    /** Line playback gain (ear rule). */
    public static final double LINE_GAIN = 0.3;
    /** The 8 lines of a 3x3 bed, as cell indices (row-major). */
    private static final int[][] LINES = {{0, 1, 2}, {3, 4, 5}, {6, 7, 8}, {0, 3, 6}, {1, 4, 7}, {2, 5, 8},
        {0, 4, 8}, {2, 4, 6}};
    private static final long SALT = 0x4847_4431L; // "HGD1"

    /** One line's chord. */
    public record Line(int index, HerbChord.Result chord, boolean fills, List<Double> playHz) {
        /** Defensive copy. */
        public Line {
            playHz = List.copyOf(playHz);
        }
    }

    /** A judged planting. */
    public record Verdict(boolean perfect, int lines, int target, List<Line> detail) {
        /** Defensive copy. */
        public Verdict {
            detail = List.copyOf(detail);
        }
    }

    private final long seed;
    private final List<Herb> hand;
    private final HerbChord.Effect wanted;
    private final boolean[] tripleFills = new boolean[512];
    private final int target;
    private final int[] best;

    private HerbChordGarden(long seed, List<Herb> hand, HerbChord.Effect wanted) {
        this.seed = seed;
        this.hand = List.copyOf(hand);
        this.wanted = wanted;
        for (int a = 0; a < 9; a++) {
            for (int b = a + 1; b < 9; b++) {
                for (int c = b + 1; c < 9; c++) {
                    boolean f = HerbChord.sound(List.of(hand.get(a), hand.get(b), hand.get(c))).effect() == wanted;
                    tripleFills[(1 << a) | (1 << b) | (1 << c)] = f;
                }
            }
        }
        int[] perm = {0, 1, 2, 3, 4, 5, 6, 7, 8};
        int[] bestPerm = perm.clone();
        int bestCount = -1;
        do {
            int n = count(perm);
            if (n > bestCount) {
                bestCount = n;
                bestPerm = perm.clone();
            }
        } while (nextPermutation(perm));
        this.target = bestCount;
        this.best = bestPerm;
    }

    /**
     * Seeded commission: nine distinct herbs from the catalog and one wanted effect. Hands whose best bed fills
     * fewer than 2 lines are redrawn (deterministically) so every commission is worth planting.
     */
    public static HerbChordGarden seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        HerbChordGarden g = null;
        for (int attempt = 0; attempt < 64 && (g == null || g.target < 2); attempt++) {
            List<String> pool = new ArrayList<>(CATALOG);
            List<Herb> hand = new ArrayList<>();
            for (int i = 0; i < 9; i++) {
                hand.add(new Herb(pool.remove((int) Long.remainderUnsigned(rng.nextLong(), pool.size())), 1.0));
            }
            HerbChord.Effect e = COMMISSIONS.get((int) Long.remainderUnsigned(rng.nextLong(), COMMISSIONS.size()));
            g = new HerbChordGarden(seed, hand, e);
        }
        return g;
    }

    /** Number of lines in a bed (3 rows, 3 columns, 2 diagonals). */
    public static int lineCount() {
        return LINES.length;
    }

    /** Cells (row-major indices) of line {@code i}. */
    public static int[] line(int i) {
        return LINES[i].clone();
    }

    /** The nine herbs, hand order. */
    public List<Herb> hand() {
        return hand;
    }

    /** The effect the commission asks for. */
    public HerbChord.Effect wanted() {
        return wanted;
    }

    /** Most lines any planting of this hand can fill (proved by the exhaustive solver). */
    public int target() {
        return target;
    }

    /** One perfect planting (cell -> hand index), for hints. */
    public int[] solution() {
        return best.clone();
    }

    /** The seed this commission came from. */
    public long seed() {
        return seed;
    }

    /** Judges a planting: bed[cell] = hand index, a permutation of 0..8. */
    public Verdict judge(int[] bed) {
        checkBed(bed);
        List<Line> detail = new ArrayList<>();
        int n = 0;
        for (int i = 0; i < LINES.length; i++) {
            List<Herb> herbs = List.of(hand.get(bed[LINES[i][0]]), hand.get(bed[LINES[i][1]]), hand.get(bed[LINES[i][2]]));
            HerbChord.Result r = HerbChord.sound(herbs);
            boolean fills = r.effect() == wanted;
            if (fills) {
                n++;
            }
            List<Double> hz = new ArrayList<>();
            for (double f : r.frequencies()) {
                hz.add(Math.round(f / 2 * 1000.0) / 1000.0);
            }
            detail.add(new Line(i, r, fills, hz));
        }
        return new Verdict(n == target, n, target, detail);
    }

    private int count(int[] bed) {
        int n = 0;
        for (int[] l : LINES) {
            if (tripleFills[(1 << bed[l[0]]) | (1 << bed[l[1]]) | (1 << bed[l[2]])]) {
                n++;
            }
        }
        return n;
    }

    private static boolean nextPermutation(int[] a) {
        int i = a.length - 2;
        while (i >= 0 && a[i] >= a[i + 1]) {
            i--;
        }
        if (i < 0) {
            return false;
        }
        int j = a.length - 1;
        while (a[j] <= a[i]) {
            j--;
        }
        int t = a[i];
        a[i] = a[j];
        a[j] = t;
        for (int l = i + 1, r = a.length - 1; l < r; l++, r--) {
            t = a[l];
            a[l] = a[r];
            a[r] = t;
        }
        return true;
    }

    private static void checkBed(int[] bed) {
        if (bed == null || bed.length != 9) {
            throw new IllegalArgumentException("a bed is 9 cells");
        }
        boolean[] seen = new boolean[9];
        for (int v : bed) {
            if (v < 0 || v > 8 || seen[v]) {
                throw new IllegalArgumentException("each herb planted once: " + Arrays.toString(bed));
            }
            seen[v] = true;
        }
    }
}
