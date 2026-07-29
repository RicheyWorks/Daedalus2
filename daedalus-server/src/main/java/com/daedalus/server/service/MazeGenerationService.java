// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.MazeMetadata;
import com.daedalus.model.MazeStats;
import com.daedalus.plugin.events.MazeGeneratedEvent;
import com.daedalus.theory.MazeMetrics;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

/**
 * Orchestrates maze generation. Looks up the generator from the registry, runs it,
 * publishes a {@link MazeGeneratedEvent} so plugins can react, and caches the result.
 */
@Service
public class MazeGenerationService {

    private final GeneratorRegistry registry;
    private final ApplicationEventPublisher events;
    private final MeterRegistry meters;
    private final ConcurrentMap<UUID, Cached> cache = new ConcurrentHashMap<>();

    public MazeGenerationService(GeneratorRegistry registry,
                                  ApplicationEventPublisher events,
                                  MeterRegistry meters) {
        this.registry = registry;
        this.events = events;
        this.meters = meters;
    }

    public record Cached(MazeMetadata metadata, MazeGrid grid, MazeStats stats) {}

    @CircuitBreaker(name = "generation", fallbackMethod = "fallback")
    public Cached generate(String generatorId, int rows, int cols, long seed) {
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
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        MazeMetadata meta = MazeMetadata.of(rows, cols, seed, generatorId,
                grid.start(), grid.goal());

        Cached cached = new Cached(meta, grid, stats);
        cache.put(meta.id(), cached);
        events.publishEvent(new MazeGeneratedEvent(this, meta, grid, stats));
        return cached;
    }

    public Cached find(UUID id) { return cache.get(id); }

    @SuppressWarnings("unused")
    private Cached fallback(String generatorId, int rows, int cols, long seed, Throwable t) {
        // Minimal recovery: deterministic baseline using BinaryTree (always succeeds).
        return generate("binary-tree", rows, cols, seed);
    }
}
