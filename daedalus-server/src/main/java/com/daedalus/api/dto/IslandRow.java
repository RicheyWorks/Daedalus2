// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * One raised island: its lane slot, world origin (the centre of its ground plane), seed, and the
 * traits derived from that seed. {@code top}/{@code bottom} are relative to {@code y}.
 */
public record IslandRow(int slot, int x, int y, int z, long seed, int radius, int columns,
                        int blocks, int trees, int blossomTrees, int pondColumns, int streamLength,
                        boolean waterfall, int crystals, int boulders, int top, int bottom) {
}
