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
import org.springframework.http.ResponseEntity;
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
 *   <li>{@code POST   /api/v1/session/{id}/move}               — move the player</li>
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
        var cached = gen.generate(req.generatorId(), req.rows(), req.cols(), seed);
        String actualGeneratorId = cached.metadata().generatorId();
        return toResponse(cached.metadata().id(), actualGeneratorId,
                req.rows(), req.cols(), seed, cached.grid());
    }

    @GetMapping("/maze/{id}")
    @Operation(summary = "Fetch a previously-generated maze's metadata + tile grid.")
    public ResponseEntity<GenerateResponse> get(@PathVariable UUID id) {
        var c = gen.find(id);
        if (c == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(toResponse(
                c.metadata().id(), c.metadata().generatorId(),
                c.metadata().rows(), c.metadata().cols(), c.metadata().seed(), c.grid()));
    }

    @PostMapping("/maze/{id}/solve/{solverId}")
    @Operation(summary = "Run a registered solver against a stored maze.",
            description = "Rate-limited per caller (authenticated subject, else client IP) against "
                    + "the 'mazeSolve' budget.")
    @PerKeyRateLimit("mazeSolve")
    public ResponseEntity<SolveResponse> solve(
            @PathVariable UUID id,
            @PathVariable
            @AlgorithmId
            String solverId) {
        var c = gen.find(id);
        if (c == null) return ResponseEntity.notFound().build();
        var r = solverSvc.solve(solverId, c.grid(), id);
        return ResponseEntity.ok(new SolveResponse(
                solverId, r.path(),
                r.stats().cellsVisited(), r.stats().cellsExplored(),
                r.stats().elapsed().toMillis(), r.stats().success()));
    }

    @PostMapping("/maze/{id}/session")
    @Operation(summary = "Open a play session for the given maze.",
            description = "The returned session id is required for /api/v1/session/{id}/move.")
    public ResponseEntity<SessionResponse> openSession(
            @PathVariable UUID id,
            @RequestParam(defaultValue = "anon")
            @NotBlank
            @Size(max = 64, message = "player name must be at most 64 chars")
            String player) {
        var c = gen.find(id);
        if (c == null) return ResponseEntity.notFound().build();
        var s = sessions.open(id, player, c.grid().start());
        return ResponseEntity.ok(new SessionResponse(s.id(), id, s.currentPosition()));
    }

    @PostMapping("/session/{id}/move")
    @Operation(summary = "Move the player to an adjacent cell.",
            description = "Returns true if the move was legal (target cell is open and adjacent).")
    public ResponseEntity<Boolean> move(@PathVariable UUID id, @Valid @RequestBody MoveRequest req) {
        var s = sessions.find(id);
        if (s == null) return ResponseEntity.notFound().build();
        var c = gen.find(s.mazeId());
        if (c == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(sessions.tryMove(id, c.grid(), req.to()));
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
                                                long seed, MazeGrid grid) {
        TileType[][] tiles = grid.toTileGrid();
        char[][] glyphs = new char[tiles.length][];
        for (int r = 0; r < tiles.length; r++) {
            glyphs[r] = new char[tiles[r].length];
            for (int c = 0; c < tiles[r].length; c++) {
                glyphs[r][c] = tiles[r][c].glyph();
            }
        }
        return new GenerateResponse(id, generatorId, rows, cols, seed, glyphs);
    }
}
