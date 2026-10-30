// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;
import java.util.Map;

/**
 * One island's life (ADR-023): the ecological {@code day} it has been stepped to, how long a day
 * lasts in server ms, its habitat cells by guild and their sum ({@code area}), the CSRBT diversity
 * indices, and every kind living there, most numerous first.
 */
public record IslandEcologyResponse(String worldId, int slot, long day, long dayMs, double area,
                                    Map<String, Double> habitat, int richness, double total,
                                    double shannon, double evenness, double simpson,
                                    List<CargoRow> species) {

    /** Copy on construct: the caller's collections cannot change what this record says. */
    public IslandEcologyResponse {
        habitat = habitat == null ? Map.of() : Map.copyOf(habitat);
        species = species == null ? List.of() : List.copyOf(species);
    }
}
