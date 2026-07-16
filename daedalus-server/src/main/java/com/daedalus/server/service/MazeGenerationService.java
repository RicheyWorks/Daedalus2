// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.MazeMetadata;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.MazeGeneratedEvent;
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

        MazeMetadata meta = MazeMetadata.of(rows, cols, seed, generatorId,
                new Point(0, 0), new Point(rows - 1, cols - 1));
        grid.setStart(meta.start());
        grid.setGoal(meta.goal());

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
