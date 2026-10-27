// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import com.daedalus.world.odds.OddsRng;
import java.util.List;

/**
 * One minigame plugged into the balance simulator. An adapter mirrors the game's real rules and difficulty constants and
 * plays one seeded session with a stated player model; it never changes the game itself.
 */
public interface BalanceGame {

    /** Stable id, e.g. {@code shardring}. */
    String id();

    /** Difficulty names in intended order, softest first. A name the game does not ship is reported, not simulated. */
    List<String> difficulties();

    /** True if the game's source ships this difficulty. */
    boolean supports(String difficulty);

    /** Plays one seeded session and returns its outcome. */
    SessionOutcome play(String difficulty, OddsRng rng);
}
