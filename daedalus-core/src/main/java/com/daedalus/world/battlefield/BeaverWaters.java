// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.PriorityQueue;

/**
 * Beaver Waters (contest G34): ark beavers dam a spring stream on a floating island fragment, and the pond backs up
 * behind the dams. Pond cells turn into WETLAND on the {@link BattlefieldEcology} field (ADR-061 beaver ground: never
 * burns, grows willow), so a pond is a firebreak (FIRE01) and a willow nursery (ASH01).
 *
 * <p>The water is steady state and the spring never runs dry. Its water fills the basin it rises in up to the basin's
 * spill level (the lowest rim over which water can reach the island edge), pours over and runs downhill, fills every
 * basin on the way, and finally falls off the fragment edge into the sky. A dam raises one
 * cell by {@code damHeightCm} (dams stack), and building one fells {@code woodPerDam} pine or oak cells within
 * {@code woodReach}, the nearest first. A breach removes one layer again, and drained cells are left as wet meadow.
 *
 * <p>Win by putting the target plot under a pond without any water reaching the homestead plot. No randomness:
 * the heightmap, the spring and the dams decide everything.
 */
public final class BeaverWaters {

    public enum Outcome { DRY, WET, FLOODED }

    /** A rectangle of cells, inclusive. */
    public record Plot(int i0, int j0, int i1, int j1) {
        public Plot {
            if (i0 > i1 || j0 > j1) {
                throw new IllegalArgumentException("plot corners out of order");
            }
        }

        public boolean contains(int i, int j) { return i >= i0 && i <= i1 && j >= j0 && j <= j1; }

        public int cells() { return (i1 - i0 + 1) * (j1 - j0 + 1); }
    }

    /**
     * Tuning.
     *
     * @param dams         dam layers the colony can build in total
     * @param damHeightCm  height one layer adds to its cell
     * @param woodPerDam   pine/oak cells felled per layer
     * @param woodReach    trees are felled within this many cells of the dam (Chebyshev)
     * @param targetShare  WET when this share of the target plot is under water
     */
    public record Settings(int dams, int damHeightCm, int woodPerDam, int woodReach, double targetShare) {
        public static final Settings DEFAULT = new Settings(8, 60, 1, 4, 0.75);

        public Settings {
            if (dams < 0 || damHeightCm < 1 || woodPerDam < 0 || woodReach < 0
                    || !(targetShare > 0 && targetShare <= 1)) {
                throw new IllegalArgumentException("bad BeaverWaters settings");
            }
        }
    }

    private final BattlefieldEcology field;
    private final Settings s;
    private final int w;
    private final int h;
    private final int[] ground;
    private final int[] dam;
    private final boolean[] wet;
    private final int[] depth;
    private final int spring;
    private final Plot home;
    private final Plot target;
    private int layers;
    private int felled;
    private int spillCm;

    private BeaverWaters(BattlefieldEcology field, int[] groundCm, int si, int sj, Plot home, Plot target,
            Settings s) {
        this.field = field;
        this.s = s;
        this.w = field.width();
        this.h = field.height();
        if (groundCm.length != w * h) {
            throw new IllegalArgumentException("heightmap must have width x height cells");
        }
        this.ground = groundCm.clone();
        this.dam = new int[w * h];
        this.wet = new boolean[w * h];
        this.depth = new int[w * h];
        this.spring = index(si, sj);
        this.home = inside(home);
        this.target = inside(target);
        if (home.contains(si, sj)) {
            throw new IllegalArgumentException("the spring cannot rise inside the homestead");
        }
        settle();
    }

    /**
     * A spring at cell (si, sj) on a fragment with this heightmap (cm, row-major, j * width + i). The pond is filled
     * at once and written into the field.
     */
    public static BeaverWaters spring(BattlefieldEcology field, int[] groundCm, int si, int sj, Plot homestead,
            Plot target, Settings settings) {
        if (field == null || groundCm == null || homestead == null || target == null || settings == null) {
            throw new IllegalArgumentException("field, heightmap, plots and settings are required");
        }
        return new BeaverWaters(field, groundCm, si, sj, homestead, target, settings);
    }

    // ---- the colony's moves -------------------------------------------------------------------------------------

