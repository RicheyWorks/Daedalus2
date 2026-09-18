// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Read-back after a drive. Inspect: does not bump revision.
 * {@code place} and {@code lot} are empty off a slab.
 */
public record WorldObserveResponse(String worldId, long revision, int x, int y, int z,
                                   String blockType, String doorState, String place, String lot) {

    public WorldObserveResponse {
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
    }
}
