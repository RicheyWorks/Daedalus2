// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.DailyMazeResponse;
import com.daedalus.api.dto.GenerateRequest;
import com.daedalus.api.dto.GenerateResponse;
import com.daedalus.api.dto.Hotspot;
import com.daedalus.api.dto.MoveRequest;
import com.daedalus.api.dto.SessionResponse;
import com.daedalus.api.dto.SolveResponse;
import com.daedalus.api.validation.AlgorithmId;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.LeaderboardEntry;
import com.daedalus.model.TileType;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.web.ResourceNotFoundException;
import com.daedalus.server.service.AlgorithmCatalogService;
import com.daedalus.server.service.DailyMazeService;
import com.daedalus.server.service.GameSessionService;
import com.daedalus.server.service.LeaderboardService;
import com.daedalus.server.service.LivingMazeService;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.MazeSolverService;
import com.daedalus.server.service.TrafficService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
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
 *   <li>{@code GET    /api/v1/maze/daily}                      — today's shared challenge (ADR-006)</li>
 *   <li>{@code GET    /api/v1/maze/{id}}                       — fetch metadata + tile grid</li>
 *   <li>{@code POST   /api/v1/maze/{id}/live}                  — bring the maze to life (ADR-006)</li>
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
    private final LivingMazeService living;
    private final DailyMazeService daily;
    private final TrafficService traffic;

    public MazeController(MazeGenerationService gen,
                          MazeSolverService solverSvc,
                          AlgorithmCatalogService catalog,
                          GameSessionService sessions,
                          LeaderboardService leaderboard,
                          LivingMazeService living,
                          DailyMazeService daily,
                          TrafficService traffic) {
        this.gen = gen;
        this.solverSvc = solverSvc;
        this.catalog = catalog;
        this.sessions = sessions;
        this.leaderboard = leaderboard;
        this.living = living;
        this.daily = daily;
        this.traffic = traffic;
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
                    + "Optional braid in [0, 1] opens that fraction of dead ends after generation "
                    + "(the tournament's sample recipe). "
                    + "Rate-limited per caller (authenticated subject, else client IP) against the "
                    + "'mazeGenerate' budget; bursts past the configured limit return 429 with a "
                    + "Retry-After header.")
    @PerKeyRateLimit("mazeGenerate")
    public GenerateResponse generate(@Valid @RequestBody GenerateRequest req) {
        long seed = req.seed() != null ? req.seed() : System.nanoTime();
        double braid = req.braid() == null ? 0.0 : req.braid();
        var cached = gen.generate(req.generatorId(), req.rows(), req.cols(), seed,
                req.hotspots(), braid);
        String actualGeneratorId = cached.metadata().generatorId();
        return toResponse(cached.metadata().id(), actualGeneratorId,
                req.rows(), req.cols(), seed, cached.grid(), cached.hotspots(),
                cached.braid());
    }

    /**
     * ADR-006 idea #4 — the shared daily challenge. The seed derives from the UTC date, so
     * every instance serves the same topology with zero coordination; this endpoint is a
     * cached read after the day's first request. Note the literal path deliberately
     * outranks {@code GET /maze/{id}} (exact segments win over templates in Spring's
     * mapping order), so "daily" is never misparsed as a UUID.
     */
    @GetMapping("/maze/daily")
    @Operation(summary = "Today's shared challenge — same maze for everyone until midnight UTC.",
            description = "Deterministic from the date: every server instance generates the "
                    + "identical topology. The returned maze is ordinary — solve it, open a "
                    + "session, bring it to life, or walk it blind via the agent API.")
    public DailyMazeResponse daily() {
        var d = daily.today();
        var c = d.maze();
        return new DailyMazeResponse(d.date().toString(), toResponse(
                c.metadata().id(), c.metadata().generatorId(),
                c.metadata().rows(), c.metadata().cols(), c.metadata().seed(), c.grid(),
                c.hotspots(), c.braid()));
    }

    @GetMapping("/maze/{id}")
    @Operation(summary = "Fetch a previously-generated maze's metadata + tile grid.")
    public ResponseEntity<GenerateResponse> get(@PathVariable UUID id) {
        var c = gen.find(id);
        if (c == null) throw ResourceNotFoundException.maze(id);
        return ResponseEntity.ok(toResponse(
                c.metadata().id(), c.metadata().generatorId(),
                c.metadata().rows(), c.metadata().cols(), c.metadata().seed(), c.grid(),
                c.hotspots(), c.braid()));
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
        if (c == null) throw ResourceNotFoundException.maze(id);
        List<com.daedalus.model.Point> path = List.of();
        if (solve != null) {
            var grid = c.grid();
            path = solverSvc.solve(solve, grid, grid.start(), grid.goal(), id).path();
        }
        return ResponseEntity.ok(
                com.daedalus.visualize.AsciiMazeVisualizer.renderToString(c.grid(), path));
    }

    /**
     * ADR-006 / ADR-008 — living mazes. Erosion only ever opens walls; hardening
     * ({@code seal}) only ever closes non-forest passages, so a live maze can never
     * become unsolvable mid-run. The default seed derives from the maze id so the same
     * maze brought to life mutates the same way every time. {@code seal} defaults to the
     * process-wide {@code daedalus.living.seal-factor} (0 — v1 erosion only).
     */
    @PostMapping("/maze/{id}/live")
    @Operation(summary = "Bring a maze to life: schedule bounded mutation ticks that mutate it in place.",
            description = "Each tick opens a fraction of the maze's dead-end walls, optionally "
                    + "closes a fraction of extra passages (seal in [0,1]), and drifts hotspot "
                    + "costs on weighted mazes, then swaps the new snapshot into the cache and "
                    + "publishes a MutationFrame on /topic/maze/{id}/state. Idempotent while "
                    + "alive (a second call returns the running ticker's status). Answers 409 "
                    + "when daedalus.living.max-concurrent mazes are already alive. "
                    + "Rate-limited per caller against the 'mazeLive' budget.")
    @PerKeyRateLimit("mazeLive")
    public ResponseEntity<LivingMazeService.LiveStatus> live(
            @PathVariable UUID id,
            @RequestParam(defaultValue = "30")
            @Min(value = 1,   message = "ticks must be at least 1")
            @Max(value = 240, message = "ticks must be at most 240")
            int ticks,
            @RequestParam(required = false) Long seed,
            @RequestParam(required = false)
            @DecimalMin(value = "0.0", message = "seal must be at least 0")
            @DecimalMax(value = "1.0", message = "seal must be at most 1")
            Double seal) {
        var c = gen.find(id);
        if (c == null) throw ResourceNotFoundException.maze(id);
        long erosionSeed = seed != null ? seed : id.getLeastSignificantBits();
        return ResponseEntity.ok(seal == null
                ? living.start(id, ticks, erosionSeed)
                : living.start(id, ticks, erosionSeed, seal));
    }

    /**
     * ADR-006 idea #3 — traffic. Enabling wraps a uniform grid weighted; from then on,
     * player moves and agent steps raise entered cells' costs and every pulse decays them
     * back toward uniform. Shares the {@code mazeLive} budget: same cost profile (each
     * acceptance schedules a ticker).
     */
    @PostMapping("/maze/{id}/traffic")
    @Operation(summary = "Track traffic on a maze: occupancy raises cell costs, which decay each pulse.",
            description = "Players and fog-of-war agents count identically. Weight-aware "
                    + "solvers route around the crowd; the response's hotspots list mirrors "
                    + "congestion so cost shading just works. Idempotent while tracked; 409 "
                    + "when daedalus.traffic.max-concurrent mazes are already tracked. "
                    + "Rate-limited against the 'mazeLive' budget.")
    @PerKeyRateLimit("mazeLive")
    public ResponseEntity<TrafficService.TrafficStatus> traffic(@PathVariable UUID id) {
        var status = traffic.enable(id);
        if (status == null) throw ResourceNotFoundException.maze(id);
        return ResponseEntity.ok(status);
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
        if (c == null) throw ResourceNotFoundException.maze(id);
        var grid = c.grid();
        var r = solverSvc.solve(solverId, grid, grid.start(), grid.goal(), id, replay);
        return ResponseEntity.ok(new SolveResponse(
                solverId, r.path(),
                r.stats().cellsVisited(), r.stats().cellsExplored(),
                r.stats().elapsed().toMillis(), r.stats().success(),
                r.expansions()));
    }

    /**
     * ADR-006 idea #5 — crossbreeding. Deterministic per (a, b, seed); the default seed
     * mixes both parents' ids so the same pair breeds the same child by default.
     */
    @PostMapping("/maze/breed")
    @Operation(summary = "Breed two mazes: the child inherits patches of both and is repaired to full connectivity.",
            description = "Parents must share dimensions (400 otherwise). The child is a "
                    + "first-class maze — solve it, play it, bring it to life, breed it "
                    + "again. Parent hotspots are unioned (max cost on a shared cell, "
                    + "capped at 64) so a weighted pair does not breed a uniform-cost child. "
                    + "Rate-limited against the 'mazeGenerate' budget.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<GenerateResponse> breed(
            @RequestParam UUID a,
            @RequestParam UUID b,
            @RequestParam(required = false) Long seed) {
        var pa = gen.find(a);
        var pb = gen.find(b);
        // Name the one that is missing. "one of your two parents is gone" is a worse answer
        // than "parent b is gone", and the caller cannot tell which to regenerate.
        if (pa == null) throw ResourceNotFoundException.maze(a);
        if (pb == null) throw ResourceNotFoundException.maze(b);
        long s = seed != null ? seed
                : a.getLeastSignificantBits() ^ Long.rotateLeft(b.getLeastSignificantBits(), 17);
        MazeGrid child = com.daedalus.engine.MazeBreeder.breed(pa.grid(), pb.grid(), s);
        var cached = gen.adopt(child, "crossbreed", s,
                mergeParentHotspots(pa.hotspots(), pb.hotspots()));
        return ResponseEntity.ok(toResponse(cached.metadata().id(), "crossbreed",
                cached.grid().rows(), cached.grid().cols(), s, cached.grid(),
                cached.hotspots(), null));
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
        // The session is fine and its maze has been evicted. Previously indistinguishable from
        // "no such session", which sent callers looking for the wrong problem.
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
                    + "feed owner-only. Rate-limited per caller against the 'sessionOpen' budget.")
    @PerKeyRateLimit("sessionOpen")
    public ResponseEntity<SessionResponse> join(
            @PathVariable UUID id,
            @RequestParam
            @NotBlank
            @Size(max = 64, message = "player name must be at most 64 chars")
            String player,
            Authentication authentication) {
        // Multiplayer off answers exactly what an unknown session answers — the endpoint has
        // to look absent, not disabled, or the 404 becomes a feature-flag oracle.
        if (!sessions.multiplayerEnabled()) throw ResourceNotFoundException.session(id);
        var s = sessions.find(id);
        if (s == null) throw ResourceNotFoundException.session(id);
        // The session is fine and its maze has been evicted. Previously indistinguishable from
        // "no such session", which sent callers looking for the wrong problem.
        var c = gen.find(s.mazeId());
        if (c == null) throw new ResourceNotFoundException("maze", s.mazeId().toString(),
                "Session " + id + " is open but its maze " + s.mazeId() + " has been evicted "
                        + "from the cache, so moves cannot be validated against it.");
        var joined = sessions.join(id, player, c.grid().start(), ownerOf(authentication));
        if (joined == null) return ResponseEntity.status(409).build(); // completed or full
        return ResponseEntity.ok(new SessionResponse(
                joined.id(), joined.mazeId(), joined.playerPosition(player)));
    }

    @GetMapping("/leaderboard")
    @Operation(summary = "Top-N completion times across active sessions.",
            description = "Snapshot — backed by Redis when daedalus.redis.enabled=true, "
                    + "otherwise in-memory. Pass maze=<id> for that maze's own board — the "
                    + "partition behind the daily challenge's leaderboard — or generator=<id> "
                    + "for one algorithm's board. maze wins if both are given, being the more "
                    + "specific of the two.")
    public List<LeaderboardEntry> leaderboard(
            @RequestParam(defaultValue = "20")
            @Min(value = 1,   message = "n must be at least 1")
            @Max(value = 100, message = "n must be at most 100")
            int n,
            @RequestParam(required = false) UUID maze,
            @RequestParam(required = false)
            @Size(max = 64, message = "generator id must be at most 64 chars")
            String generator) {
        if (maze != null) {
            return leaderboard.top(n, maze);
        }
        return leaderboard.topByGenerator(n, generator);
    }

    /**
     * Build a {@link GenerateResponse} from a maze grid + its identifying metadata. The grid's
     * {@link MazeGrid#toTileGrid()} returns the typed {@link TileType} layer; we flatten it to
     * {@code char[][]} here so the JSON response carries glyphs that any tile renderer (web,
     * desktop, terminal) can consume directly without importing the {@code TileType} enum.
     */
    private static GenerateResponse toResponse(UUID id, String generatorId, int rows, int cols,
                                                long seed, MazeGrid grid,
                                                List<com.daedalus.api.dto.Hotspot> hotspots,
                                                Double braid) {
        TileType[][] tiles = grid.toTileGrid();
        char[][] glyphs = new char[tiles.length][];
        for (int r = 0; r < tiles.length; r++) {
            glyphs[r] = new char[tiles[r].length];
            for (int c = 0; c < tiles[r].length; c++) {
                glyphs[r][c] = tiles[r][c].glyph();
            }
        }
        return new GenerateResponse(id, generatorId, rows, cols, seed, glyphs, hotspots, braid);
    }

    /**
     * Union of parent weights, row-major, max cost on a shared cell. Generate accepts
     * at most 64 hotspots; a pair of full lists would otherwise overflow that contract.
     */
    static List<Hotspot> mergeParentHotspots(List<Hotspot> a, List<Hotspot> b) {
        if ((a == null || a.isEmpty()) && (b == null || b.isEmpty())) {
            return null;
        }
        java.util.TreeMap<String, Hotspot> byCell = new java.util.TreeMap<>();
        for (Hotspot h : a == null ? List.<Hotspot>of() : a) {
            byCell.merge(String.format("%04d,%04d", h.row(), h.col()), h,
                    (x, y) -> x.cost() >= y.cost() ? x : y);
        }
        for (Hotspot h : b == null ? List.<Hotspot>of() : b) {
            byCell.merge(String.format("%04d,%04d", h.row(), h.col()), h,
                    (x, y) -> x.cost() >= y.cost() ? x : y);
        }
        return byCell.values().stream().limit(64).toList();
    }
}
