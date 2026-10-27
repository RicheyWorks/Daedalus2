// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.watch;

/** The hours a sailor offers to stay awake, from {@code start} up to (not including) {@code end}. */
public record Stretch(String sailor, int start, int end) {
    public Stretch {
        if (sailor == null || sailor.isBlank() || start < 0 || end <= start) {
            throw new IllegalArgumentException("bad stretch " + sailor);
        }
    }

    public boolean covers(int hour) {
        return hour >= start && hour < end;
    }
}
