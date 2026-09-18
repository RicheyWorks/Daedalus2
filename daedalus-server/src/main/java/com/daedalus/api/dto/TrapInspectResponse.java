// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Trap inspect — same facts automation reads. Place and lot are empty off a slab. */
public record TrapInspectResponse(
        String id, String worldId, int x, int y, int z, String state,
        String place, String lot, String acl) {

    public TrapInspectResponse {
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        acl = acl == null ? "" : acl;
    }

    public TrapInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot) {
        this(id, worldId, x, y, z, state, place, lot, "");
    }

    public TrapInspectResponse(String id, String worldId, int x, int y, int z, String state) {
        this(id, worldId, x, y, z, state, "", "", "");
    }
}
