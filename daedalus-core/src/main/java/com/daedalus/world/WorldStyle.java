// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * How a world looks and is generated (ADR-029, ADR-030). Storage is the same for every style —
 * chunked cubes, parcels, frames — so portals, claims, deeds and mazes work in all of them. A style
 * is {@link #ready} once its generator and renderer have shipped; the others are named now so the
 * registry, the API and the chain agree on them from the start.
 */
public enum WorldStyle {
    /** Minecraft / The Sandbox: seeded floating islands and arks (ADR-018..028). */
    SKY_ISLANDS(true, "Sky Islands"),
    /** Decentraland: a flat district of square plots with streets and a plaza (ADR-033). */
    PARCELS(true, "Parcels"),
    /** Roblox: a studded baseplate, a spawn, an obby over lava, blocky avatars (ADR-034). */
    BRICKS(true, "Bricks"),
    /** Cryptovoxels: a street-grid city of parcels with height limits, and galleries of maze art (ADR-035). */
    GALLERY(true, "Gallery City"),
    /** Daedalus itself: World One mazes at walking scale. */
    LABYRINTH(false, "Labyrinth");

    private final boolean ready;
    private final String title;

    WorldStyle(boolean ready, String title) {
        this.ready = ready;
        this.title = title;
    }

    public boolean ready() {
        return ready;
    }

    public String title() {
        return title;
    }
}
