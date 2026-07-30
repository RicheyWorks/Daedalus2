// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.api.dto.Hotspot;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.MazeMetadata;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.MazeGeneratedEvent;
import com.daedalus.theory.MazeMetrics;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.UUID;


/**
 * Orchestrates maze generation. Looks up the generator from the registry, runs it,
 * publishes a {@link MazeGeneratedEvent} so plugins can react, and caches the result.
 */
@Service
public class MazeGenerationService {

    private final GeneratorRegistry registry;
    private final ApplicationEventPublisher events;
    private final MeterRegistry meters;
    private final Cache<UUID, Cached> cache;

    /** Default bounds — see the four-arg constructor. */
    public MazeGenerationService(GeneratorRegistry registry,
                                  ApplicationEventPublisher events,
                                  MeterRegistry meters) {
        this(registry, events, meters, 5000, Duration.ofHours(2));
    }

    /**
     * @param cacheMaxSize maximum cached mazes; @param cacheTtl idle TTL per maze. The cache
     *        was previously an unbounded {@code ConcurrentHashMap} — at the base rate limit
     *        (30 generations/minute/caller) a long-running instance accumulated grids without
     *        end, the same slow-leak shape the rate-limiter buckets had before their Caffeine
     *        bound (BACKLOG, 2026-07-19). Eviction is safe by construction: {@code find}
     *        answering {@code null} is already the API's "unknown maze" path (404), and the
     *        idle TTL comfortably outlives any session actually being played. Bounds are
     *        configurable via {@code daedalus.maze.cache.*}.
     */
    @Autowired
    public MazeGenerationService(GeneratorRegistry registry,
                                  ApplicationEventPublisher events,
                                  MeterRegistry meters,
                                  @Value("${daedalus.maze.cache.max-size:5000}") long cacheMaxSize,
                                  @Value("${daedalus.maze.cache.idle-ttl:2h}") Duration cacheTtl) {
        this.registry = registry;
        this.events = events;
        this.meters = meters;
        this.cache = Caffeine.newBuilder()
                .maximumSize(cacheMaxSize)
                .expireAfterAccess(cacheTtl)
                .build();
    }

    /** @param hotspots the weighted cells applied to this maze, or {@code null} for uniform cost */
    public record Cached(MazeMetadata metadata, MazeGrid grid, MazeStats stats,
                         java.util.List<Hotspot> hotspots) {
        /** Uniform-cost shape, kept for source compatibility. */
        public Cached(MazeMetadata metadata, MazeGrid grid, MazeStats stats) {
            this(metadata, grid, stats, null);
        }
    }

    /** Uniform-cost generation — the pre-hotspot contract. */
    public Cached generate(String generatorId, int rows, int cols, long seed) {
        return generate(generatorId, rows, cols, seed, null);
    }

    /**
     * @param hotspots cells whose traversal cost is raised (validated for range upstream;
     *                 bounds against this maze checked here — an out-of-range hotspot is a
     *                 caller error, answered 400 by {@code ApiExceptionHandler}). A non-empty
     *                 list makes the cached grid a {@link WeightedMazeGrid}, which the
     *                 weight-aware solvers (Dijkstra, A*, Dial) consult on every relaxation —
     *                 the routing visibly detours around expensive cells wherever the topology
     *                 offers a choice. This is what fired the weighted-shading trigger
     *                 recorded in ADR-004.
     */
    @CircuitBreaker(name = "generation", fallbackMethod = "fallback")
    public Cached generate(String generatorId, int rows, int cols, long seed,
                           java.util.List<Hotspot> hotspots) {
        MazeGenerator gen = registry.require(generatorId);
        Timer timer = meters.timer("daedalus.generate", "algo", generatorId);
        MazeStats stats = new MazeStats();
        MazeGrid grid = timer.record(() -> gen.generate(rows, cols, seed, stats));
        if (grid == null) {
            // Timer.record(Supplier) is @Nullable; a generator returning null
            // is a contract violation worth failing loudly on.
            throw new IllegalStateException("generator returned null grid: " + generatorId);
        }

        // Start/goal at the maze's two farthest-apart carved cells — never at fixed corners.
        // Corners are safe for spanning-tree generators (every cell is carved) and silently
        // wrong for sparse ones: a dungeon's corners are solid rock, so the served maze was
        // unsolvable and a play session opened inside a wall. Extremes placement is
        // deterministic (row-major tie-break), seeds from the largest component, and gives
        // perfect mazes their maximum-challenge route for free. Same corner assumption the
        // 07-19 audit removed from `theory`, one layer up; pinned by
        // MazeGenerationStartGoalTest.
        java.util.List<Hotspot> applied = null;
        if (hotspots != null && !hotspots.isEmpty()) {
            WeightedMazeGrid weighted = new WeightedMazeGrid(grid);
            for (Hotspot h : hotspots) {
                if (h.row() >= rows || h.col() >= cols) {
                    throw new IllegalArgumentException("hotspot (" + h.row() + "," + h.col()
                            + ") is outside a " + rows + "x" + cols + " maze");
                }
                weighted.setWeight(new Point(h.row(), h.col()), h.cost());
            }
            grid = weighted;
            applied = java.util.List.copyOf(hotspots);
        }
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        MazeMetadata meta = MazeMetadata.of(rows, cols, seed, generatorId,
                grid.start(), grid.goal());

        Cached cached = new Cached(meta, grid, stats, applied);
        cache.put(meta.id(), cached);
        events.publishEvent(new MazeGeneratedEvent(this, meta, grid, stats));
        return cached;
    }

    public Cached find(UUID id) { return cache.getIfPresent(id); }

    @SuppressWarnings("unused")
    private Cached fallback(String generatorId, int rows, int cols, long seed,
                            java.util.List<Hotspot> hotspots, Throwable t) {
        // A caller error is not a generator failure — rethrow so it answers 400, not a
        // silently different maze.
        if (t instanceof IllegalArgumentException iae) {
            throw iae;
        }
        // Minimal recovery: deterministic baseline using BinaryTree (always succeeds).
        return generate("binary-tree", rows, cols, seed, hotspots);
    }
}
