// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/** Every island raised in a world, in slot order. */
public record WorldIslandsResponse(String worldId, List<IslandRow> islands) {

    /** Copy on construct: the caller's list cannot change what this record says. */
    public WorldIslandsResponse {
        islands = islands == null ? List.of() : List.copyOf(islands);
    }
}
