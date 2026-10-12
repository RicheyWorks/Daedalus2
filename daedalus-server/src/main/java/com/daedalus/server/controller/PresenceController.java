// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.PresenceService;
import com.daedalus.server.service.WorldHub;
import com.daedalus.server.web.ResourceNotFoundException;
import io.swagger.v3.oas.annotations.Operation;
import org.springframework.http.ResponseEntity;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.security.Principal;
import java.util.List;
import java.util.Map;

/**
 * Players in a world (ADR-039). Clients POST where they are a few times a second; everyone subscribed to
 * {@code /topic/world/{id}/presence} sees MOVE and LEAVE frames. Clients cannot SEND over STOMP (the
 * interceptor rejects it), so reports come in over HTTP, where the rate limiter and auth apply.
 */
@RestController
@RequestMapping("/api/v1")
public class PresenceController {

    public static final String TAB_HEADER = "X-Daedalus-Tab";

    private final WorldHub hub;
    private final PresenceService presence;

    public PresenceController(WorldHub hub, SimpMessagingTemplate stomp) {
        this.hub = hub;
        this.presence = new PresenceService(System::currentTimeMillis,
                f -> stomp.convertAndSend("/topic/world/" + f.worldId() + "/presence", f));
    }

    @GetMapping("/world/{id}/presence")
    @Operation(summary = "Everyone walking around in this world now.")
    public ResponseEntity<Map<String, Object>> who(@PathVariable String id) {
        if (hub.get(id) == null) {
            throw ResourceNotFoundException.world(id);   // the JSON error contract, not an empty 404
        }
        List<PresenceService.Player> players = presence.who(id);
        return ResponseEntity.ok(Map.of("worldId", id, "players", players, "staleMs", PresenceService.STALE_MS));
    }

    @PostMapping("/world/{id}/presence")
    @PerKeyRateLimit("presence")
    @Operation(summary = "Say where you are: position, heading, animation and look. Send it a few times a second.")
    public ResponseEntity<Map<String, Object>> report(@PathVariable String id, @RequestBody PresenceService.Report body,
                                                      @RequestHeader(value = TAB_HEADER, required = false) String tab,
                                                      Principal principal) {
        if (hub.get(id) == null) {
            throw ResourceNotFoundException.world(id);   // the JSON error contract, not an empty 404
        }
        String pid = PresenceService.playerId(principal == null ? null : principal.getName(), tab);
        PresenceService.Result r = presence.report(id, pid, body);
        if (!r.ok()) {
            return ResponseEntity.badRequest().body(Map.of("error", r.refused()));
        }
        return ResponseEntity.ok(Map.of("player", r.player()));
    }

    @PostMapping("/world/{id}/presence/leave")
    @PerKeyRateLimit("presence")
    @Operation(summary = "Leave now, instead of fading out after the stale time.")
    public ResponseEntity<Map<String, Object>> leave(@PathVariable String id,
                                                     @RequestHeader(value = TAB_HEADER, required = false) String tab,
                                                     Principal principal) {
        String pid = PresenceService.playerId(principal == null ? null : principal.getName(), tab);
        return ResponseEntity.ok(Map.of("left", presence.leave(id, pid)));
    }

    /** For tests: the service behind the endpoints. */
    PresenceService service() {
        return presence;
    }
}
