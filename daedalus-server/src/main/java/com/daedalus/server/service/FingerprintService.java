// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.theory.GeneratorClassifier;
import com.daedalus.theory.MazeFingerprint;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.UUID;
import java.util.concurrent.Executor;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Guess which algorithm produced a maze, from its structure alone (ADR-007 idea 4).
 *
 * <p>Wraps {@link GeneratorClassifier}: train once, lazily, on the registry's own generators,
 * then classify any stored maze. Because the answer is derived purely from the tile grid, it
 * works on mazes whose provenance the server does not know — a crossbred child, an eroded
 * living maze, or a maze whose recorded {@code generatorId} says nothing about its current
 * shape.
 *
 * <p><b>Trained lazily, off the request thread, and exactly once.</b> Training samples every
 * registered generator at several sizes and seeds. Doing it in a constructor would tax every
 * start, including tests that never ask. Doing it on the first GET used to pin a Tomcat
 * worker for the whole fit (~40s) and, on a race, train once per concurrent first hit. A
 * dedicated thread trains; {@link #identify} answers {@link ClassifierWarmingException}
 * (503) until the reference is published. A thrown fit stays a 503 on the next
 * identify — that must not look like "still warming" in a warn-only log. The miss
 * increments {@code daedalus.fingerprint.train.failure} and health reports it
 * while staying UP.
 */
@Service
public class FingerprintService {

    private static final Logger log = LoggerFactory.getLogger(FingerprintService.class);
    private static final int[] TRAIN_SIZES = {21, 31, 41};

    /**
     * The classifier is still fitting. Retry — do not hold a request thread across generation.
     */
    public static final class ClassifierWarmingException extends RuntimeException {
        public ClassifierWarmingException() {
            super("The generator classifier is still training. Retry shortly.");
        }
    }

    /**
     * A maze's signature and the classifier's verdict.
     *
     * @param recordedGeneratorId what the server has on file, which may be {@code crossbreed}
     *                            or simply out of date after erosion
     * @param agrees              whether the structural guess matches the record — {@code false}
     *                            is interesting rather than wrong (see {@code note})
     */
    public record Identification(UUID mazeId, MazeFingerprint.Signature signature,
                                 String predictedGeneratorId, double confidence,
                                 String runnerUp, String recordedGeneratorId, boolean agrees,
                                 String note) {}

    private final MazeGenerationService gen;
    private final GeneratorRegistry registry;
    private final int trainSeeds;
    private final int[] trainSizes;
    private final Executor trainer;
    private final Counter trainFailure;
    private final AtomicReference<GeneratorClassifier> classifier = new AtomicReference<>();
    private final AtomicBoolean training = new AtomicBoolean();
    private final AtomicBoolean lastTrainFailed = new AtomicBoolean();
    private final AtomicReference<String> lastTrainError = new AtomicReference<>();

    @Autowired
    public FingerprintService(MazeGenerationService gen, GeneratorRegistry registry,
                              @Value("${daedalus.fingerprint.train-seeds:4}") int trainSeeds,
                              MeterRegistry meters) {
        this(gen, registry, trainSeeds, TRAIN_SIZES, dedicatedTrainer(), meters);
    }

    /** Test seam — a stalling executor pins single-flight without a 40s fit. */
    FingerprintService(MazeGenerationService gen, GeneratorRegistry registry,
                       int trainSeeds, int[] trainSizes, Executor trainer) {
        this(gen, registry, trainSeeds, trainSizes, trainer, new SimpleMeterRegistry());
    }

    FingerprintService(MazeGenerationService gen, GeneratorRegistry registry,
                       int trainSeeds, int[] trainSizes, Executor trainer, MeterRegistry meters) {
        this.gen = gen;
        this.registry = registry;
        this.trainSeeds = Math.max(1, trainSeeds);
        this.trainSizes = trainSizes.clone();
        this.trainer = trainer;
        this.trainFailure = Counter.builder("daedalus.fingerprint.train.failure")
                .description("Generator-classifier fits that threw")
                .register(meters);
    }

    private static ExecutorService dedicatedTrainer() {
        return Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r, "fingerprint-trainer");
            t.setDaemon(true);
            return t;
        });
    }

    /** True after the classifier has published a fit. */
    public boolean ready() {
        return classifier.get() != null;
    }

    /** True after a thrown fit until a later fit publishes. */
    public boolean lastTrainFailed() {
        return lastTrainFailed.get();
    }

    /** Last fit exception, or null when the last fit succeeded or never ran. */
    public String lastTrainError() {
        return lastTrainError.get();
    }

    @PreDestroy
    void shutdown() {
        if (trainer instanceof ExecutorService es) {
            es.shutdownNow();
        }
    }

    private void requestTrain() {
        if (classifier.get() != null || !training.compareAndSet(false, true)) {
            return;
        }
        trainer.execute(() -> {
            try {
                long start = System.nanoTime();
                GeneratorClassifier trained = GeneratorClassifier.train(
                        registry.all().stream().toList(), trainSizes, trainSeeds);
                classifier.set(trained);
                lastTrainFailed.set(false);
                lastTrainError.set(null);
                log.info("generator classifier trained on {} generators in {} ms",
                        trained.knownGenerators().size(),
                        (System.nanoTime() - start) / 1_000_000);
            } catch (RuntimeException e) {
                // Identify stays 503 until a fit publishes. That is not "still
                // warming" — surface it, do not leave the miss in a warn-only log.
                lastTrainFailed.set(true);
                lastTrainError.set(e.toString());
                trainFailure.increment();
                log.warn("generator classifier training failed; the next identify will retry", e);
            } finally {
                training.set(false);
            }
        });
    }

    /**
     * Fingerprint a stored maze and name its likely author.
     *
     * @return {@code null} when the maze is unknown (the controller answers 404)
     * @throws ClassifierWarmingException when the fit has been kicked off but is not ready
     */
    public Identification identify(UUID mazeId) {
        var cached = gen.find(mazeId);
        if (cached == null) {
            return null;
        }
        GeneratorClassifier ready = classifier.get();
        if (ready == null) {
            requestTrain();
            throw new ClassifierWarmingException();
        }
        var signature = MazeFingerprint.of(cached.grid());
        var verdict = ready.classify(cached.grid());
        String recorded = cached.metadata().generatorId();
        boolean agrees = verdict.generatorId().equals(recorded);
        return new Identification(mazeId, signature, verdict.generatorId(), verdict.confidence(),
                verdict.runnerUp(), recorded, agrees, noteFor(verdict, recorded, agrees));
    }

    /**
     * Explain the verdict, including the cases where disagreeing with the record is the more
     * informative answer.
     */
    private static String noteFor(GeneratorClassifier.Verdict verdict, String recorded,
                                  boolean agrees) {
        if (agrees) {
            return verdict.confidence() < 0.15
                    ? "matches the record, but only just — " + verdict.runnerUp()
                      + " produces near-identical texture at this size."
                    : "structure alone identifies the generator on record.";
        }
        if ("crossbreed".equals(recorded)) {
            return "a crossbred maze has no single author; the signature reports whichever "
                    + "parent's texture dominates, which is " + verdict.generatorId() + " here.";
        }
        return "structure says " + verdict.generatorId() + " though the record says " + recorded
                + ". Either the maze has been altered since generation (erosion and braiding "
                + "both rewrite texture), or the two algorithms genuinely produce the same "
                + "shape — Aldous-Broder and Wilson's, for instance, sample the same "
                + "distribution and cannot be told apart by any structural statistic.";
    }
}
