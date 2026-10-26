// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

/**
 * Vegetation state of one battlefield cell (ADR-061). The succession ladder runs BARE, MEADOW, SCRUB, PINE, OAK;
 * WETLAND sits beside it (beaver ground, never burns). Each state carries what a fight cares about.
 *
 * @param code          one-letter code used by the DBE 1 snapshot
 * @param cover         0..1, how much the cell stops shots (trunks, rock-hard stems)
 * @param concealment   0..1, how much it hides a unit from sight (canopy, tall grass)
 * @param flammability  0..1, chance per tick a burning neighbour ignites this cell
 * @param burnTicks     how long the cell burns once lit
 * @param yearsToNext   years of quiet growth to reach the next stage (0 = no further stage)
 */
public enum Vegetation {
    BARE('.', 0.00, 0.00, 0.00, 0, 1.0),
    MEADOW('m', 0.05, 0.35, 0.60, 1, 4.0),
    SCRUB('s', 0.25, 0.65, 0.45, 2, 15.0),
    PINE('p', 0.55, 0.70, 0.35, 4, 40.0),
    OAK('o', 0.80, 0.60, 0.12, 6, 0.0),
    WETLAND('w', 0.10, 0.40, 0.00, 0, 0.0);

    private final char code;
    private final double cover;
    private final double concealment;
    private final double flammability;
    private final int burnTicks;
    private final double yearsToNext;

    Vegetation(char code, double cover, double concealment, double flammability, int burnTicks, double yearsToNext) {
        this.code = code;
        this.cover = cover;
        this.concealment = concealment;
        this.flammability = flammability;
        this.burnTicks = burnTicks;
        this.yearsToNext = yearsToNext;
    }

    public char code() { return code; }
    public double cover() { return cover; }
    public double concealment() { return concealment; }
    public double flammability() { return flammability; }
    public int burnTicks() { return burnTicks; }
    public double yearsToNext() { return yearsToNext; }

    /** The next succession stage, or this one when it is terminal (OAK, WETLAND). */
    public Vegetation next() {
        return switch (this) {
            case BARE -> MEADOW;
            case MEADOW -> SCRUB;
            case SCRUB -> PINE;
            case PINE -> OAK;
            case OAK, WETLAND -> this;
        };
    }

    public static Vegetation ofCode(char c) {
        for (Vegetation v : values()) {
            if (v.code == c) {
                return v;
            }
        }
        throw new IllegalArgumentException("unknown vegetation code '" + c + "'");
    }
}
