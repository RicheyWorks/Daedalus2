// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.futures;

/**
 * A storm-herb forward: deliver {@code bundles} bundles on {@code day} at {@code price}. A long (buy) forward gains when
 * spot settles above the price; a short (sell) forward gains when it settles below.
 */
public record Forward(int day, int bundles, double price, boolean longSide) {
    public Forward {
        if (day < 0 || bundles < 1 || !(price > 0)) {
            throw new IllegalArgumentException("day >= 0, bundles >= 1, price > 0 required");
        }
    }

    /** Profit at settlement spot {@code spot}. */
    public double payoff(double spot) {
        double perBundle = longSide ? spot - price : price - spot;
        return perBundle * bundles;
    }
}
