// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/** Parcel inspect — same facts the well paints. */
public record WorldParcelsResponse(String worldId, List<WorldParcelRow> parcels) {
}
