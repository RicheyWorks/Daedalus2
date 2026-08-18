// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.api.dto.Hotspot;
import com.daedalus.engine.Braider;
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
import com.github.benmanes.caffeine.cache.Ticker;
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
        this(registry, events, meters, cacheMaxSize, cacheTtl, Ticker.systemTicker());
    }

    /**
     * Ticker seam, the same one {@code GameSessionService} carries and for the same reason. The
     * idle TTL is a promise about the passage of time, and a test that cannot move time can only
     * assert that the builder was called: {@code BoundedStoresTest} pinned {@code maximumSize}
     * here — and reflectively, that every cache in the server declares one — while deleting
     * {@code expireAfterAccess} from this builder left the whole suite green. Size and idle are
     * separate bounds. A cache bounded only by size holds every maze anyone ever generated until
     * 5,000 more arrive, which on a quiet instance is indefinitely, and the eviction path that
     * both tickers and the campaign planner are written around would then never fire in practice.
     */
    MazeGenerationService(GeneratorRegistry registry,
                          ApplicationEventPublisher events,
                          MeterRegistry meters,
                          long cacheMaxSize,
                          Duration cacheTtl,
                          Ticker ticker) {
        this.registry = registry;
        this.events = events;
        this.meters = meters;
        this.cache = Caffeine.newBuilder()
                .maximumSize(cacheMaxSize)
                .expireAfterAccess(cacheTtl)
                .ticker(ticker)
                .build();
    }

    /**
     * @param hotspots the weighted cells applied to this maze, or {@code null} for uniform cost
     * @param braid    generate-time opening factor, or {@code null} when none was applied
     */
    public record Cached(MazeMetadata metadata, MazeGrid grid, MazeStats stats,
                         java.util.List<Hotspot> hotspots, Double braid) {
        /** Uniform-cost, unbraided — the pre-hotspot contract. */
        public Cached(MazeMetadata metadata, MazeGrid grid, MazeStats stats) {
            this(metadata, grid, stats, null, null);
        }

        /** Weighted, unbraided — the pre-braid-echo contract. */
        public Cached(MazeMetadata metadata, MazeGrid grid, MazeStats stats,
                      java.util.List<Hotspot> hotspots) {
            this(metadata, grid, stats, hotspots, null);
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
    public Cached generate(String generatorId, int rows, int cols, long seed,
                           java.util.List<Hotspot> hotspots) {
        return generate(generatorId, rows, cols, seed, hotspots, 0.0);
    }

    /**
     * @param braid fraction of dead ends to open after generation, clamped to
     *              {@code [0, 1]}. Zero is a no-op so existing callers keep a
     *              tree. Same {@code (grid, factor, seed)} as the tournament,
     *              then extremes are placed on the braided graph — otherwise
     *              start and goal would still be the tree's diameter.
     */
    @CircuitBreaker(name = "generation", fallbackMethod = "fallback")
    public Cached generate(String generatorId, int rows, int cols, long seed,
                           java.util.List<Hotspot> hotspots, double braid) {
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
        if (braid > 0) {
            Braider.braid(grid, braid, seed);
        }
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        MazeMetadata meta = MazeMetadata.of(rows, cols, seed, generatorId,
                grid.start(), grid.goal());

        Double recordedBraid = braid > 0 ? braid : null;
        Cached cached = new Cached(meta, grid, stats, applied, recordedBraid);
        cache.put(meta.id(), cached);
        events.publishEvent(new MazeGeneratedEvent(this, meta, grid, stats));
        return cached;
    }

    /**
     * Register a grid produced outside the generator pipeline — crossbred offspring
     * (ADR-006 idea #5) today, any future in-memory construction tomorrow. Runs the same
     * finishing steps as {@link #generate}: extremes start/goal placement, metadata,
     * cache entry, and the {@link MazeGeneratedEvent} plugins and the STOMP bridge expect,
     * so an adopted maze is indistinguishable from a generated one downstream.
     */
    public Cached adopt(MazeGrid grid, String generatorId, long seed) {
        return adopt(grid, generatorId, seed, null);
    }

    /**
     * @param hotspots parent weights to keep on an adopted child; {@code null} for uniform cost
     */
    public Cached adopt(MazeGrid grid, String generatorId, long seed,
                        java.util.List<Hotspot> hotspots) {
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        java.util.List<Hotspot> applied = null;
        if (hotspots != null && !hotspots.isEmpty()) {
            WeightedMazeGrid weighted = new WeightedMazeGrid(grid);
            for (Hotspot h : hotspots) {
                if (h.row() >= grid.rows() || h.col() >= grid.cols()) {
                    throw new IllegalArgumentException("hotspot (" + h.row() + "," + h.col()
                            + ") is outside a " + grid.rows() + "x" + grid.cols() + " maze");
                }
                weighted.setWeight(new Point(h.row(), h.col()), h.cost());
            }
            grid = weighted;
            applied = java.util.List.copyOf(hotspots);
        }
        MazeMetadata meta = MazeMetadata.of(grid.rows(), grid.cols(), seed, generatorId,
                grid.start(), grid.goal());
        Cached cached = new Cached(meta, grid, new MazeStats(), applied);
        cache.put(meta.id(), cached);
        events.publishEvent(new MazeGeneratedEvent(this, meta, grid, cached.stats()));
        return cached;
    }

    public Cached find(UUID id) { return cache.getIfPresent(id); }

    /**
     * Atomically swap a cached maze for a new snapshot — the living-maze tick's commit
     * point (ADR-006). Present-only by design: {@code computeIfPresent} never resurrects a
     * maze the cache already evicted, so a living run whose maze ages out stops on its next
     * tick instead of pinning the entry forever. Readers that fetched the old {@link Cached}
     * keep a consistent immutable snapshot; the next {@link #find} sees the new one.
     *
     * @return true if the maze was present and swapped; false if it is gone (evicted or
     *         never cached), which callers must treat as "stop mutating"
     */
    public boolean replace(UUID id, Cached updated) {
        return cache.asMap().computeIfPresent(id, (k, old) -> updated) != null;
    }

    @SuppressWarnings("unused")
    private Cached fallback(String generatorId, int rows, int cols, long seed,
                            java.util.List<Hotspot> hotspots, double braid, Throwable t) {
        // A caller error is not a generator failure — rethrow so it answers 400, not a
        // silently different maze.
        if (t instanceof IllegalArgumentException iae) {
            throw iae;
        }
        // Minimal recovery: deterministic baseline using BinaryTree (always succeeds).
        return generate("binary-tree", rows, cols, seed, hotspots, braid);
    }
}
