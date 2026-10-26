// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * Keystone Shore (contest G108): the sea star that keeps the tide pools diverse (Paine's keystone predator).
 *
 * <p>A rocky shore is a {@code width}×{@code height} grid. Row 0 is the high shore and the last row is the low shore. Each
 * cell is bare rock or holds barnacles, mussels or kelp. Every year runs in this order:
 * <ul>
 *   <li><b>Settlement.</b> Larvae settle on bare rock in their zone: barnacles in the top half, mussels in the middle
 *       rows, kelp in the bottom half. Each has a chance per cell.</li>
 *   <li><b>Overgrowth.</b> Mussels are the dominant competitor. A mussel overgrows each orthogonal barnacle or kelp
 *       neighbour with chance {@code overgrow}.</li>
 *   <li><b>Predation.</b> Each sea star eats {@code starAppetite} mussel cells in the lower {@code starReach} share of
 *       the shore (the lowest rows first, since stars cannot hunt high and dry).</li>
 *   <li><b>Storms.</b> A seeded storm year clears a random patch of {@code stormPatch}×{@code stormPatch} cells.</li>
 * </ul>
 * Every draw is fixed by (seed, year, cell), so the plan never shifts the dice elsewhere.
 *
 * <p>The island takes sea stars as bait: {@code harvest(n)} removes n stars at the start, and the bait goal is
 * {@code baitGoal}. Outcomes at the end:
 * <ul>
 *   <li>DIVERSE: every species covers at least {@code minCover} of the shore and the bait goal is met.</li>
 *   <li>MUSSEL_BED: mussels cover at least {@code bedCover}.</li>
 *   <li>THIN: anything else.</li>
 * </ul>
 */
public final class KeystoneShore {

    /** What grows on a cell. */
    public enum Life { BARE, BARNACLE, MUSSEL, KELP }

    /** What the shore became. */
    public enum Outcome { DIVERSE, MUSSEL_BED, THIN }

    /**
     * Shore tuning.
     *
     * @param width        cells along the shore
     * @param height       rows from high to low shore
     * @param years        years to run
     * @param stars        sea stars on the shore at the start
     * @param starAppetite mussel cells one star clears a year
     * @param starReach    lower share of the rows the stars can hunt
     * @param settle       chance a bare cell in a species' zone is settled each year
     * @param overgrow     chance a mussel overgrows each barnacle or kelp neighbour a year
     * @param stormChance  chance a year has a storm
     * @param stormPatch   side of the square patch a storm clears
     * @param minCover     cover every species needs for a diverse shore
     * @param bedCover     mussel cover that makes a mussel bed
     * @param baitGoal     stars the island needs as bait
     */
    public record Settings(int width, int height, int years, int stars, int starAppetite, double starReach,
            double settle, double overgrow, double stormChance, int stormPatch, double minCover, double bedCover,
            int baitGoal) {

        /** The default shore. */
        public static final Settings DEFAULT = new Settings(16, 12, 30, 6, 6, 0.7, 0.3, 0.25, 0.3, 3, 0.06, 0.6, 2);

        /** Rejects a shore that cannot run. */
        public Settings {
            if (width < 1 || height < 3 || years < 1 || stars < 0 || starAppetite < 0
                    || !(starReach >= 0 && starReach <= 1) || !(settle >= 0 && settle <= 1)
                    || !(overgrow >= 0 && overgrow <= 1) || !(stormChance >= 0 && stormChance <= 1) || stormPatch < 0
                    || !(minCover >= 0 && minCover <= 1) || !(bedCover >= 0 && bedCover <= 1) || baitGoal < 0) {
                throw new IllegalArgumentException("bad keystone shore settings");
            }
        }
    }

    /** One year's cover. */
    public record Year(int index, boolean storm, int stars, double barnacle, double mussel, double kelp,
            int eaten) {}

    /** The result. */
    public record Report(Outcome outcome, Map<Life, Double> cover, int bait, List<Life> shore, List<Year> years) {

        /** Defensive copies. */
        public Report {
            cover = Map.copyOf(cover);
            shore = List.copyOf(shore);
            years = List.copyOf(years);
        }

        /** Species with at least {@code min} cover. */
        public int species(double min) {
            int n = 0;
            for (Life l : new Life[] {Life.BARNACLE, Life.MUSSEL, Life.KELP}) {
                if (cover.getOrDefault(l, 0.0) >= min) {
                    n++;
                }
            }
            return n;
        }

        /** The shore cell as a band on the ecology grid: kelp is WETLAND, anything else on the rock is BARE. */
        public Vegetation band(int index) {
            return shore.get(index) == Life.KELP ? Vegetation.WETLAND : Vegetation.BARE;
        }
    }

    private final Settings s;
    private final long seed;
    private int harvested;

    private KeystoneShore(Settings s, long seed) {
        this.s = s;
        this.seed = seed;
    }

