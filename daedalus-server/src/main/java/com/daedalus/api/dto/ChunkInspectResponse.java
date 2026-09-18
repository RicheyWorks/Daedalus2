// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Chunk inspect. A missing chunk is AIR everywhere — {@code present} is false.
 * Street fields name plots whose AABB overlaps this 16³, not the whole world.
 */
public record ChunkInspectResponse(
        int x, int y, int z, boolean present, Long revision, int occupied,
        int plots, String street, String lot, String occupants) {

    public ChunkInspectResponse {
        street = street == null ? "" : street;
        lot = lot == null ? "" : lot;
        occupants = occupants == null ? "" : occupants;
        if (plots < 0) {
            throw new IllegalArgumentException("plots must be at least 0");
        }
    }

    public ChunkInspectResponse(int x, int y, int z, boolean present, Long revision, int occupied) {
        this(x, y, z, present, revision, occupied, 0, "", "", "");
    }
}
