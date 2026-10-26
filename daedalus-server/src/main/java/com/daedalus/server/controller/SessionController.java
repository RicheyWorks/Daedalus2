// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.MoveRequest;
import com.daedalus.api.dto.SessionResponse;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.GameSessionService;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.web.ResourceNotFoundException;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

/**
 * Play sessions: open, spectate, move, join. Split from {@link MazeController} so
 * generate/solve and the board no longer share one constructor with nine services.
 */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "Sessions", description = "Open, spectate, move, and join play sessions.")
@Validated
public class SessionController {

    private final MazeGenerationService gen;
    private final GameSessionService sessions;

    public SessionController(MazeGenerationService gen, GameSessionService sessions) {
        this.gen = gen;
        this.sessions = sessions;
    }

    /**
     * ADR-006 idea #6 — the spectator seam: a read-only snapshot of a live session. The
     * web UI's {@code #session=<id>} permalink loads this once (including the opening
     * player's walk so far) and then follows the same STOMP frames the players produce.
     */
    @GetMapping("/session/{id}")
    @Operation(summary = "Read-only session snapshot — the spectator entry point.",
            description = "Includes the opening player's recorded trail so a late spectator "
                    + "can paint the walk, not just the current cell. Pair with "
                    + "/topic/session/{id}/player for live moves; owned sessions keep their "
                    + "existing per-destination STOMP authorization. Subjects stay off "
                    + "the body.")
    public ResponseEntity<com.daedalus.api.dto.SessionViewResponse> session(@PathVariable UUID id) {
        var s = sessions.find(id);
        if (s == null) throw ResourceNotFoundException.session(id);
        return ResponseEntity.ok(new com.daedalus.api.dto.SessionViewResponse(
                s.id(), s.mazeId(), s.playerName(), s.players(),
                s.completed(), s.moveCount(), s.score(), s.trail(), s.walks(),
                s.completed() ? s.completedBy() : null));
    }

    @PostMapping("/maze/{id}/session")
    @Operation(summary = "Open a play session for the given maze.",
            description = "The returned session id is required for /api/v1/session/{id}/move. "
                    + "When the request is authenticated, the session is owned by the token's "
                    + "subject and its /topic/session/{id}/player STOMP topic is restricted "
                    + "to that subject. Rate-limited per caller against the 'sessionOpen' "
                    + "budget — session creation feeds every bounded store downstream.")
    @PerKeyRateLimit("sessionOpen")
    public ResponseEntity<SessionResponse> openSession(
            @PathVariable UUID id,
            @RequestParam(defaultValue = "anon")
            @NotBlank
            @Size(max = 64, message = "player name must be at most 64 chars")
            String player,
            Authentication authentication) {
        var c = gen.find(id);
        if (c == null) throw ResourceNotFoundException.maze(id);
        var s = sessions.open(id, c.metadata().generatorId(), player, c.grid().start(),
                ownerOf(authentication));
        return ResponseEntity.ok(new SessionResponse(s.id(), id, s.currentPosition()));
    }

    /**
     * The verified subject a new session should be owned by, or {@code null} for anonymous
     * callers. Anonymous includes Spring's {@code AnonymousAuthenticationToken} (the dev
     * profile's permitAll posture), so a dev session stays unowned and its topics stay open —
     * mirroring how {@code StompAuthChannelInterceptor} treats missing-vs-forged credentials.
     */
    static String ownerOf(Authentication authentication) {
        if (authentication == null
                || !authentication.isAuthenticated()
                || authentication instanceof AnonymousAuthenticationToken) {
            return null;
        }
        return authentication.getName();
    }

    @PostMapping("/session/{id}/move")
    @Operation(summary = "Move a player to an adjacent cell.",
            description = "Returns true if the move was legal (target cell is open and adjacent). "
                    + "Omit 'player' to move the session's opening player; name one to move a "
                    + "joined player (multiplayer flag only). Rate-limited per caller against the "
                    + "'sessionMove' budget — the same 1200/min the fog-of-war agent gets, because "
                    + "it is the same shape of traffic. Until an audit measured it this endpoint "
                    + "had no limit at all, and one client sustained 201 moves/s.")
    @PerKeyRateLimit("sessionMove")
    public ResponseEntity<Boolean> move(@PathVariable UUID id, @Valid @RequestBody MoveRequest req) {
        var s = sessions.find(id);
        if (s == null) throw ResourceNotFoundException.session(id);
        var c = gen.find(s.mazeId());
        if (c == null) throw new ResourceNotFoundException("maze", s.mazeId().toString(),
                "Session " + id + " is open but its maze " + s.mazeId() + " has been evicted "
                        + "from the cache, so moves cannot be validated against it.");
        return ResponseEntity.ok(sessions.tryMove(id, req.player(), c.grid(), req.to(), gen));
    }

    @PostMapping("/session/{id}/join")
    @Operation(summary = "Join an existing session as an additional named player.",
            description = "Requires the daedalus.session.multiplayer flag; without it this "
                    + "endpoint answers 404 as if it did not exist. Joining a name already in "
                    + "the session keeps that player's position (reconnect must not teleport). "
                    + "When the request is authenticated, the token's subject is added to the "
                    + "session's STOMP allowlist (ADR-012) so the joiner can SUBSCRIBE to the "
                    + "player topic — joining used to put a piece on the board and leave the "
                    + "feed owner-only. A finished session and a full session both answer 409 "
                    + "but with distinct problem types (session-completed vs session-full). "
                    + "Rate-limited per caller against the 'sessionOpen' budget.")
    @PerKeyRateLimit("sessionOpen")
    public ResponseEntity<SessionResponse> join(
            @PathVariable UUID id,
            @RequestParam
            @NotBlank
            @Size(max = 64, message = "player name must be at most 64 chars")
            String player,
            Authentication authentication) {
        if (!sessions.multiplayerEnabled()) throw ResourceNotFoundException.session(id);
        var s = sessions.find(id);
        if (s == null) throw ResourceNotFoundException.session(id);
        var c = gen.find(s.mazeId());
        if (c == null) throw new ResourceNotFoundException("maze", s.mazeId().toString(),
                "Session " + id + " is open but its maze " + s.mazeId() + " has been evicted "
                        + "from the cache, so a join cannot be seated against it.");
        var joined = sessions.join(id, player, c.grid().start(), ownerOf(authentication));
        if (joined == null) throw ResourceNotFoundException.session(id);
        return ResponseEntity.ok(new SessionResponse(
                joined.id(), joined.mazeId(), joined.playerPosition(player)));
    }
}
