// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Door inspect — same facts automation reads. Place and lot are empty off a slab. */
public record DoorInspectResponse(
        String id, String worldId, int x, int y, int z, String state,
        String place, String lot, String acl) {

    public DoorInspectResponse {
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        acl = acl == null ? "" : acl;
    }

    public DoorInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot) {
        this(id, worldId, x, y, z, state, place, lot, "");
    }

    public DoorInspectResponse(String id, String worldId, int x, int y, int z, String state) {
        this(id, worldId, x, y, z, state, "", "", "");
    }
}
