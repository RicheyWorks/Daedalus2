// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.AnalysisResponse;
import com.daedalus.engine.Braider;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.GhostService;
import com.daedalus.server.service.HardestRouteService;
import com.daedalus.server.service.TopographyService;
import com.daedalus.server.service.TournamentService;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.theory.MazeFlow;
import com.daedalus.theory.MazeMetrics;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import com.daedalus.server.service.ComplexityLabService;
import com.daedalus.server.service.FingerprintService;
import com.daedalus.server.service.WaypointService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
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
    private final ComplexityLabService complexity;
    private final FingerprintService fingerprints;
    private final HardestRouteService hardestRoutes;
    private final TopographyService topography;
    private final TournamentService tournaments;

    public InsightController(MazeGenerationService gen, GhostService ghosts,
                             WaypointService waypoints, ComplexityLabService complexity,
                             FingerprintService fingerprints,
                             HardestRouteService hardestRoutes,
                             TopographyService topography,
                             TournamentService tournaments) {
        this.gen = gen;
        this.ghosts = ghosts;
        this.waypoints = waypoints;
        this.complexity = complexity;
        this.fingerprints = fingerprints;
        this.hardestRoutes = hardestRoutes;
        this.topography = topography;
        this.tournaments = tournaments;
    }

    /**
     * ADR-007 idea 4 — identify the algorithm from the maze's shape. One O(cells) sweep plus a
     * nearest-centroid lookup, so it shares the {@code mazeSolve} budget; the classifier trains
     * once on first use.
     */
    @GetMapping("/maze/{id}/fingerprint")
    @Operation(summary = "Structural signature of a maze, and which generator most likely made it.",
            description = "Every feature is a ratio rather than a count, so the signature "
                    + "describes texture and not size. The verdict is nearest-centroid over "
                    + "signatures learned from the registered generators: measured on held-out "
                    + "mazes it names the exact generator ~59% of the time against ~4.5% chance, "
                    + "and the right family of algorithm ~87% of the time. The gap is not "
                    + "sloppiness — Aldous-Broder and Wilson's both sample uniform spanning "
                    + "trees, so no statistic of a single maze can separate them. Disagreement "
                    + "with the recorded generator is reported, not hidden: an eroded or "
                    + "crossbred maze legitimately no longer looks like its author. "
                    + "Rate-limited against the 'mazeSolve' budget.")
    @PerKeyRateLimit("mazeSolve")
    public ResponseEntity<FingerprintService.Identification> fingerprint(@PathVariable UUID id) {
        var identification = fingerprints.identify(id);
        return identification == null
                ? ResponseEntity.notFound().build() : ResponseEntity.ok(identification);
    }

    /**
     * ADR-007 idea 2 — the Complexity Lab. A sweep generates several mazes to count their
     * construction work, so it shares the {@code mazeGenerate} budget; sizes and point count
     * are capped by the service and results are cached per input.
     */
    @GetMapping("/complexity")
    @Operation(summary = "Measure a generator's empirical growth curve and report its big-O with an R².",
            description = "Runs the generator across a capped sweep of sizes, fits the recorded "
                    + "work against candidate growth curves, and returns the winner with the "
                    + "measured points behind it. Counters are fitted, never wall-clock: timings "
                    + "measure the machine, whereas cell counts are deterministic for a given "
                    + "(generator, size, seed) so any fit reproduces exactly. A low R² is "
                    + "reported rather than hidden — it means the label is not trustworthy. "
                    + "Rate-limited against the 'mazeGenerate' budget.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<ComplexityLabService.Fit> complexity(
            @RequestParam String generator,
            @RequestParam(required = false) String metric,
            @RequestParam(required = false) Long seed) {
        var fit = complexity.fit(generator, metric, seed);
        return fit == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(fit);
    }

    @GetMapping("/complexity/metrics")
    @Operation(summary = "Which metrics the Complexity Lab can fit.")
    public List<String> complexityMetrics() {
        return complexity.metrics();
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

    /**
     * ADR-007 idea 3 — the hardest route. Longest-simple-path is NP-hard, so the search is
     * bounded by a visit budget rather than by maze size (measured 40-105 ms from 15x15 to
     * 512x512) and shares the {@code mazeSolve} budget.
     */
    @GetMapping("/maze/{id}/hardest-route")
    @Operation(summary = "The longest route from start to goal that never revisits a cell.",
            description = "Reports the shortest route, the hardest route and the detour between "
                    + "them. On a perfect maze those are the SAME number and the response says "
                    + "so: a tree has exactly one simple path between two cells, so there is "
                    + "nothing to choose. The gap only opens once the maze has loops — braid it, "
                    + "erode it with Bring to life, or use the dungeon generator, and the "
                    + "hardest route runs several times the shortest. Finding the true longest "
                    + "simple path is NP-hard, so a result may be a proven optimum or an "
                    + "honestly-labelled lower bound; it is a real walk either way. Computed on "
                    + "the maze's current snapshot, so a living maze answers differently as it "
                    + "erodes. Rate-limited against the 'mazeSolve' budget.")
    @PerKeyRateLimit("mazeSolve")
    public ResponseEntity<HardestRouteService.HardestRoute> hardestRoute(@PathVariable UUID id) {
        var route = hardestRoutes.forMaze(id);
        return route == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(route);
    }

    /**
     * ADR-007 idea 6 — the distance field, as a heat map. One breadth-first sweep, so this is
     * the cheapest analytical endpoint here; it shares the {@code mazeSolve} budget anyway
     * because the payload is the expensive part.
     */
    @GetMapping("/maze/{id}/distance-field")
    @Operation(summary = "Every cell's distance from the goal (or the start), for a heat map.",
            description = "Makes the breadth-first field visible, which is the quickest "
                    + "explanation of why a maze feels the way it does: long smooth gradients "
                    + "are corridors, tight rings of colour are a chokepoint, and an abrupt "
                    + "boundary between distant and near cells is a wall doing a lot of work. "
                    + "Unreachable cells report -1 rather than being omitted — a dungeon's rock "
                    + "is most of the grid and pretending otherwise would misdraw it. Refused "
                    + "with 400 above daedalus.topography.max-field-cells, because the sweep "
                    + "stays linear but the JSON does not. Rate-limited against 'mazeSolve'.")
    @PerKeyRateLimit("mazeSolve")
    public ResponseEntity<TopographyService.DistanceField> distanceField(
            @PathVariable UUID id,
            @RequestParam(required = false, defaultValue = "GOAL") TopographyService.Origin from) {
        var field = topography.fieldFor(id, from);
        return field == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(field);
    }

    /**
     * ADR-007 idea 5 — k-center sanctuary placement. {@code k} breadth-first sweeps for the
     * greedy plus {@code k} more to locate the worst-served cell, so it shares {@code mazeSolve}.
     */
    @GetMapping("/maze/{id}/sanctuaries")
    @Operation(summary = "Where to put k safe points so the worst-off cell is as close as possible.",
            description = "The metric k-center problem, which is NP-hard, solved by "
                    + "farthest-first greedy — a 2-approximation, and the best guarantee any "
                    + "polynomial algorithm can offer unless P = NP. The response reports the "
                    + "covering radius (the walk from the loneliest cell to its nearest "
                    + "sanctuary), that cell itself, and how many cells are actually served, so "
                    + "a placement that covers only part of a fragmented maze cannot hide behind "
                    + "a shrinking radius. k is clamped to 1..16. Rate-limited against "
                    + "'mazeSolve'.")
    @PerKeyRateLimit("mazeSolve")
    public ResponseEntity<TopographyService.Sanctuaries> sanctuaries(
            @PathVariable UUID id,
            @RequestParam(required = false) Integer k) {
        var placement = topography.sanctuariesFor(id, k);
        return placement == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(placement);
    }

    /**
     * ADR-007 ideas 10 and 7 — the tournament, and the adversarial seed that falls out of it.
     * Cost is mazes x solvers, both capped, and cached per request shape; shares the
     * {@code mazeGenerate} budget because a run generates every maze in the sample.
     */
    @GetMapping("/tournament")
    @Operation(summary = "Rank every solver over a sample of mazes, with intervals rather than one race.",
            description = "Reports each solver's mean work with a Student-t 95% interval, its "
                    + "median and spread, how many mazes it won, how often it found a shortest "
                    + "route, and which adjacent pairs are statistically INDISTINGUISHABLE. The "
                    + "last one is the point: measured, BFS, Dial and Dijkstra tie because all "
                    + "three explore essentially every cell, and reporting them as 1st, 2nd and "
                    + "3rd would be inventing a ranking out of noise. Whether a tournament beats "
                    + "a single race depends on the maze — on perfect mazes one solver won 30 of "
                    + "30, while on braided mazes the winner split five ways — so the response "
                    + "says which situation you are in. A solver that spends its node budget is "
                    + "excluded after three refusals and reported, rather than being averaged "
                    + "over the mazes it happened to survive. Rate-limited against 'mazeGenerate'.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<TournamentService.Tournament> tournament(
            @RequestParam(required = false, defaultValue = "recursive-backtracker") String generator,
            @RequestParam(required = false) Integer size,
            @RequestParam(required = false) Integer mazes,
            @RequestParam(required = false) Double braid,
            @RequestParam(required = false) Long seed) {
        var result = tournaments.run(generator, size, mazes, braid, seed);
        return result == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(result);
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
