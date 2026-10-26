// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * A frame on a wall in a Gallery City (ADR-035). The wall cube at its lowest corner is {@code x, y, z}.
 * It spans {@code w} cubes along the wall and {@code h} up, on the face toward {@code facing} (NORTH,
 * SOUTH, EAST or WEST). It shows the maze art of {@code seed}, which is served at {@code image}.
 * {@code owner} is empty for the galleries' own art.
 */
public record ArtRow(String id, int x, int y, int z, String facing, int w, int h, long seed, String title,
                     String generator, String owner, String address, String image) {
}
