// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Portal inspect — same facts automation reads. Place and lot are empty off a slab. */
public record PortalInspectResponse(
        String id, String worldId, int x, int y, int z, String state,
        String place, String lot) {

    public PortalInspectResponse {
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
    }

    public PortalInspectResponse(String id, String worldId, int x, int y, int z, String state) {
        this(id, worldId, x, y, z, state, "", "");
    }
}
