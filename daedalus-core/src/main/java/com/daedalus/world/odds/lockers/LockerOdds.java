// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.lockers;

/**
 * Exact odds for the salvage lockers: the prize is in one of {@code lockers}; the player picks one, then {@code
 * opened} of the others are opened empty and a switch to one of the remaining closed lockers (chosen at random) is
 * offered. The Keeper knows and never opens the prize (Monty Hall, generalized); the blind deckhand opens at random
 * and can show the prize, which voids the round.
 */
public final class LockerOdds {

    public static final int MAX_LOCKERS = 50;

    private final int lockers;
    private final int opened;

    public LockerOdds(int lockers, int opened) {
        if (lockers < 3 || lockers > MAX_LOCKERS) {
            throw new IllegalArgumentException("lockers must be in [3, " + MAX_LOCKERS + "]: " + lockers);
        }
        if (opened < 1 || opened > lockers - 2) {
            throw new IllegalArgumentException("opened must be in [1, " + (lockers - 2) + "]: " + opened);
        }
        this.lockers = lockers;
        this.opened = opened;
    }

    public int lockers() {
        return lockers;
    }

    public int opened() {
        return opened;
    }

    /** Lockers still closed besides the player's pick. */
    public int othersClosed() {
        return lockers - opened - 1;
    }

    /** Keeper opened: staying wins 1/n. */
    public double stayKeeper() {
        return 1.0 / lockers;
    }

    /** Keeper opened: switching to a random other closed locker wins (n - 1) / (n (n - k - 1)). */
    public double switchKeeper() {
        return (lockers - 1.0) / (lockers * (double) othersClosed());
    }

    /** Blind deckhand: chance he opens no prize, (n - k) / n. */
    public double blindKeepsRound() {
        return (lockers - opened) / (double) lockers;
    }

    /** Blind deckhand, prize not shown: staying wins 1 / (n - k). */
    public double stayBlind() {
        return 1.0 / (lockers - opened);
    }

    /** Blind deckhand, prize not shown: switching wins 1 / (n - k), no better than staying. */
    public double switchBlind() {
        return 1.0 / (lockers - opened);
    }

    /** P(the Keeper opened | no prize shown) from a prior chance {@code keeperPrior} that it was the Keeper. */
    public double keeperPosterior(double keeperPrior) {
        if (!(keeperPrior >= 0 && keeperPrior <= 1)) {
            throw new IllegalArgumentException("keeperPrior must be in [0, 1]: " + keeperPrior);
        }
        double blind = (1.0 - keeperPrior) * blindKeepsRound();
        return keeperPrior / (keeperPrior + blind);
    }

    /** Switch chance when you were not told who opened (prior {@code keeperPrior}), given no prize shown. */
    public double switchUntold(double keeperPrior) {
        double post = keeperPosterior(keeperPrior);
        return post * switchKeeper() + (1.0 - post) * switchBlind();
    }

    /** Stay chance when you were not told who opened, given no prize shown. */
    public double stayUntold(double keeperPrior) {
        double post = keeperPosterior(keeperPrior);
        return post * stayKeeper() + (1.0 - post) * stayBlind();
    }
}
