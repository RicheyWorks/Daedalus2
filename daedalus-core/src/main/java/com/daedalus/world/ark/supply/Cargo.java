// SPDX-License-Identifier: MIT
package com.daedalus.world.ark.supply;

/**
 * What an ark carries between islands, with weight (kg) and hold volume (crate slots) per unit. Proposed values,
 * original to Daedalus.
 */
public enum Cargo {
    WATER_CASK(10, 1),
    FODDER_BALE(5, 2),
    SEED_CACHE(2, 1),
    SALVE_JAR(1, 1),
    TIMBER_BUNDLE(20, 4);

    private final int kg;
    private final int volume;

    Cargo(int kg, int volume) { this.kg = kg; this.volume = volume; }

    public int kg() { return kg; }

    public int volume() { return volume; }
}
