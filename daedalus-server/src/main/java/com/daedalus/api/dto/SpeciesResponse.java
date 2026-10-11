// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;
import java.util.Map;

/** The species canon: every kind, in catalog order, and how many fall in each guild. */
public record SpeciesResponse(int count, Map<String, Integer> guilds, List<SpeciesRow> species) {

    /** Copy on construct: the caller's collections cannot change what this record says. */
    public SpeciesResponse {
        guilds = guilds == null ? Map.of() : Map.copyOf(guilds);
        species = species == null ? List.of() : List.copyOf(species);
    }
}
