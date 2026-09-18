// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * World-level inspect. Not a maze snapshot — no tiles, no Caffeine id.
 * Street fields are empty strings when the world has no plots.
 */
public record WorldInspectResponse(
        String id,
        long revision,
        int chunkCount,
        int plots,
        String street,
        String lot,
        String maze,
        String lease,
        String place) {

    public WorldInspectResponse {
        street = street == null ? "" : street;
        lot = lot == null ? "" : lot;
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
        place = place == null ? "" : place;
        if (plots < 0) {
            throw new IllegalArgumentException("plots must be at least 0");
        }
    }
}
