// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.chests;

/** A keepsake a family could carry: its weight in the chest and how much it is remembered by. */
public record Keepsake(String id, int weight, int memory) {
    public Keepsake {
        if (id == null || id.isBlank() || weight <= 0 || memory < 0) {
            throw new IllegalArgumentException("bad keepsake " + id);
        }
    }
}