    /**
     * Builds one dam layer at (i, j). Refused (false) with no layers left, on the spring, under a pond, inside the
     * homestead, or without enough pine/oak within reach. A stream cell can be dammed; a pond cell cannot.
     * On success the felled trees become meadow and the pond settles to the new spill level.
     */
    public boolean dam(int i, int j) {
        int k = index(i, j);
        if (layers >= s.dams() || k == spring || depth[k] > 0 || home.contains(i, j)) {
            return false;
        }
        List<Integer> trees = treesNear(i, j);
        if (trees.size() < s.woodPerDam()) {
            return false;
        }
        for (int t = 0; t < s.woodPerDam(); t++) {
            int tk = trees.get(t);
            field.set(tk % w, tk / w, Vegetation.MEADOW);
            felled++;
        }
        layers++;
        dam[k] += s.damHeightCm();
        settle();
        return true;
    }

    /** Breaches one layer of the dam at (i, j). False when there is no dam there. The pond drains to the new level. */
    public boolean breach(int i, int j) {
        int k = index(i, j);
        if (dam[k] == 0) {
            return false;
        }
        dam[k] -= s.damHeightCm();
        layers--;
        settle();
        return true;
    }

    // ---- queries ------------------------------------------------------------------------------------------------

    /** True when water stands or runs on the cell (pond or stream). */
    public boolean water(int i, int j) { return wet[index(i, j)]; }
    /** True when the cell is under a pond (standing water deeper than 0). */
    public boolean pond(int i, int j) { return depth[index(i, j)] > 0; }
    public int damCm(int i, int j) { return dam[index(i, j)]; }
    public int surfaceCm(int i, int j) { return ground[index(i, j)] + dam[index(i, j)]; }
    /** Depth of water over the cell in cm, 0 when dry. */
    public int depthCm(int i, int j) {
        return depth[index(i, j)];
    }
    /** Water level at the spring in cm: the surface of the spring's pond, or the spring's ground with no pond. */
    public int spillCm() { return spillCm; }
    public int layersLeft() { return s.dams() - layers; }
    public int felled() { return felled; }

    /** Cells under standing water. */
    public int pondCells() {
        int n = 0;
        for (int d : depth) {
            n += d > 0 ? 1 : 0;
        }
        return n;
    }

    /** Cells with water on them, ponds and streams. */
    public int wetCells() {
        int n = 0;
        for (boolean b : wet) {
            n += b ? 1 : 0;
        }
        return n;
    }

    /** Share of the target plot under a pond (a stream running through does not count). */
    public double targetWet() {
        int n = 0;
        for (int j = target.j0(); j <= target.j1(); j++) {
            for (int i = target.i0(); i <= target.i1(); i++) {
                n += depth[j * w + i] > 0 ? 1 : 0;
            }
        }
        return (double) n / target.cells();
    }

    public boolean homeFlooded() {
        for (int j = home.j0(); j <= home.j1(); j++) {
            for (int i = home.i0(); i <= home.i1(); i++) {
                if (wet[j * w + i]) {
                    return true;
                }
            }
        }
        return false;
    }

    public Outcome outcome() {
        if (homeFlooded()) {
            return Outcome.FLOODED;
        }
        return targetWet() >= s.targetShare() ? Outcome.WET : Outcome.DRY;
    }

    // ---- internals ----------------------------------------------------------------------------------------------

