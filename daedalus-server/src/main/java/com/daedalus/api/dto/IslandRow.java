// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * One raised island: its lane slot, world origin (the centre of its ground plane), seed, and the
 * traits derived from that seed. {@code top}/{@code bottom} are relative to {@code y};
 * {@code dockX,dockY,dockZ} is the pier tip in world coordinates (ADR-019). {@code owner} is who
 * claimed it, empty while it is open to everyone, and {@code builders} whom the owner lets build
 * (ADR-026).
 */
public record IslandRow(int slot, int x, int y, int z, long seed, int radius, int columns,
                        int blocks, int trees, int blossomTrees, int pondColumns, int streamLength,
                        boolean waterfall, int crystals, int boulders, int top, int bottom,
                        int dockX, int dockY, int dockZ, String owner, List<String> builders) {

    /** Copy on construct: the caller's list cannot change what this record says. */
    public IslandRow {
        owner = owner == null ? "" : owner;
        builders = builders == null ? List.of() : List.copyOf(builders);
    }
}
