// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.SpeciesResponse;
import com.daedalus.api.dto.SpeciesRow;
import com.daedalus.world.ecology.Guild;
import com.daedalus.world.ecology.Species;
import com.daedalus.world.ecology.SpeciesCanon;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** The species canon (ADR-021): every creature, plant and fungus the islands can hold. */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "Species", description = "The species canon the island ecology draws on")
public class SpeciesController {

    @GetMapping("/species")
    @Operation(summary = "List the species canon with each kind's guild, size and r/K strategy.")
    public ResponseEntity<SpeciesResponse> species() {
        SpeciesCanon canon = SpeciesCanon.get();
        Map<String, Integer> guilds = new LinkedHashMap<>();
        for (Guild g : Guild.values()) {
            guilds.put(g.name(), canon.guild(g).size());
        }
        List<SpeciesRow> rows = new ArrayList<>();
        for (Species s : canon.all()) {
            rows.add(new SpeciesRow(s.key(), s.name(), s.rarity(), s.temperament(), s.guild().name(),
                    s.size(), String.valueOf(s.strategy()), s.disperses()));
        }
        return ResponseEntity.ok(new SpeciesResponse(rows.size(), guilds, rows));
    }
}
