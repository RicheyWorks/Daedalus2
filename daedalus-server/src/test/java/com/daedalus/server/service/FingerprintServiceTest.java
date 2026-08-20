// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The classifier fit must not run on the caller, and two first Identifies must not
 * both train. A stalling executor is the seam — a 21/31/41 fit would hide the race
 * behind forty seconds of generation.
 */
class FingerprintServiceTest {

    private final MazeGenerationService gen = new MazeGenerationService(
            new GeneratorRegistry(List.of(new BinaryTreeGenerator())),
            event -> { }, new SimpleMeterRegistry());

    @Test
    void anUnknownMazeDoesNotStartATrain() {
        var submitted = new AtomicInteger();
        var svc = new FingerprintService(gen, genRegistry(), 1, new int[] {5},
                r -> submitted.incrementAndGet());
        assertThat(svc.identify(UUID.randomUUID())).isNull();
        assertThat(submitted.get()).isZero();
    }

    @Test
    void theFirstIdentifyStartsOneTrainAndAnswersWarmingUntilItPublishes() {
        var cached = gen.generate("binary-tree", 7, 7, 1L);
        var pending = new AtomicReference<Runnable>();
        var submitted = new AtomicInteger();
        var svc = new FingerprintService(gen, genRegistry(), 1, new int[] {5}, r -> {
            submitted.incrementAndGet();
            pending.set(r);
        });

        assertThatThrownBy(() -> svc.identify(cached.metadata().id()))
                .isInstanceOf(FingerprintService.ClassifierWarmingException.class);
        assertThatThrownBy(() -> svc.identify(cached.metadata().id()))
                .as("a second first-hit must join the same train, not start another")
                .isInstanceOf(FingerprintService.ClassifierWarmingException.class);
        assertThat(submitted.get()).isEqualTo(1);

        pending.get().run();
        var id = svc.identify(cached.metadata().id());
        assertThat(id).isNotNull();
        assertThat(id.predictedGeneratorId()).isEqualTo("binary-tree");
        assertThat(id.mazeId()).isEqualTo(cached.metadata().id());
    }

    private static GeneratorRegistry genRegistry() {
        return new GeneratorRegistry(List.of(new BinaryTreeGenerator()));
    }
}
