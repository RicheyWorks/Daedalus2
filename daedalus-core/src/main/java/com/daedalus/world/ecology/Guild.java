// SPDX-License-Identifier: MIT

package com.daedalus.world.ecology;

/**
 * Where on a sky island a species can live (ADR-021). Each guild draws on a different part of an
 * island's terrain, so a reed-ringed pond and a crowded orchard support different communities.
 */
public enum Guild {
    /** Open grass and scrub: grazers, burrowers, pollinators, ground predators, wildflowers. */
    MEADOW,
    /** Trees: birds, climbers, gliders, tree snakes — and the trees themselves. */
    CANOPY,
    /** The pond and its stream: fish, amphibians, freshwater cells. */
    POND,
    /** Soil and deadwood: fungi, lichen, worms, the cleanup crew. */
    DECOMPOSER,
    /** Fell with the meteor. They live on the crystals under the islands. */
    STARBORN,
    /** Sea creatures. The sea fell away in the Shattering; no sky island holds them yet. */
    MARINE
}
