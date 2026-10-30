// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/** Parcel inspect — same facts the well paints. */
public record WorldParcelsResponse(String worldId, List<WorldParcelRow> parcels) {

    /** Copy on construct: the caller's list cannot change what this record says. */
    public WorldParcelsResponse {
        parcels = parcels == null ? List.of() : List.copyOf(parcels);
    }
}
