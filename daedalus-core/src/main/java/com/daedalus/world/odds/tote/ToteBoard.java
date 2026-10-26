// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.tote;

import java.util.Arrays;

/**
 * A pari-mutuel tote: every herb staked goes into one pool, the house keeps a {@code takeout}, and the rest is split
 * among the stakes on the winner. Decimal tote odds on outcome {@code i} are {@code pool x (1 - takeout) / stakeOn(i)}.
 * Unlike the Keeper's fixed boards, the price is set by the crowd and moves with every bet, including yours.
 */
public final class ToteBoard {

    /** Highest takeout the Keeper allows. */
    public static final double MAX_TAKEOUT = 0.25;

    private final long[] stakes;
    private final double takeout;

    public ToteBoard(int outcomes, double takeout) {
        if (outcomes < 2) {
            throw new IllegalArgumentException("need at least two outcomes: " + outcomes);
        }
        if (!(takeout >= 0 && takeout <= MAX_TAKEOUT)) {
            throw new IllegalArgumentException("takeout must be in [0, " + MAX_TAKEOUT + "]: " + takeout);
        }
        this.stakes = new long[outcomes];
        this.takeout = takeout;
    }

    public int size() {
        return stakes.length;
    }

    public double takeout() {
        return takeout;
    }

    /** Adds {@code herbs} to the stakes on outcome {@code i}. */
    public void bet(int i, long herbs) {
        if (herbs < 1) {
            throw new IllegalArgumentException("bet must be >= 1 herb: " + herbs);
        }
        stakes[i] += herbs;
    }

    public long pool() {
        return Arrays.stream(stakes).sum();
    }

    public long stakeOn(int i) {
        return stakes[i];
    }

    /** Current tote odds on outcome {@code i}; 0 when nothing is staked on it. */
    public double odds(int i) {
        return stakes[i] == 0 ? 0.0 : pool() * (1 - takeout) / stakes[i];
    }

    /** Tote odds on {@code i} after adding a further {@code stake} herbs to it (your own bet moves the price). */
    public double oddsAfter(int i, long stake) {
        if (stake < 0) {
            throw new IllegalArgumentException("stake must be >= 0: " + stake);
        }
        long on = stakes[i] + stake;
        return on == 0 ? 0.0 : (pool() + stake) * (1 - takeout) / on;
    }

    /**
     * Largest stake on {@code i} that still has positive edge for a bettor who believes the chance is {@code p}:
     * p (P + s)(1 - t) > S_i + s, i.e. s < (p (1 - t) P - S_i) / (1 - p (1 - t)). Returns 0 when there is no overlay.
     */
    public long maxOverlayStake(int i, double p) {
        if (!(p >= 0 && p <= 1)) {
            throw new IllegalArgumentException("p must be in [0, 1]: " + p);
        }
        double k = p * (1 - takeout);
        if (k >= 1) {
            return Long.MAX_VALUE;
        }
        double s = (k * pool() - stakes[i]) / (1 - k);
        if (s <= 0) {
            return 0;
        }
        long whole = (long) Math.ceil(s) - 1;
        return Math.max(0, whole);
    }

    /** Herbs returned to {@code stake} on the winner {@code winner} (floor of stake x final odds). */
    public long payout(int winner, long stake) {
        return (long) Math.floor(stake * odds(winner));
    }
}
