// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Outcome of {@code stamp.apply}. Overlap is a named result, not a merge.
 * {@code box} and {@code maze} are empty until a slab is applied.
 */
public record StampMutationResponse(boolean ok, String result, String parcelId, long revision,
                                   int minX, int maxX, int minZ, int maxZ, String box,
                                   String maze) {

    public StampMutationResponse {
        box = box == null ? "" : box;
        maze = maze == null ? "" : maze;
    }

    public StampMutationResponse(boolean ok, String result, String parcelId, long revision,
                                 int minX, int maxX, int minZ, int maxZ, String box) {
        this(ok, result, parcelId, revision, minX, maxX, minZ, maxZ, box, "");
    }

    public StampMutationResponse(boolean ok, String result, String parcelId, long revision,
                                 int minX, int maxX, int minZ, int maxZ) {
        this(ok, result, parcelId, revision, minX, maxX, minZ, maxZ, "", "");
    }
}
