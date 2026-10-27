// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

/** Result of one simulated session: whether it counts as a win, and the game's own score. */
public final class SessionOutcome {

    private final boolean won;
    private final long score;

    public SessionOutcome(boolean won, long score) {
        this.won = won;
        this.score = score;
    }

    public boolean won() {
        return won;
    }

    public long score() {
        return score;
    }
}
