// SPDX-License-Identifier: MIT

package com.daedalus.world.odds;

/**
 * What an encounter is worth to the player, for the expected-value figure: a value per outcome, and a cost per point
 * of health lost. Units are the caller's (coins, reputation, anything); the engine only does the arithmetic.
 */
public record Payoffs(double win, double loss, double draw, double costPerHealth) {

    /** +1 for a win, -1 for a loss, nothing for a draw, health is free. */
    public static final Payoffs WIN_LOSE = new Payoffs(1, -1, 0, 0);

    public Payoffs {
        if (!Double.isFinite(win) || !Double.isFinite(loss) || !Double.isFinite(draw)
                || !Double.isFinite(costPerHealth) || costPerHealth < 0) {
            throw new IllegalArgumentException("payoffs must be finite and the health cost at least 0");
        }
    }

    double value(CombatOddsSimulator.Outcome outcome, double healthLost) {
        double base = switch (outcome) {
            case WIN -> win;
            case LOSS -> loss;
            case DRAW -> draw;
        };
        return base - costPerHealth * healthLost;
    }
}