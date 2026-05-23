// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationEventPublisher;

import java.lang.reflect.Method;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

/**
 * Covers the audit's #1 server fix: when {@code MazeGenerationService.generate(...)} hits its
 * Resilience4j fallback, the returned {@code Cached} must carry metadata whose
 * {@code generatorId()} reflects the algorithm that actually ran ("binary-tree"), not the
 * algorithm the caller originally requested.
 *
 * <p>The test bypasses Spring AOP (the {@code @CircuitBreaker} proxy) by exercising the
 * {@code fallback} method directly via reflection. That is sufficient to verify the recovery
 * contract; integration with Resilience4j itself is exercised by the framework's own tests.
 */
class MazeGenerationServiceFallbackTest {

    private MazeGenerationService newServiceWithBinaryTree() {
        // Real BinaryTreeGenerator → guaranteed to succeed regardless of seed/dimensions.
        GeneratorRegistry registry = new GeneratorRegistry(List.of(new BinaryTreeGenerator()));
        ApplicationEventPublisher events = mock(ApplicationEventPublisher.class);
        return new MazeGenerationService(registry, events, new SimpleMeterRegistry());
    }

    @Test
    void fallback_returnsCachedWithBinaryTreeMetadata_evenWhenRequestedIdDiffers() throws Exception {
        MazeGenerationService service = newServiceWithBinaryTree();

        // The audit's bug: the response used to report the *requested* generatorId ("astar")
        // even though the fallback actually produced a binary-tree maze. We verify that the
        // Cached returned by fallback() is the binary-tree one.
        Method fallback = MazeGenerationService.class
                .getDeclaredMethod("fallback", String.class, int.class, int.class, long.class, Throwable.class);
        fallback.setAccessible(true);

        MazeGenerationService.Cached cached =
                (MazeGenerationService.Cached) fallback.invoke(service,
                        "some-broken-generator", 5, 5, 42L, new RuntimeException("breaker open"));

        assertThat(cached).isNotNull();
        assertThat(cached.metadata().generatorId())
                .as("fallback must surface its actual algorithm, not the caller's requested id")
                .isEqualTo("binary-tree");
        assertThat(cached.metadata().rows()).isEqualTo(5);
        assertThat(cached.metadata().cols()).isEqualTo(5);
        assertThat(cached.metadata().seed()).isEqualTo(42L);
        assertThat(cached.grid()).isNotNull();
    }

    @Test
    void generate_normalPath_metadataMatchesRequestedId() {
        MazeGenerationService service = newServiceWithBinaryTree();

        MazeGenerationService.Cached cached = service.generate("binary-tree", 4, 4, 1L);

        assertThat(cached.metadata().generatorId()).isEqualTo("binary-tree");
        assertThat(cached.metadata().rows()).isEqualTo(4);
        assertThat(cached.metadata().cols()).isEqualTo(4);
    }

    /**
     * Sanity check on a hand-rolled stub generator — confirms that whatever id() the generator
     * exposes is the value that ends up in {@code Cached.metadata().generatorId()} on the happy
     * path. Combined with the fallback test above, this triangulates the audit's fix: the
     * controller now reads from {@code metadata().generatorId()} rather than from the request.
     */
    @Test
    void generate_writesGeneratorIdFromTheRunningGenerator() {
        MazeGenerator stub = new MazeGenerator() {
            @Override public String id() { return "stub"; }
            @Override public String displayName() { return "Stub"; }
            @Override public AlgorithmDescriptor descriptor() {
                return new AlgorithmDescriptor("stub", "Stub", "generator", "O(1)", "none", "test stub");
            }
            @Override public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
                MazeGrid g = new MazeGrid(rows, cols);
                stats.finish(true);
                return g;
            }
        };
        GeneratorRegistry registry = new GeneratorRegistry(List.of(stub));
        MazeGenerationService service = new MazeGenerationService(
                registry, mock(ApplicationEventPublisher.class), new SimpleMeterRegistry());

        MazeGenerationService.Cached cached = service.generate("stub", 3, 3, 7L);

        assertThat(cached.metadata().generatorId()).isEqualTo("stub");
    }
}
