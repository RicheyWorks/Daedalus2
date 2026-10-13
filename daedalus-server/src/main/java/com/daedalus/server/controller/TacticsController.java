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
 * <p>Requires an authenticated configured host subject and configured squad in every profile; blank configuration
 * denies all. That one trusted subject owns encounter sessions for the squad. Session ids are not credentials.
 * The baseline is {@code SquadDirector}; opt-in configuration supplies a persistent adaptive brain.
 */
@RestController
@RequestMapping("/api/v1/tactics")
@Tag(name = "Tactics", description = "Squad orders for Unreal: DTR 1 + DTE 1 in, DTO 1 out (ADR-060).")
public class TacticsController {

    private final TacticsHost host;
    private final String hostSubject;
    private final String hostSquad;

    public TacticsController() { this(new TacticsHost()); }

    public TacticsController(TacticsHost host) { this(host, "", ""); }

    @org.springframework.beans.factory.annotation.Autowired
    public TacticsController(TacticsHost host,
            @org.springframework.beans.factory.annotation.Value("${daedalus.tactics.host.subject:}") String hostSubject,
            @org.springframework.beans.factory.annotation.Value("${daedalus.tactics.host.squad:}") String hostSquad) {
        this.host = java.util.Objects.requireNonNull(host);
        this.hostSubject = java.util.Objects.requireNonNull(hostSubject);
        this.hostSquad = java.util.Objects.requireNonNull(hostSquad);
    }

    @PostMapping("/decide")
    @Operation(summary = "One squad's roster and events in, its DTO 1 orders out (fenced by session and tick).")
    @PerKeyRateLimit("tacticsDecide")
    public ResponseEntity<TacticsDecideResponse> decide(@Valid @RequestBody TacticsDecideRequest body,
                                                       java.security.Principal principal) {
        // One explicitly trusted engine identity owns all encounter sessions for this configured squad.
        // Caller-supplied session ids are correlation keys, never authorization credentials.
        if (hostSubject.isBlank() || hostSquad.isBlank()
                || !(principal instanceof org.springframework.security.core.Authentication auth)
                || !auth.isAuthenticated()
                || auth instanceof org.springframework.security.authentication.AnonymousAuthenticationToken
                || !hostSubject.equals(auth.getName())) {
            throw new org.springframework.web.server.ResponseStatusException(org.springframework.http.HttpStatus.FORBIDDEN,
                    "Tactical host not authorized");
        }
        var roster = com.daedalus.world.tactics.TacticalOrders.parseRoster(body.roster());
        if (!hostSquad.equals(roster.squad())) {
            throw new org.springframework.web.server.ResponseStatusException(org.springframework.http.HttpStatus.FORBIDDEN,
                    "Tactical squad not authorized");
        }
        TacticsHost.Decision d = host.decide(body.roster(), body.events());
        return ResponseEntity.ok(new TacticsDecideResponse(d.result().name(), d.spec(), d.why(), host.squads()));
    }
}
