// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.GenerateRequest;
import com.daedalus.api.dto.GenerateResponse;
import com.daedalus.api.dto.MoveRequest;
import com.daedalus.api.dto.SessionResponse;
import com.daedalus.api.dto.SolveResponse;
import com.daedalus.api.validation.AlgorithmId;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.LeaderboardEntry;
import com.daedalus.model.TileType;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.AlgorithmCatalogService;
import com.daedalus.server.service.GameSessionService;
import com.daedalus.server.service.LeaderboardService;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.MazeSolverService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Primary REST surface.
 *
 * <p>Endpoints:
 * <ul>
 *   <li>{@code GET    /api/v1/algorithms}                      — list everything registered</li>
 *   <li>{@code POST   /api/v1/maze/generate}                   — generate a maze</li>
 *   <li>{@code GET    /api/v1/maze/{id}}                       — fetch metadata + tile grid</li>
 *   <li>{@code POST   /api/v1/maze/{id}/solve/{solverId}}      — run a solver against the maze</li>
 *   <li>{@code POST   /api/v1/maze/{id}/session?player=...}    — open a play session</li>
 *   <li>{@code POST   /api/v1/session/{id}/move}               — move a player</li>
 *   <li>{@code POST   /api/v1/session/{id}/join?player=...}    — join as an extra player
 *       (multiplayer flag)</li>
 *   <li>{@code GET    /api/v1/leaderboard?n=20}                — leaderboard snapshot</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "Mazes", description = "Generate, fetch, solve, and play mazes.")
@Validated // enables @Min/@Max/@Pattern on @PathVariable and @RequestParam (body validation works without it)
public class MazeController {

    private final MazeGenerationService gen;
    private final MazeSolverService solverSvc;
    private final AlgorithmCatalogService catalog;
    private final GameSessionService sessions;
    private final LeaderboardService leaderboard;

    public MazeController(MazeGenerationService gen,
                          MazeSolverService solverSvc,
                          AlgorithmCatalogService catalog,
                          GameSessionService sessions,
                          LeaderboardService leaderboard) {
        this.gen = gen;
        this.solverSvc = solverSvc;
        this.catalog = catalog;
        this.sessions = sessions;
        this.leaderboard = leaderboard;
    }

    @GetMapping("/algorithms")
    @Operation(summary = "List every registered generator and solver, grouped by role.")
    public Map<String, List<AlgorithmDescriptor>> algorithms() {
        return Map.of(
                "generators", catalog.generators(),
                "solvers", catalog.solvers()
        );
    }

    @PostMapping("/maze/generate")
    @Operation(summary = "Generate a maze.",
            description = "If the named generator is unavailable or the circuit breaker is open, "
                    + "the response's generatorId reflects the actual fallback algorithm used. "
                    + "Rate-limited per caller (authenticated subject, else client IP) against the "
                    + "'mazeGenerate' budget; bursts past the configured limit return 429 with a "
                    + "Retry-After header.")
    @PerKeyRateLimit("mazeGenerate")
    public GenerateResponse generate(@Valid @RequestBody GenerateRequest req) {
        long seed = req.seed() != null ? req.seed() : System.nanoTime();
        var cached = gen.generate(req.generatorId(), req.rows(), req.cols(), seed, req.hotspots());
        String actualGeneratorId = cached.metadata().generatorId();
        return toResponse(cached.metadata().id(), actualGeneratorId,
                req.rows(), req.cols(), seed, cached.grid(), cached.hotspots());
    }

