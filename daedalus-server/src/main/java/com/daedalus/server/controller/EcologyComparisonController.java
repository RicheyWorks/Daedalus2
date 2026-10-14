// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.IslandEcologyComparisonResponse;
import com.daedalus.server.service.WorldHub;
import com.daedalus.server.service.WorldService;
import com.daedalus.server.web.ResourceNotFoundException;
import com.daedalus.world.ecology.CommunityComparison;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Between-island ecology, using the same current-day snapshots as the existing Life route. */
@RestController
@RequestMapping("/api/v1/world/{id}/islands/{slot}/ecology")
@Tag(name = "World")
public class EcologyComparisonController {
    private final WorldHub hub;

    public EcologyComparisonController(WorldHub hub) {
        this.hub = hub;
    }

    @GetMapping("/compare")
    @Operation(summary = "Compare two island communities using six CSRBT beta-diversity measures.")
    public IslandEcologyComparisonResponse compare(@PathVariable("id") String id,
                                                   @PathVariable("slot") int slot,
                                                   @RequestParam("otherWorldId") String otherWorldId,
                                                   @RequestParam("otherSlot") int otherSlot) {
        WorldService firstWorld = mounted(id);
        WorldService secondWorld = mounted(otherWorldId);
        WorldService.IslandEcology first = snapshot(firstWorld, id, slot);
        WorldService.IslandEcology second = id.equals(otherWorldId) && slot == otherSlot
                ? first : snapshot(secondWorld, otherWorldId, otherSlot);
        return new IslandEcologyComparisonResponse(id, slot, first.day(),
                otherWorldId, otherSlot, second.day(),
                CommunityComparison.between(first.abundance(), second.abundance()));
    }

    private WorldService mounted(String id) {
        WorldService service = hub.get(id);
        if (service == null) throw ResourceNotFoundException.world(id);
        return service;
    }

    private static WorldService.IslandEcology snapshot(WorldService service, String id, int slot) {
        WorldService.IslandEcology snapshot = service.ecology(id, slot);
        if (snapshot == null) throw ResourceNotFoundException.island(slot);
        return snapshot;
    }
}
