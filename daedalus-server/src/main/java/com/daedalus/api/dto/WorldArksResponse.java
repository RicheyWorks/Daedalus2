// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/** Every ark in a world, in home-slot order. */
public record WorldArksResponse(String worldId, List<ArkRow> arks) {

    /** Copy on construct: the caller's list cannot change what this record says. */
    public WorldArksResponse {
        arks = arks == null ? List.of() : List.copyOf(arks);
    }
}
