// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/** Every frame on a wall in a Gallery City, the galleries' own first (ADR-035). */
public record ArtListResponse(String worldId, List<ArtRow> art) {

    public ArtListResponse {
        art = art == null ? List.of() : List.copyOf(art);
    }
}
