// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import java.util.EnumSet;
import java.util.Locale;
import java.util.Set;

/** Simulated win rate of one game on one difficulty, with its 95% Wilson interval and any balance flags. */
public final class ModeResult {

    private final String game;
    private final String difficulty;
    private final int trials;
    private final int wins;
    private final double meanScore;
    private final double low;
    private final double high;
    private final EnumSet<BalanceFlag> flags = EnumSet.noneOf(BalanceFlag.class);

    ModeResult(String game, String difficulty, int trials, int wins, double meanScore, double[] wilson) {
        this.game = game;
        this.difficulty = difficulty;
        this.trials = trials;
        this.wins = wins;
        this.meanScore = meanScore;
        this.low = wilson[0];
        this.high = wilson[1];
    }

    public String game() {
        return game;
    }

    public String difficulty() {
        return difficulty;
    }

    public int trials() {
        return trials;
    }

    public int wins() {
        return wins;
    }

    /** Point estimate; 0 for a mode the game does not ship. */
    public double winRate() {
        return trials == 0 ? 0 : (double) wins / trials;
    }

    public double meanScore() {
        return meanScore;
    }

    public double low() {
        return low;
    }

    public double high() {
        return high;
    }

    public Set<BalanceFlag> flags() {
        return EnumSet.copyOf(flags);
    }

    public boolean flagged() {
        return !flags.isEmpty();
    }

    void flag(BalanceFlag f) {
        flags.add(f);
    }

    @Override
    public String toString() {
        if (trials == 0) {
            return String.format(Locale.ROOT, "%s/%s: not in source %s", game, difficulty, flags);
        }
        return String.format(Locale.ROOT, "%s/%s: win %.1f%% [%.1f, %.1f] n=%d mean score %.1f %s", game, difficulty,
                100 * winRate(), 100 * low, 100 * high, trials, meanScore, flags);
    }
}
