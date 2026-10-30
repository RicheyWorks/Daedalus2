// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

/** Acceptable win-rate band [floor, ceiling] for one difficulty. */
public final class BalanceBand {

    private final double floor;
    private final double ceiling;

    public BalanceBand(double floor, double ceiling) {
        if (!(floor >= 0 && floor <= ceiling && ceiling <= 1)) {
            throw new IllegalArgumentException("band needs 0 <= floor <= ceiling <= 1: " + floor + ", " + ceiling);
        }
        this.floor = floor;
        this.ceiling = ceiling;
    }

    public double floor() {
        return floor;
    }

    public double ceiling() {
        return ceiling;
    }
}
