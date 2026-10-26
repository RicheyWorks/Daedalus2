// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * One plot of a Parcels world (ADR-033): plot {@code n} (row × 8 + column) covers x {@code minX..maxX},
 * z {@code minZ..maxZ}, from the ground to {@code height}. {@code show} is what the district opened with
 * there (LAWN, GROVE, PAVILION, TOWER, SCULPTURE, POND). {@code owner} is empty while the plot is unclaimed,
 * and nobody may build on an unclaimed plot. {@code builders} are the people the owner lets build.
 */
public record PlotRow(int n, int minX, int minZ, int maxX, int maxZ, int height, String show, String owner,
                      List<String> builders) {

    /** Copy on construct: the caller's list cannot change what this record says. */
    public PlotRow {
        owner = owner == null ? "" : owner;
        builders = builders == null ? List.of() : List.copyOf(builders);
    }
}
