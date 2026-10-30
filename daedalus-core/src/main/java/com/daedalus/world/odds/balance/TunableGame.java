// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import com.daedalus.world.odds.OddsRng;
import java.util.List;

/**
 * A minigame whose difficulty constants can be replayed at other values, for {@link BalanceTuner}. The adapter plays
 * the game's own rules with knob values it is handed; it never edits the game.
 */
public interface TunableGame {

    String id();

    /** Difficulty names, softest first. */
    List<String> difficulties();

    /** The knobs, in the order {@link #play} reads them. */
    List<Knob> knobs();

    /** Knob values the game's source ships for a difficulty, or null if the source has no such mode. */
    int[] shipped(String difficulty);

    /** Plays one seeded session with the given knob values. */
    SessionOutcome play(int[] knobs, OddsRng rng);
}
