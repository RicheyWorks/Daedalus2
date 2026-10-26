// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.ledger;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * One storm-herb bankroll shared by every Odds Keeper wager. A win pays floor(stake x odds) back (stake included); a
 * loss forfeits the stake. Tracks history, peak and worst drawdown. Herbs are in-game only.
 */
public final class HerbLedger {

    /** One settled wager. */
    public record Entry(String game, int stake, double odds, boolean won, int balanceAfter) {
        public Entry {
            Objects.requireNonNull(game, "game");
        }
    }

    private final int start;
    private final List<Entry> history = new ArrayList<>();
    private int balance;
    private int peak;
    private double maxDrawdown;

    public HerbLedger(int start) {
        if (start < 1) {
            throw new IllegalArgumentException("start must be >= 1: " + start);
        }
        this.start = start;
        this.balance = start;
        this.peak = start;
    }

    /**
     * Settles a wager from {@code game} and returns the new balance.
     *
     * @throws IllegalArgumentException if the stake is below 1 or above the balance, or odds are below evens
     */
    public int settle(String game, int stake, double odds, boolean won) {
        Objects.requireNonNull(game, "game");
        if (stake < 1 || stake > balance) {
            throw new IllegalArgumentException("stake must be in [1, " + balance + "]: " + stake);
        }
        if (!(odds >= 1.0) || Double.isInfinite(odds)) {
            throw new IllegalArgumentException("odds must be finite and >= 1: " + odds);
        }
        balance += won ? (int) Math.floor(stake * odds) - stake : -stake;
        peak = Math.max(peak, balance);
        maxDrawdown = Math.max(maxDrawdown, (peak - balance) / (double) peak);
        history.add(new Entry(game, stake, odds, won, balance));
        return balance;
    }

    public int start() {
        return start;
    }

    public int balance() {
        return balance;
    }

    public int peak() {
        return peak;
    }

    /** Worst fall from a running peak, as a fraction of that peak. */
    public double maxDrawdown() {
        return maxDrawdown;
    }

    public boolean broke() {
        return balance < 1;
    }

    /** Settled wagers, oldest first. */
    public List<Entry> history() {
        return List.copyOf(history);
    }

    public int wins() {
        return (int) history.stream().filter(Entry::won).count();
    }
}