    /**
     * Settles the water and writes it into the field. First the filled surface: for every cell, the lowest level at
     * which its water could reach the island edge (priority flood from the edge, minimax over paths). Cells whose
     * filled surface is above the ground are basins. Then the spring's water is traced: it fills the basin it is in,
     * pours over the basin's outlet and runs downhill, filling every basin on its way, until it falls off the edge.
     * Wet cells become WETLAND; cells that dried out are left as wet meadow.
     */
    private void settle() {
        int[] surface = new int[w * h];
        for (int k = 0; k < surface.length; k++) {
            surface[k] = ground[k] + dam[k];
        }
        int[] filled = fill(surface);
        spillCm = filled[spring];
        boolean[] next = new boolean[w * h];
        ArrayDeque<Integer> q = new ArrayDeque<>();
        next[spring] = true;
        q.add(spring);
        while (!q.isEmpty()) {
            int k = q.poll();
            int i = k % w;
            int j = k / w;
            boolean edge = i == 0 || j == 0 || i == w - 1 || j == h - 1;
            int lowest = -1;
            for (int nb : neighbours(k)) {
                if (filled[nb] == filled[k] && (filled[nb] > surface[nb] || filled[k] > surface[k])) {
                    add(next, q, nb);   // the same lake, or its rim cell, at one level
                } else if (filled[nb] < filled[k] && (lowest < 0 || filled[nb] < filled[lowest])) {
                    lowest = nb;
                }
            }
            if (edge) {
                continue;   // pours off the fragment
            }
            if (lowest >= 0) {
                add(next, q, lowest);
            } else {
                for (int nb : neighbours(k)) {
                    if (filled[nb] == filled[k]) {
                        add(next, q, nb);   // a flat run of dry ground: the stream spreads across it
                    }
                }
            }
        }
        for (int k = 0; k < next.length; k++) {
            depth[k] = next[k] ? filled[k] - surface[k] : 0;
            if (next[k] && !wet[k]) {
                field.set(k % w, k / w, Vegetation.WETLAND);
            } else if (!next[k] && wet[k]) {
                field.set(k % w, k / w, Vegetation.MEADOW);
            }
        }
        System.arraycopy(next, 0, wet, 0, next.length);
    }

    private static void add(boolean[] seen, ArrayDeque<Integer> q, int k) {
        if (!seen[k]) {
            seen[k] = true;
            q.add(k);
        }
    }

    /** Priority flood from the island edge: the filled (spill) surface of every cell. */
    private int[] fill(int[] surface) {
        int[] filled = new int[w * h];
        Arrays.fill(filled, Integer.MAX_VALUE);
        PriorityQueue<int[]> pq =
                new PriorityQueue<>(Comparator.<int[]>comparingInt(a -> a[0]).thenComparingInt(a -> a[1]));
        for (int k = 0; k < filled.length; k++) {
            int i = k % w;
            int j = k / w;
            if (i == 0 || j == 0 || i == w - 1 || j == h - 1) {
                filled[k] = surface[k];
                pq.add(new int[] {filled[k], k});
            }
        }
        while (!pq.isEmpty()) {
            int[] top = pq.poll();
            int k = top[1];
            if (top[0] > filled[k]) {
                continue;
            }
            for (int nb : neighbours(k)) {
                int level = Math.max(filled[k], surface[nb]);
                if (level < filled[nb]) {
                    filled[nb] = level;
                    pq.add(new int[] {level, nb});
                }
            }
        }
        return filled;
    }

    private List<Integer> neighbours(int k) {
        int i = k % w;
        int j = k / w;
        List<Integer> out = new ArrayList<>(4);
        if (i > 0) {
            out.add(k - 1);
        }
        if (i < w - 1) {
            out.add(k + 1);
        }
        if (j > 0) {
            out.add(k - w);
        }
        if (j < h - 1) {
            out.add(k + w);
        }
        return out;
    }

    private List<Integer> treesNear(int ci, int cj) {
        List<Integer> trees = new ArrayList<>();
        int r = s.woodReach();
        for (int j = Math.max(0, cj - r); j <= Math.min(h - 1, cj + r); j++) {
            for (int i = Math.max(0, ci - r); i <= Math.min(w - 1, ci + r); i++) {
                Vegetation v = field.vegetation(i, j);
                if ((v == Vegetation.PINE || v == Vegetation.OAK) && !wet[j * w + i]) {
                    trees.add(j * w + i);
                }
            }
        }
        trees.sort(Comparator.<Integer>comparingInt(k -> Math.max(Math.abs(k % w - ci), Math.abs(k / w - cj)))
                .thenComparingInt(k -> k));
        return trees;
    }

    private Plot inside(Plot p) {
        if (p.i0() < 0 || p.j0() < 0 || p.i1() >= w || p.j1() >= h) {
            throw new IllegalArgumentException("plot outside the field");
        }
        return p;
    }

    private int index(int i, int j) {
        if (i < 0 || j < 0 || i >= w || j >= h) {
            throw new IndexOutOfBoundsException("cell " + i + "," + j + " outside " + w + "x" + h);
        }
        return j * w + i;
    }
}
