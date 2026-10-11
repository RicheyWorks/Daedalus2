// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * Every ark in a world, in home-slot order, and the server clock {@code now} (epoch ms) the voyage
 * times are measured against — a client keeps the offset so its animation runs on server time.
 */
public record WorldArksResponse(String worldId, long now, List<ArkRow> arks) {

    /** Copy on construct: the caller's list cannot change what this record says. */
    public WorldArksResponse {
        arks = arks == null ? List.of() : List.copyOf(arks);
    }
}
