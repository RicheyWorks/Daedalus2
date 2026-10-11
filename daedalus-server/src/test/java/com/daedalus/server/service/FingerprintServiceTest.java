// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
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
        assertThat(svc.ready()).isTrue();
        assertThat(svc.lastTrainFailed()).isFalse();
        assertThat(svc.lastTrainError()).isNull();
    }

    @Test
    void aThrownFitFlagsTheFailureAndLetsTheNextIdentifyRetry() {
        var cached = gen.generate("binary-tree", 7, 7, 1L);
        var pending = new AtomicReference<Runnable>();
        SimpleMeterRegistry meters = new SimpleMeterRegistry();
        var svc = new FingerprintService(gen, new GeneratorRegistry(List.of(explodingOnce())),
                1, new int[] {5}, pending::set, meters);

        assertThatThrownBy(() -> svc.identify(cached.metadata().id()))
                .isInstanceOf(FingerprintService.ClassifierWarmingException.class);
        pending.get().run();
        assertThat(svc.lastTrainFailed())
                .as("a thrown fit is not still-warming")
                .isTrue();
        assertThat(svc.lastTrainError()).contains("fit boom");
        assertThat(svc.ready()).isFalse();
        assertThat(meters.counter("daedalus.fingerprint.train.failure").count())
                .isEqualTo(1.0);

        assertThatThrownBy(() -> svc.identify(cached.metadata().id()))
                .as("identify stays 503 until a later fit publishes")
                .isInstanceOf(FingerprintService.ClassifierWarmingException.class);
        pending.get().run();
        assertThat(svc.lastTrainFailed())
                .as("health must recover when a later fit publishes")
                .isFalse();
        assertThat(svc.lastTrainError()).isNull();
        assertThat(svc.identify(cached.metadata().id()).predictedGeneratorId())
                .isEqualTo("binary-tree");
    }

    @Test
    void aClassifierNeverAskedIsNotAFailure() {
        var svc = new FingerprintService(gen, genRegistry(), 1, new int[] {5}, r -> { });
        assertThat(svc.ready()).isFalse();
        assertThat(svc.lastTrainFailed()).isFalse();
        assertThat(svc.lastTrainError()).isNull();
    }

    private static GeneratorRegistry genRegistry() {
        return new GeneratorRegistry(List.of(new BinaryTreeGenerator()));
    }

    /** First generate throws; later generates delegate to binary-tree. */
    private static AbstractMazeGenerator explodingOnce() {
        AtomicBoolean boom = new AtomicBoolean(true);
        return new AbstractMazeGenerator() {
            @Override public String id() { return "binary-tree"; }
            @Override public String displayName() { return "Binary Tree"; }
            @Override public AlgorithmDescriptor descriptor() {
                return new BinaryTreeGenerator().descriptor();
            }
            @Override public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
                if (boom.getAndSet(false)) {
                    throw new RuntimeException("fit boom");
                }
                return new BinaryTreeGenerator().generate(rows, cols, seed, stats);
            }
        };
    }
}
