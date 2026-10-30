// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Meteor Scar Dig (contest gap G132): mine starmetal and emberite on the hot scar (ISLAND.md beat 6, "Mine Meteor Scar
 * (starmetal + emberite), rivet at the drydock"). The scar is a seeded {@value #SIZE} x {@value #SIZE} grid. Its veins
 * glow (Prop_Asteroid_Core has emissive veins), so the miner can see every cell. The skill is in spending water well.
 *
 * <p>Every swing costs {@value #THIRST_PER_SWING} water, because the caldera doubles thirst. A cell breaks after its
 * hardness in strikes: slag 1, rock 2, emberite 3, starmetal 4. Breaking a steam vent scalds for another
 * {@value #VENT_SCALD}. A canteen restores {@value #CANTEEN} water (thirst_restore_25, the island's dual tonics). If
 * the water runs out the miner faints on the scar and drops half the haul. Two dual tonics from the cookbook help:
 * Scar Prospector adds {@value #PROSPECTOR_LUCK_PCT}% ore luck to the haul, and Drydock Shift's harder swing strikes
 * twice. Two ore smelt to one {@code starmetal_ingot} (items.json); emberite goes to the drydock as is.
 *
 * <p>Pure and deterministic: {@link #plan} lays the same scar for the same seed, and {@link #run} gives the same
 * {@link Result} for the same kit and actions.
 */
public final class ScarDig {

    public static final int SIZE = 8;
    public static final int START_WATER = 60;
    public static final int THIRST_PER_SWING = 2;
    public static final int VENT_SCALD = 10;
    public static final int CANTEEN = 25;
    public static final int MAX_CANTEENS = 3;
    public static final int PROSPECTOR_LUCK_PCT = 10;
    public static final int ORE_PER_INGOT = 2;

    /** What a scar cell is. */
    public enum Cell {
        ROCK(2), SLAG(1), EMBERITE(3), STARMETAL(4), VENT(1);

        private final int hardness;

        Cell(int hardness) {
            this.hardness = hardness;
        }

        /** Strikes to break it. */
        public int hardness() {
            return hardness;
        }
    }

    /** The seeded scar, row-major. */
    public record Plan(List<Cell> cells) {

        public Plan {
            cells = List.copyOf(cells);
            if (cells.size() != SIZE * SIZE) {
                throw new IllegalArgumentException("a scar has " + SIZE * SIZE + " cells, not " + cells.size());
            }
        }

        public Cell at(int x, int y) {
            return cells.get(y * SIZE + x);
        }
    }

    /** What the miner carries: tonics drunk before the dig and canteens in the pack. */
    public record Kit(boolean prospector, boolean drydockShift, int canteens) {

        public Kit {
            if (canteens < 0 || canteens > MAX_CANTEENS) {
                throw new IllegalArgumentException("canteens 0.." + MAX_CANTEENS + ", not " + canteens);
            }
        }

        /** Strikes one swing lands. */
        public int strike() {
            return drydockShift ? 2 : 1;
        }
    }

    /** One thing the miner does. */
    public record Action(boolean isDrink, int x, int y) {

        public static Action swing(int x, int y) {
            return new Action(false, x, y);
        }

        public static Action drink() {
            return new Action(true, -1, -1);
        }
    }

    /** What the dig brought home. */
    public record Result(int starmetal, int emberite, int slag, int broken, int swings, int wasted, int water,
                         boolean fainted, int ingots, String line) {

        /** One-line SCR 1 summary, the same text as a native port's Encode(). */
        public String encode() {
            return "SCR 1 star=" + starmetal + " ember=" + emberite + " slag=" + slag + " broken=" + broken + " swings="
                    + swings + " wasted=" + wasted + " water=" + water + " fainted=" + (fainted ? 1 : 0) + " ingots=" + ingots
                    + " | " + line;
        }
    }

    private ScarDig() {
    }

    /** The scar for {@code seed}: about 6% starmetal, 8% emberite, 16% slag, 6% vents, the rest rock. */
    public static Plan plan(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x5CA2L);
        List<Cell> cells = new ArrayList<>(SIZE * SIZE);
        for (int i = 0; i < SIZE * SIZE; i++) {
            int r = rng.nextInt(100);
            cells.add(r < 6 ? Cell.STARMETAL : r < 14 ? Cell.EMBERITE : r < 30 ? Cell.SLAG : r < 36 ? Cell.VENT : Cell.ROCK);
        }
        return new Plan(cells);
    }

    /** Play {@code actions} on the scar with {@code kit}. The dig stops when the miner faints. */
    public static Result run(Plan p, Kit kit, List<Action> actions) {
        int[] hits = new int[SIZE * SIZE];
        for (int i = 0; i < hits.length; i++) {
            hits[i] = p.cells().get(i).hardness();
        }
        int water = START_WATER;
        int canteens = kit.canteens();
        int star = 0;
        int ember = 0;
        int slag = 0;
        int broken = 0;
        int swings = 0;
        int wasted = 0;
        boolean fainted = false;
        for (Action a : actions) {
            if (a.isDrink()) {
                if (canteens > 0) {
                    canteens--;
                    water = Math.min(START_WATER, water + CANTEEN);
                } else {
                    wasted++;
                }
                continue;
            }
            swings++;
            water -= THIRST_PER_SWING;
            boolean inside = a.x() >= 0 && a.x() < SIZE && a.y() >= 0 && a.y() < SIZE;
            int i = a.y() * SIZE + a.x();
            if (!inside || hits[i] == 0) {
                wasted++;
            } else {
                hits[i] = Math.max(0, hits[i] - kit.strike());
                if (hits[i] == 0) {
                    broken++;
                    Cell c = p.cells().get(i);
                    star += c == Cell.STARMETAL ? 1 : 0;
                    ember += c == Cell.EMBERITE ? 1 : 0;
                    slag += c == Cell.SLAG ? 1 : 0;
                    water -= c == Cell.VENT ? VENT_SCALD : 0;
                }
            }
            if (water <= 0) {
                water = 0;
                fainted = true;
                break;
            }
        }
        if (kit.prospector()) {
            star = luck(star);
            ember = luck(ember);
        }
        if (fainted) {
            star /= 2;
            ember /= 2;
            slag /= 2;
        }
        int ingots = star / ORE_PER_INGOT;
        return new Result(star, ember, slag, broken, swings, wasted, water, fainted, ingots, line(fainted, ingots, star + ember));
    }

    /** Scar Prospector's ore luck: +10%, rounded up, so even one vein turns up a bonus piece. */
    static int luck(int ore) {
        return (ore * (100 + PROSPECTOR_LUCK_PCT) + 99) / 100;
    }

    /** The scar miner's dig: starmetal veins first, then emberite, row by row; never a vent; drink before running dry. */
    public static List<Action> prospector(Plan p, Kit kit) {
        List<Action> out = new ArrayList<>();
        int water = START_WATER;
        int canteens = kit.canteens();
        for (Cell want : new Cell[] {Cell.STARMETAL, Cell.EMBERITE}) {
            for (int i = 0; i < SIZE * SIZE; i++) {
                if (p.cells().get(i) != want) {
                    continue;
                }
                int need = (want.hardness() + kit.strike() - 1) / kit.strike();
                for (int s = 0; s < need; s++) {
                    if (water - THIRST_PER_SWING <= 0) {
                        if (canteens == 0) {
                            return out;
                        }
                        canteens--;
                        water = Math.min(START_WATER, water + CANTEEN);
                        out.add(Action.drink());
                    }
                    water -= THIRST_PER_SWING;
                    out.add(Action.swing(i % SIZE, i / SIZE));
                }
            }
        }
        return out;
    }

    /** Quartermaster Hesper Coalhand weighs the sack at the scar gate. */
    static String line(boolean fainted, int ingots, int ore) {
        if (fainted) {
            return "The scar took your water before your ore. Canteen first, pick second.";
        }
        if (ingots >= 3) {
            return "Starmetal enough for a plate. Weighed, logged, off to the drydock.";
        }
        if (ore > 0) {
            return "Some shine in the sack. Swing where the veins glow.";
        }
        return "Rock and slag. The veins glow; the rock doesn't.";
    }
}
