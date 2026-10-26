// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.ledger;

/**
 * The Odds Keeper's staking rule: the Kelly fraction of a bankroll to stake on a wager with win chance {@code p} at
 * decimal odds {@code odds}, shaded by a multiplier (half Kelly by default) and capped so no single wager can sink the
 * ledger. Works for any Keeper board that quotes a chance and posted odds (G18 parlay, G35 cup, G47 routes).
 */
public final class KellyStake {

    /** The Keeper's default shading: half Kelly. */
    public static final double HALF = 0.5;
    /** Never advise more than this fraction of the bankroll on one wager. */
    public static final double CAP = 0.25;

    /** Guard against floating-point dust when flooring an exact stake (0.7999... x 20 must still be 4). */
    private static final double EPS = 1e-9;

    private KellyStake() {
    }

    /** Expected profit per herb staked: {@code p * odds - 1}. */
    public static double edge(double p, double odds) {
        check(p, odds);
        return p * odds - 1.0;
    }

    /** Full Kelly fraction {@code (b p - q) / b} with {@code b = odds - 1}; 0 when there is no edge. */
    public static double fraction(double p, double odds) {
        check(p, odds);
        if (odds <= 1.0) {
            return 0.0;
        }
        double b = odds - 1.0;
        return Math.max(0.0, (b * p - (1.0 - p)) / b);
    }

    /**
     * Herbs to stake from {@code bankroll}: floor(bankroll x min(cap, multiplier x Kelly)), at least 1 when there is
     * any edge and any bankroll, 0 when there is no edge.
     */
    public static int advise(int bankroll, double p, double odds, double multiplier, double cap) {
        if (bankroll < 0) {
            throw new IllegalArgumentException("bankroll must be >= 0: " + bankroll);
        }
        if (!(multiplier > 0) || !(cap > 0 && cap <= 1)) {
            throw new IllegalArgumentException("multiplier must be > 0 and cap in (0, 1]: " + multiplier + ", " + cap);
        }
        double f = Math.min(cap, multiplier * fraction(p, odds));
        if (f <= 0 || bankroll == 0) {
            return 0;
        }
        return Math.max(1, (int) Math.floor(bankroll * f + EPS));
    }

    /** Half-Kelly advice with the default cap. */
    public static int advise(int bankroll, double p, double odds) {
        return advise(bankroll, p, odds, HALF, CAP);
    }

    private static void check(double p, double odds) {
        if (!(p >= 0 && p <= 1)) {
            throw new IllegalArgumentException("p must be in [0, 1]: " + p);
        }
        if (!(odds >= 0) || Double.isInfinite(odds)) {
            throw new IllegalArgumentException("odds must be finite and >= 0: " + odds);
        }
    }
}
