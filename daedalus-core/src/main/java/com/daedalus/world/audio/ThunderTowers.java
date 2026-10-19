// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Thunder Towers (contest G89): storm season on the shattered planet; the bell towers warn the arks.
 *
 * <p>The island is a {@link #GRID} x {@link #GRID} grid of {@link #CELL_M} m cells. Lightning strikes one
 * seeded cell; three seeded bell towers each hear the thunder after (distance between cell centres) /
 * {@link #SOUND_MPS} seconds, rounded to 0.1 s. From the three delays the player names the strike cell.
 * Seeds are built so exactly one cell matches all three delays; {@link #candidates()} checks every cell.
 */
public final class ThunderTowers {
    /** Grid size (cells per side). */
    public static final int GRID = 12;
    /** Cell size, metres. */
    public static final double CELL_M = 250.0;
    /** Speed of sound, m/s. (343 m/s = dry air at about 20 C; c = 331.3 + 0.606 T). */
    public static final double SOUND_MPS = 343.0;
    private static final long SALT = 0x5448_5431L; // "THT1"

    /** A grid cell. */
    public record Cell(int x, int y) {
        /** Validates. */
        public Cell {
            if (x < 0 || y < 0 || x >= GRID || y >= GRID) {
                throw new IllegalArgumentException("cell off the island: " + x + "," + y);
            }
        }
    }

    /** A judged guess: delay error per tower in tenths of a second. */
    public record Verdict(boolean correct, Cell strike, List<Integer> errorTenths) {
        /** Defensive copy. */
        public Verdict {
            errorTenths = List.copyOf(errorTenths);
        }
    }

    private final long seed;
    private final List<Cell> towers;
    private final Cell strike;

    private ThunderTowers(long seed, List<Cell> towers, Cell strike) {
        this.seed = seed;
        this.towers = List.copyOf(towers);
        this.strike = strike;
    }

    /** A seeded storm with a uniquely locatable strike. */
    public static ThunderTowers seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        List<Cell> towers = new ArrayList<>();
        while (towers.size() < 3) {
            Cell c = new Cell(pick(rng), pick(rng));
            if (!towers.contains(c)) {
                towers.add(c);
            }
        }
        while (true) {
            ThunderTowers t = new ThunderTowers(seed, towers, new Cell(pick(rng), pick(rng)));
            if (t.candidates().size() == 1) {
                return t;
            }
        }
    }

    private static int pick(Rng rng) {
        return (int) Long.remainderUnsigned(rng.nextLong(), GRID);
    }

    /** Thunder delay from {@code from} to {@code to}, in tenths of a second. */
    public static int delayTenths(Cell from, Cell to) {
        double d = Math.hypot(from.x() - to.x(), from.y() - to.y()) * CELL_M;
        return (int) Math.round(d / SOUND_MPS * 10);
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** The three towers. */
    public List<Cell> towers() {
        return towers;
    }

    /** What each tower heard, tenths of a second after the flash. */
    public List<Integer> heard() {
        return delaysFrom(strike);
    }

    private List<Integer> delaysFrom(Cell c) {
        List<Integer> out = new ArrayList<>();
        for (Cell t : towers) {
            out.add(delayTenths(c, t));
        }
        return out;
    }

    /** Every cell consistent with the heard delays. */
    public List<Cell> candidates() {
        List<Integer> h = heard();
        List<Cell> out = new ArrayList<>();
        for (int x = 0; x < GRID; x++) {
            for (int y = 0; y < GRID; y++) {
                Cell c = new Cell(x, y);
                if (delaysFrom(c).equals(h)) {
                    out.add(c);
                }
            }
        }
        return out;
    }

    /** Judge a guessed cell. */
    public Verdict judge(Cell guess) {
        List<Integer> h = heard();
        List<Integer> g = delaysFrom(guess);
        List<Integer> err = new ArrayList<>();
        for (int i = 0; i < h.size(); i++) {
            err.add(g.get(i) - h.get(i));
        }
        return new Verdict(guess.equals(strike), strike, err);
    }
}
