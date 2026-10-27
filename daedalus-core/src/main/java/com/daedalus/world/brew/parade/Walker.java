// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.parade;

/** A child in the line and the height of their lantern pole. */
public record Walker(String name, int height) {
    public Walker {
        if (name == null || name.isBlank() || height <= 0) {
            throw new IllegalArgumentException("bad walker " + name);
        }
    }
}
