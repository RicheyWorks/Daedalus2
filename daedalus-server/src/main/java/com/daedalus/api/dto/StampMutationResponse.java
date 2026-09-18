// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Outcome of {@code stamp.apply}. Overlap is a named result, not a merge.
 * {@code box} is empty until a slab is applied.
 */
public record StampMutationResponse(boolean ok, String result, String parcelId, long revision,
                                   int minX, int maxX, int minZ, int maxZ, String box) {

    public StampMutationResponse {
        box = box == null ? "" : box;
    }

    public StampMutationResponse(boolean ok, String result, String parcelId, long revision,
                                 int minX, int maxX, int minZ, int maxZ) {
        this(ok, result, parcelId, revision, minX, maxX, minZ, maxZ, "");
    }
}
