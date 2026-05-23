package com.daedalus.controller;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.LeaderboardEntry;
import com.daedalus.model.Point;
import com.daedalus.service.AlgorithmCatalogService;
import com.daedalus.service.GameSessionService;
import com.daedalus.service.LeaderboardService;
import com.daedalus.service.MazeGenerationService;
import com.daedalus.service.MazeSolverService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Primary REST surface.
 *
 * <p>Endpoints:
 * <ul>
 *   <li>{@code GET    /api/algorithms}                         — list everything registered</li>
 *   <li>{@code POST   /api/maze/generate}                      — generate a maze</li>
 *   <li>{@code GET    /api/maze/{id}}                          — fetch metadata + tile grid</li>
 *   <li>{@code POST   /api/maze/{id}/solve/{solverId}}         — run a solver against the maze</li>
 *   <li>{@code POST   /api/maze/{id}/session?player=...}       — open a play session</li>
 *   <li>{@code POST   /api/session/{id}/move}                  — move the player</li>
 *   <li>{@code GET    /api/leaderboard?n=20}                   — leaderboard snapshot</li>
 * </ul>
 */
@RestController
@RequestMapping("/api")
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

    public record GenerateRequest(String generatorId, int rows, int cols, Long seed) {}
    public record GenerateResponse(UUID id, String generatorId, int rows, int cols,
                                   long seed, char[][] tiles) {}

    @GetMapping("/algorithms")
    public Map<String, List<AlgorithmDescriptor>> algorithms() {
        return Map.of(
                "generators", catalog.generators(),
                "solvers", catalog.solvers()
        );
    }

    @PostMapping("/maze/generate")
    public GenerateResponse generate(@RequestBody GenerateRequest req) {
        long seed = req.seed() != null ? req.seed() : System.nanoTime();
        var cached = gen.generate(req.generatorId(), req.rows(), req.cols(), seed);
        return toResponse(cached.metadata().id(), req.generatorId(),
                req.rows(), req.cols(), seed, cached.grid());
    }

    @GetMapping("/maze/{id}")
    public ResponseEntity<GenerateResponse> get(@PathVariable UUID id) {
        var c = gen.find(id);
        if (c == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(toResponse(
                c.metadata().id(), c.metadata().generatorId(),
                c.metadata().rows(), c.metadata().cols(), c.metadata().seed(), c.grid()));
    }

    public record SolveResponse(String solverId, List<Point> path,
                                 long visited, long explored, long elapsedMs, boolean success) {}

    @PostMapping("/maze/{id}/solve/{solverId}")
    public ResponseEntity<SolveResponse> solve(@PathVariable UUID id, @PathVariable String solverId) {
        var c = gen.find(id);
        if (c == null) return ResponseEntity.notFound().build();
        var r = solverSvc.solve(solverId, c.grid(), id);
        return ResponseEntity.ok(new SolveResponse(
                solverId, r.path(),
                r.stats().cellsVisited(), r.stats().cellsExplored(),
                r.stats().elapsed().toMillis(), r.stats().success()));
    }

    public record SessionResponse(UUID sessionId, UUID mazeId, Point position) {}

    @PostMapping("/maze/{id}/session")
    public ResponseEntity<SessionResponse> openSession(@PathVariable UUID id,
                                                       @RequestParam(defaultValue = "anon") String player) {
        var c = gen.find(id);
        if (c == null) return ResponseEntity.notFound().build();
        var s = sessions.open(id, player, c.grid().start());
        return ResponseEntity.ok(new SessionResponse(s.id(), id, s.currentPosition()));
    }

    public record MoveRequest(Point to) {}

    @PostMapping("/session/{id}/move")
    public ResponseEntity<Boolean> move(@PathVariable UUID id, @RequestBody MoveRequest req) {
        var s = sessions.find(id);
        if (s == null) return ResponseEntity.notFound().build();
        var c = gen.find(s.mazeId());
        if (c == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(sessions.tryMove(id, c.grid(), req.to()));
    }

    @GetMapping("/leaderboard")
    public List<LeaderboardEntry> leaderboard(@RequestParam(defaultValue = "20") int n) {
        return leaderboard.top(n);
    }

    private GenerateResponse toResponse(UUID id, String genId, int rows, int cols,
                                         long seed, MazeGrid grid) {
        var tiles = grid.toTileGrid();
        char[][] flat = new char[tiles.length][tiles[0].length];
        for (int r = 0; r < tiles.length; r++)
            for (int c = 0; c < tiles[0].length; c++)
                flat[r][c] = tiles[r][c].glyph();
        return new GenerateResponse(id, genId, rows, cols, seed, flat);
    }
}
