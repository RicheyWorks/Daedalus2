// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.AnalysisResponse;
import com.daedalus.engine.Braider;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.GhostService;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.theory.MazeFlow;
import com.daedalus.theory.MazeMetrics;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import com.daedalus.server.service.WaypointService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

/**
 * Read-only insight over stored mazes — where the {@code theory} module finally reaches
 * the product surface (ADR-006 idea #9), plus ghost recordings (idea #8).
 *
 * <ul>
 *   <li>{@code GET /api/v1/maze/{id}/analysis} — min-cut chokepoints, dead ends, route
 *       length. Computed on the current snapshot: analyze a living maze twice and watch
 *       its chokepoints dissolve as erosion braids them away.</li>
 *   <li>{@code GET /api/v1/maze/{id}/ghost} — the best completed run's timed recording,
 *       replayed by the web UI as a translucent racer.</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "Insight", description = "Structural analysis and ghost recordings.")
public class InsightController {

    private final MazeGenerationService gen;
    private final GhostService ghosts;
    private final WaypointService waypoints;

    public InsightController(MazeGenerationService gen, GhostService ghosts,
                             WaypointService waypoints) {
        this.gen = gen;
        this.ghosts = ghosts;
        this.waypoints = waypoints;
    }

    /**
     * ADR-007 idea 1 — Waypoint Tour mode. Held-Karp is {@code O(2^k · k²)}, so this shares
     * the {@code mazeSolve} budget and the waypoint count is hard-capped by the service.
     */
    @GetMapping("/maze/{id}/tour")
    @Operation(summary = "The maze's waypoints and the provably optimal route collecting them all.",
            description = "Waypoints are placed by k-center (farthest-first), so they spread "
                    + "rather than clump, and they derive from the maze alone — every player on "
                    + "a maze solves the same instance, which is what makes scoring against the "
                    + "optimum comparable between players. The order is exact, not heuristic: "
                    + "Held-Karp over the waypoint set plus the goal as the compulsory last "
                    + "stop. Rate-limited against the 'mazeSolve' budget.")
    @PerKeyRateLimit("mazeSolve")
    public ResponseEntity<WaypointService.Tour> tour(
            @PathVariable UUID id,
            @RequestParam(required = false) Integer count) {
        var tour = waypoints.tourFor(id, count);
        return tour == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(tour);
    }

    @GetMapping("/session/{id}/tour")
    @Operation(summary = "How a session is doing against the optimal tour.",
            description = "Collection is observed server-side from the session's own moves, not "
                    + "reported by the client, so the count that scores cannot be claimed.")
    public ResponseEntity<WaypointService.Progress> tourProgress(@PathVariable UUID id) {
        var progress = waypoints.progressFor(id);
        return progress == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(progress);
    }

    /**
     * Max-flow (min-cut) plus two linear sweeps — comparable to a solve in cost, so it
     * shares the {@code mazeSolve} budget rather than minting a new one.
     */
    @GetMapping("/maze/{id}/analysis")
    @Operation(summary = "Structural analysis: min-cut chokepoints, dead ends, route length.",
            description = "cutSize is start↔goal edge connectivity — 1 on every perfect maze "
                    + "(sever any route passage and the maze splits), higher once braided. "
                    + "The chokepoints are the actual min-cut passages. Computed on the "
                    + "maze's CURRENT snapshot; a living maze re-analyzes differently as it "
                    + "erodes. Rate-limited against the 'mazeSolve' budget.")
    @PerKeyRateLimit("mazeSolve")
    public ResponseEntity<AnalysisResponse> analysis(@PathVariable UUID id) {
        var c = gen.find(id);
        if (c == null) {
            return ResponseEntity.notFound().build();
        }
        var grid = c.grid();
        MazeFlow.MinCut cut = MazeFlow.minCutStartToGoal(grid);
        var deadEnds = Braider.deadEnds(grid);
        var route = MazeMetrics.shortestPath(grid, grid.start(), grid.goal());
        return ResponseEntity.ok(new AnalysisResponse(
                id, grid.rows(), grid.cols(),
                route.size(), cut.cutSize(), cut.cutEdges(),
                deadEnds.size(), deadEnds));
    }

    @GetMapping("/maze/{id}/ghost")
    @Operation(summary = "The best completed run on this maze, as a timed recording.",
            description = "404 until someone completes a session on the maze. The web UI "
                    + "replays it as a translucent ghost racing the live player — original "
                    + "pacing included, hesitations and all.")
    public ResponseEntity<GhostService.GhostRun> ghost(@PathVariable UUID id) {
        var run = ghosts.ghostOf(id);
        return run == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(run);
    }
}
