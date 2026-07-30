// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.theory.GeneratorClassifier;
import com.daedalus.theory.MazeFingerprint;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.UUID;
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
 * <p><b>Trained lazily and exactly once.</b> Training samples every registered generator at
 * several sizes and seeds, which costs real work; doing it in a constructor would tax every
 * application start, including tests that never ask for a fingerprint. The reference is
 * published atomically, so a race at worst trains twice and keeps one — cheaper than holding a
 * lock across generation work.
 */
@Service
public class FingerprintService {

    private static final Logger log = LoggerFactory.getLogger(FingerprintService.class);

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
    private final AtomicReference<GeneratorClassifier> classifier = new AtomicReference<>();

    public FingerprintService(MazeGenerationService gen, GeneratorRegistry registry,
                              @Value("${daedalus.fingerprint.train-seeds:4}") int trainSeeds) {
        this.gen = gen;
        this.registry = registry;
        this.trainSeeds = Math.max(1, trainSeeds);
    }

    private GeneratorClassifier classifier() {
        GeneratorClassifier existing = classifier.get();
        if (existing != null) {
            return existing;
        }
        long start = System.nanoTime();
        GeneratorClassifier trained = GeneratorClassifier.train(
                registry.all().stream().toList(), new int[] {21, 31, 41}, trainSeeds);
        classifier.compareAndSet(null, trained);
        log.info("generator classifier trained on {} generators in {} ms",
                trained.knownGenerators().size(), (System.nanoTime() - start) / 1_000_000);
        return classifier.get();
    }

    /**
     * Fingerprint a stored maze and name its likely author.
     *
     * @return {@code null} when the maze is unknown (the controller answers 404)
     */
    public Identification identify(UUID mazeId) {
        var cached = gen.find(mazeId);
        if (cached == null) {
            return null;
        }
        var signature = MazeFingerprint.of(cached.grid());
        var verdict = classifier().classify(cached.grid());
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
