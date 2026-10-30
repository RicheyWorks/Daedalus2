// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * A Bricks world's playground (ADR-034). Avatars appear on the cube {@code spawnX, spawnY, spawnZ}. The obby
 * runs through {@code platforms} in order, over lava whose top is at {@code lavaY}: touching it sends an
 * avatar back to the last checkpoint it stood on. Standing on {@code finish} completes the run. Building is
 * free on the open plate up to {@code height}; the plane rests at {@code hangarX, hangarY, hangarZ}.
 */
public record ObbyResponse(String worldId, int spawnX, int spawnY, int spawnZ, int lavaY, int height,
                           int hangarX, int hangarY, int hangarZ, List<Platform> platforms, Platform finish) {

    /** One brick of the run: its footprint, the y of its top, its colour, and whether it is a checkpoint. */
    public record Platform(int n, int minX, int minZ, int maxX, int maxZ, int y, String type, boolean checkpoint) {
    }

    /** Copy on construct: the caller's list cannot change what this record says. */
    public ObbyResponse {
        platforms = platforms == null ? List.of() : List.copyOf(platforms);
    }
}