    @GetMapping("/maze/{id}")
    @Operation(summary = "Fetch a previously-generated maze's metadata + tile grid.")
    public ResponseEntity<GenerateResponse> get(@PathVariable UUID id) {
        var c = gen.find(id);
        if (c == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(toResponse(
                c.metadata().id(), c.metadata().generatorId(),
                c.metadata().rows(), c.metadata().cols(), c.metadata().seed(), c.grid(),
                c.hotspots()));
    }

    /**
     * The same maze, negotiated as terminal-ready ASCII art — the core
     * {@code AsciiMazeVisualizer} wired to the product surface. {@code curl} it:
     * <pre>curl -H "Accept: text/plain" localhost:8080/api/v1/maze/{id}?solve=bfs</pre>
     * The optional {@code solve} runs that solver and overlays the route as {@code .} glyphs.
     * Dungeons render honestly (rock is {@code #}) thanks to the projection's honesty rules.
     */
    @GetMapping(value = "/maze/{id}", produces = MediaType.TEXT_PLAIN_VALUE)
    @Operation(summary = "The maze as ASCII art (Accept: text/plain); optional ?solve=<solverId> overlays a route.")
    public ResponseEntity<String> getAscii(
            @PathVariable UUID id,
            @RequestParam(required = false) @AlgorithmId String solve) {
        var c = gen.find(id);
        if (c == null) return ResponseEntity.notFound().build();
        List<com.daedalus.model.Point> path = List.of();
        if (solve != null) {
            var grid = c.grid();
            path = solverSvc.solve(solve, grid, grid.start(), grid.goal(), id).path();
        }
        return ResponseEntity.ok(
                com.daedalus.visualize.AsciiMazeVisualizer.renderToString(c.grid(), path));
    }

    @PostMapping("/maze/{id}/solve/{solverId}")
    @Operation(summary = "Run a registered solver against a stored maze.",
            description = "Rate-limited per caller (authenticated subject, else client IP) against "
                    + "the 'mazeSolve' budget. Pass replay=true to also receive the search's "
                    + "expansion order for step-by-step animation.")
    @PerKeyRateLimit("mazeSolve")
    public ResponseEntity<SolveResponse> solve(
            @PathVariable UUID id,
            @PathVariable
            @AlgorithmId
            String solverId,
            @RequestParam(defaultValue = "false") boolean replay) {
        var c = gen.find(id);
        if (c == null) return ResponseEntity.notFound().build();
        var grid = c.grid();
        var r = solverSvc.solve(solverId, grid, grid.start(), grid.goal(), id, replay);
        return ResponseEntity.ok(new SolveResponse(
                solverId, r.path(),
                r.stats().cellsVisited(), r.stats().cellsExplored(),
                r.stats().elapsed().toMillis(), r.stats().success(),
                r.expansions()));
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
        if (c == null) return ResponseEntity.notFound().build();
        var s = sessions.open(id, player, c.grid().start(), ownerOf(authentication));
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
                    + "joined player (multiplayer flag only).")
    public ResponseEntity<Boolean> move(@PathVariable UUID id, @Valid @RequestBody MoveRequest req) {
        var s = sessions.find(id);
        if (s == null) return ResponseEntity.notFound().build();
        var c = gen.find(s.mazeId());
        if (c == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(sessions.tryMove(id, req.player(), c.grid(), req.to()));
    }

    @PostMapping("/session/{id}/join")
    @Operation(summary = "Join an existing session as an additional named player.",
            description = "Requires the daedalus.session.multiplayer flag; without it this "
                    + "endpoint answers 404 as if it did not exist. Joining a name already in "
                    + "the session keeps that player's position (reconnect must not teleport). "
                    + "Rate-limited per caller against the 'sessionOpen' budget.")
    @PerKeyRateLimit("sessionOpen")
    public ResponseEntity<SessionResponse> join(
            @PathVariable UUID id,
            @RequestParam
            @NotBlank
            @Size(max = 64, message = "player name must be at most 64 chars")
            String player) {
        if (!sessions.multiplayerEnabled()) return ResponseEntity.notFound().build();
        var s = sessions.find(id);
        if (s == null) return ResponseEntity.notFound().build();
        var c = gen.find(s.mazeId());
        if (c == null) return ResponseEntity.notFound().build();
        var joined = sessions.join(id, player, c.grid().start());
        if (joined == null) return ResponseEntity.status(409).build(); // completed session
        return ResponseEntity.ok(new SessionResponse(
                joined.id(), joined.mazeId(), joined.playerPosition(player)));
    }

    @GetMapping("/leaderboard")
    @Operation(summary = "Top-N completion times across active sessions.",
            description = "Snapshot — backed by Redis when daedalus.redis.enabled=true, otherwise in-memory.")
    public List<LeaderboardEntry> leaderboard(
            @RequestParam(defaultValue = "20")
            @Min(value = 1,   message = "n must be at least 1")
            @Max(value = 100, message = "n must be at most 100")
            int n) {
        return leaderboard.top(n);
    }

    /**
     * Build a {@link GenerateResponse} from a maze grid + its identifying metadata. The grid's
     * {@link MazeGrid#toTileGrid()} returns the typed {@link TileType} layer; we flatten it to
     * {@code char[][]} here so the JSON response carries glyphs that any tile renderer (web,
     * desktop, terminal) can consume directly without importing the {@code TileType} enum.
     */
    private static GenerateResponse toResponse(UUID id, String generatorId, int rows, int cols,
                                                long seed, MazeGrid grid,
                                                List<com.daedalus.api.dto.Hotspot> hotspots) {
        TileType[][] tiles = grid.toTileGrid();
        char[][] glyphs = new char[tiles.length][];
        for (int r = 0; r < tiles.length; r++) {
            glyphs[r] = new char[tiles[r].length];
            for (int c = 0; c < tiles[r].length; c++) {
                glyphs[r][c] = tiles[r][c].glyph();
            }
        }
        return new GenerateResponse(id, generatorId, rows, cols, seed, glyphs, hotspots);
    }
}
