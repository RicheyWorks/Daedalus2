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
 *
 * <p>G516 {@link com.daedalus.world.stable.FeedLoft} (quest {@code q_full_manger}): hay bales with weight,
 * bulk and nourishment go into a loft with a weight limit and a volume limit; the manger is full when
 * the load equals the exact two-constraint 0/1 optimum, while stacking by nourishment per weight
 * fills the loft with light, bulky bales.
 *
 * <p>G523 {@link com.daedalus.world.stable.PaddockRotation} (quest {@code q_green_pasture}): the herd grazes
 * one paddock a day; each paddock regrows while it rests, up to its cap. The pasture stays green when
 * the season plan equals the exact rest-counter optimum, while always grazing the fullest paddock
 * strips the lush paddocks before they refill.
 *
 * <p>G528 {@link com.daedalus.world.stable.ShoeingShed} (quest {@code q_sound_hooves}): one farrier shoes
 * the waiting horses in turn; each has a shoeing time, a fret weight and a show-ring call. The exact
 * subset DP minimizes total weighted lateness, while Smith's rule (fret per minute) ignores the calls
 * and leaves early-called horses waiting.
 *
 * <p>G530 Tack Room Pegs ({@link TackRoomPegs}, quest {@code q_tidy_tack_room}): hang every piece of tack on the
 * fewest pegs with a weight limit per peg and no two feuding horses' tack on one peg (bin packing with conflicts);
 * exact subset DP vs. first-fit, which a feud pushes to an extra peg.
 *
 * <p>G532 Hay Wagon Round ({@link HayWagonRound}, quest {@code q_hay_on_time}): feed every stall inside its feeding
 * window and get the hay wagon home earliest (travelling salesman with time windows, waiting allowed); exact
 * Held-Karp over (stalls fed, last stall) vs. nearest-open-stall, which a stall by the barn strands.
 */
package com.daedalus.world.stable;
