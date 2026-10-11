// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

/**
 * What an island <em>is</em>, as numbers a client, a field report or a later token's metadata can
 * read without regenerating it. Every field is derived from the seed; none is chosen afterwards.
 *
 * @param columns     ground-plane footprint in cubes — the island's area
 * @param blocks      every non-air cube in the plan, water and clouds included
 * @param pondColumns columns the pond covers
 * @param streamLength stream columns carved from the pond to the rim
 * @param top         highest y in the plan, relative to the origin
 * @param bottom      lowest y in the plan, relative to the origin
 */
public record IslandTraits(
        long seed,
        int radius,
        int columns,
        int blocks,
        int trees,
        int blossomTrees,
        int pondColumns,
        int streamLength,
        boolean waterfall,
        int crystals,
        int boulders,
        int top,
        int bottom) {
}
