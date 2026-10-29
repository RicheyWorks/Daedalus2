// SPDX-License-Identifier: MIT

/**
 * Studio horse lane minigames.
 *
 * <p>G506 {@link com.daedalus.world.stable.TrottingRing} (quest {@code q_blue_rosette}): the judge
 * calls walk, trot or canter for each ring segment; the rider picks a gait per segment, scoring 2
 * for a match, 1 for one step off and 0 otherwise, while trot costs 1 stamina, canter 2 and walk
 * restores 1. The rosette goes to a round that equals the dynamic-programming optimum; the eager
 * "always obey the judge" habit tires the horse before the last canter. Deterministic from a seed,
 * source only, no Unreal or Blender dependency.
 */
package com.daedalus.world.stable;
