// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

/** One integer difficulty knob a tuner may move: values {@code min, min + step, ..., <= max}. */
public record Knob(String name, int min, int max, int step) {

    public Knob {
        if (name == null || name.isBlank() || step < 1 || max < min) {
            throw new IllegalArgumentException("knob needs a name, step >= 1 and max >= min: " + name);
        }
    }

    /** Number of grid values. */
    public int size() {
        return (max - min) / step + 1;
    }

    public int value(int index) {
        return min + index * step;
    }
}
