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
 *
 * <p>G535 Farrier's Two Anvils ({@link FarriersTwoAnvils}, quest {@code q_two_anvils}): shoeing jobs with
 * must-finish-first links on two identical anvils, finish the last job earliest (P2|prec|Cmax); exact memoised event
 * search, which may idle an anvil on purpose, vs. Graham list scheduling in job order.
 *
 * <p>G537 Bridle Rack Matching ({@link BridleRackMatching}, quest {@code q_all_tacked}): give every horse its own
 * groom whose skill covers the horse's temperament so the last horse is ready earliest (bottleneck assignment with
 * compatibility); exact threshold search with augmenting paths vs. cheapest-pair-first, which strands or delays.
 *
 * <p>G539 Water Trough Fill ({@link WaterTroughFill}, quest {@code q_troughs_full}): pump the required buckets from
 * the well to the trough through pipes with capacities and per-bucket costs at least cost (min-cost flow); exact
 * successive shortest paths on the residual network vs. cheapest-path-without-undo, which runs dry or pays more.
 *
 * <p>G540 Lantern Posts ({@link LanternPosts}, quest {@code q_paths_lit}): light every path of the tree-shaped yard
 * with lanterns at junctions, each with its own price and lighting at most {@code reach} adjacent paths (capacitated
 * weighted vertex cover on a tree); exact tree DP vs. busiest-junction-per-coin, which pays more on most seeds.
 *
 * <p>G542 Hay Bale Stacking ({@link HayBaleStacking}, quest {@code q_tall_stack}): build the tallest stack of bales,
 * each strictly smaller on both footprint sides than the one below (turning allowed) and carrying at most its strength
 * (box stacking with load limits); exact DP over (bottom bale, stack weight) vs. biggest-first, usually shorter.
 *
 * <p>G545 Tack Ledger Index ({@link TackLedgerIndex}, quest {@code q_quick_ledger}): file the horses' ledger cards
 * as a binary search tree so lookups, weighted by how often each card is asked for, flip the fewest cards (optimal
 * binary search tree); exact Knuth interval DP vs. most-asked-card-at-the-root, which files lopsided ledgers.
 *
 * <p>G547 Stall Plaques ({@link StallPlaques}, quest {@code q_neat_plaques}): letter the stable roll onto fixed-width
 * plaque lines so the squared leftover space on every line but the last is least (Knuth-Plass-style word wrap); exact
 * DP over line starts vs. fill-each-line, which leaves short stub lines.
 *
 * <p>G548 Barn Upgrades ({@link BarnUpgrades}, quest {@code q_paying_barn}): choose stable upgrades, each earning or
 * costing coin, so every prerequisite is included and net coin is greatest (maximum-weight closure / project
 * selection); exact min cut vs. one-at-a-time, which skips groundwork that only pays when shared.
 */
package com.daedalus.world.stable;
