// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.boats;

/** One cargo crate and its weight in stone. */
public record Crate(String name, int weight) {
    public Crate {
        if (name == null || name.isBlank() || weight <= 0) {
            throw new IllegalArgumentException("bad crate " + name);
        }
    }
}
