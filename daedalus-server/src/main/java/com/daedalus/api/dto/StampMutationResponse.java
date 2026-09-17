// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Outcome of {@code stamp.apply}. Overlap is a named result, not a merge.
 */
public record StampMutationResponse(boolean ok, String result, String parcelId, long revision,
                                   int minX, int maxX, int minZ, int maxZ) {
}
