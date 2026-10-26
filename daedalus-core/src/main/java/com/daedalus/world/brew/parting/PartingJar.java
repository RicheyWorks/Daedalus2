// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.parting;

import com.daedalus.world.brew.cellar.Preserve;

/** A family's parting order: {@code jars} of their favourite, kept by {@code method}, ready by day {@code due}. */
public record PartingJar(String family, String food, Preserve.Method method, int jars, int prepDays, int due) {
    public PartingJar {
        if (prepDays < 1 || jars < 1) {
            throw new IllegalArgumentException("a jar takes at least a day: " + family);
        }
    }
}
