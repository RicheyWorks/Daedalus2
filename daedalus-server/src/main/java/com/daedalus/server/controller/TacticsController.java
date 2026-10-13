// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.TacticsDecideRequest;
import com.daedalus.api.dto.TacticsDecideResponse;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.world.tactics.TacticsHost;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The squad director over HTTP for Unreal (ADR-060 transport). The game posts a squad's DTR 1 roster and DTE 1
 * events about once a second per squad, off the game thread, and applies the DTO 1 spec it gets back. Ticks are
 * fenced per (session, squad) here and again natively, so retries and reordering are harmless. Unreal keeps its
 * native fallback when this does not answer in time: nothing in a frame waits on Java.
 *
 * <p>Authenticated in prod: only the trusted game host (signed in as the ops user) may drive NPCs. The brain is the
 * baseline {@code SquadDirector}; the adaptive director (PR32) replaces it through {@link TacticsHost.Brain}.
 */
@RestController
@RequestMapping("/api/v1/tactics")
@Tag(name = "Tactics", description = "Squad orders for Unreal: DTR 1 + DTE 1 in, DTO 1 out (ADR-060).")
public class TacticsController {

    private final TacticsHost host = new TacticsHost();

    @PostMapping("/decide")
    @Operation(summary = "One squad's roster and events in, its DTO 1 orders out (fenced by session and tick).")
    @PerKeyRateLimit("tacticsDecide")
    public ResponseEntity<TacticsDecideResponse> decide(@Valid @RequestBody TacticsDecideRequest body) {
        TacticsHost.Decision d = host.decide(body.roster(), body.events());
        return ResponseEntity.ok(new TacticsDecideResponse(d.result().name(), d.spec(), d.why(), host.squads()));
    }
}
