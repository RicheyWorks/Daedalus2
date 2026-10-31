// SPDX-License-Identifier: MIT

package com.daedalus.mazegame;

/**
 * Three original cabinet skins from the Prismheart looks table, as 0xRRGGBB ints so the rules
 * module stays free of AWT. Order: floor, wall, runner, exit, hint trail, fog.
 */
public enum Skin {
    LUMEN_SLATE("Lumen Slate", 0x1B2230, 0xC9D6E8, 0x7FE3FF, 0xFFD45E, 0x5FA8FF, 0x0B0E14),
    EMBER_FACET("Ember Facet", 0x2A1712, 0xF2B279, 0xFF6B3D, 0xFFF1A8, 0xE8834F, 0x120806),
    MOSS_GLASS("Moss Glass", 0x14241B, 0xA7D9B0, 0x8BFFB0, 0xF7E27A, 0x5FD08A, 0x07100B);

    private final String label;
    private final int floor;
    private final int wall;
    private final int runner;
    private final int exit;
    private final int hint;
    private final int fog;

    Skin(String label, int floor, int wall, int runner, int exit, int hint, int fog) {
        this.label = label;
        this.floor = floor;
        this.wall = wall;
        this.runner = runner;
        this.exit = exit;
        this.hint = hint;
        this.fog = fog;
    }

    public String label() { return label; }
    public int floor() { return floor; }
    public int wall() { return wall; }
    public int runner() { return runner; }
    public int exit() { return exit; }
    public int hint() { return hint; }
    public int fog() { return fog; }

    public Skin next() {
        Skin[] all = values();
        return all[(ordinal() + 1) % all.length];
    }
}