    /** A seeded shore. */
    public static KeystoneShore shore(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new KeystoneShore(settings, seed);
    }

    /** Take {@code n} sea stars as bait before the run. False if there are not that many. */
    public boolean harvest(int n) {
        if (n < 1 || harvested + n > s.stars()) {
            return false;
        }
        harvested += n;
        return true;
    }

    /** Stars still on the shore. */
    public int starsLeft() {
        return s.stars() - harvested;
    }

    /** Whether a species can settle in this row. */
    public boolean zone(Life life, int row) {
        int h = s.height();
        return switch (life) {
            case BARNACLE -> row < h / 2;
            case MUSSEL -> row >= h / 3 && row < h - h / 4;
            case KELP -> row >= h / 2;
            case BARE -> true;
        };
    }

    /** Runs the shore. Deterministic in the settings, the seed and the plan. */
    public Report run() {
        int w = s.width();
        int h = s.height();
        int n = w * h;
        Life[] cell = new Life[n];
        java.util.Arrays.fill(cell, Life.BARE);
        int stars = s.stars() - harvested;
        int firstHunt = h - (int) Math.round(s.starReach() * h);
        List<Year> log = new ArrayList<>();
        Life[] order = {Life.MUSSEL, Life.BARNACLE, Life.KELP};
        for (int y = 0; y < s.years(); y++) {
            for (int i = 0; i < n; i++) {
                if (cell[i] != Life.BARE) {
                    continue;
                }
                int row = i / w;
                for (int k = 0; k < order.length; k++) {
                    if (zone(order[k], row) && roll(y, i, 1 + k) < s.settle()) {
                        cell[i] = order[k];
                        break;
                    }
                }
            }
            Life[] next = cell.clone();
            for (int i = 0; i < n; i++) {
                if (cell[i] != Life.MUSSEL) {
                    continue;
                }
                int x = i % w;
                int row = i / w;
                int[] nb = {x > 0 ? i - 1 : -1, x + 1 < w ? i + 1 : -1, row > 0 ? i - w : -1, row + 1 < h ? i + w : -1};
                for (int d = 0; d < nb.length; d++) {
                    int j = nb[d];
                    if (j >= 0 && (cell[j] == Life.BARNACLE || cell[j] == Life.KELP) && roll(y, i, 10 + d) < s.overgrow()) {
                        next[j] = Life.MUSSEL;
                    }
                }
            }
            cell = next;
            int eaten = 0;
            int budget = stars * s.starAppetite();
            for (int row = h - 1; row >= firstHunt && eaten < budget; row--) {
                for (int x = 0; x < w && eaten < budget; x++) {
                    int i = row * w + (int) ((x + (long) (roll(y, row, 20) * w)) % w);
                    if (cell[i] == Life.MUSSEL) {
                        cell[i] = Life.BARE;
                        eaten++;
                    }
                }
            }
            boolean storm = roll(y, -1, 30) < s.stormChance();
            if (storm && s.stormPatch() > 0) {
                int px = (int) (roll(y, -1, 31) * Math.max(1, w - s.stormPatch() + 1));
                int py = (int) (roll(y, -1, 32) * Math.max(1, h - s.stormPatch() + 1));
                for (int dy = 0; dy < s.stormPatch() && py + dy < h; dy++) {
                    for (int dx = 0; dx < s.stormPatch() && px + dx < w; dx++) {
                        cell[(py + dy) * w + px + dx] = Life.BARE;
                    }
                }
            }
            Map<Life, Double> c = cover(cell);
            log.add(new Year(y, storm, stars, c.get(Life.BARNACLE), c.get(Life.MUSSEL), c.get(Life.KELP), eaten));
        }
        Map<Life, Double> c = cover(cell);
        boolean diverse = c.get(Life.BARNACLE) >= s.minCover() && c.get(Life.MUSSEL) >= s.minCover()
                && c.get(Life.KELP) >= s.minCover();
        Outcome outcome = c.get(Life.MUSSEL) >= s.bedCover() ? Outcome.MUSSEL_BED
                : diverse && harvested >= s.baitGoal() ? Outcome.DIVERSE : Outcome.THIN;
        return new Report(outcome, c, harvested, List.of(cell), log);
    }

    private static Map<Life, Double> cover(Life[] cell) {
        Map<Life, Double> c = new EnumMap<>(Life.class);
        for (Life l : Life.values()) {
            c.put(l, 0.0);
        }
        for (Life l : cell) {
            c.merge(l, 1.0 / cell.length, Double::sum);
        }
        return c;
    }

    private double roll(int year, long key, int salt) {
        long z = seed + 0x9E3779B97F4A7C15L * (year + 1) + 0xBF58476D1CE4E5B9L * (key + 2) + 0x94D049BB133111EBL * salt;
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z = z ^ (z >>> 31);
        return (z >>> 11) * 0x1.0p-53;
    }
}
