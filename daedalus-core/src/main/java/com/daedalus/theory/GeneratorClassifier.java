// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeStats;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Identifies which algorithm produced an unlabelled maze, from its structure alone
 * (ADR-007 idea 4).
 *
 * <p>Nearest-centroid over {@link MazeFingerprint} signatures. Each generator is sampled at
 * several seeds and sizes; the per-feature mean becomes its centroid and the per-feature
 * standard deviation across the whole training set becomes the scale. Classification is then
 * the nearest centroid under standardised (z-scored) Euclidean distance.
 *
 * <p><b>Why standardise.</b> The features have wildly different spreads — {@code edgeDensity}
 * varies by a couple of percent across generators while {@code horizontalBias} swings from 0.1
 * to 0.9. Raw Euclidean distance would let the widest feature decide every verdict on its own,
 * which is a classifier that has learned one thing and pretends to know eight.
 *
 * <p><b>Nearest centroid, deliberately.</b> It is the simplest thing that can work, it trains in
 * milliseconds, it needs no dependencies in a framework-free module, and — most usefully — it
 * is interpretable: a misclassification can be read off as "these two generators genuinely
 * produce the same texture", which is a fact about the algorithms rather than an artefact of an
 * opaque model. Accuracy is measured on held-out seeds, never on the training set.
 */
public final class GeneratorClassifier {

    /** One generator's learned centre in feature space. */
    public record Centroid(String generatorId, double[] mean) {}

    /**
     * A verdict.
     *
     * @param generatorId  the nearest centroid's generator
     * @param distance     standardised distance to it — smaller is a closer match
     * @param confidence   how much closer the winner is than the runner-up, in {@code [0, 1]};
     *                     near zero means two generators produce near-identical texture and the
     *                     label is close to a coin flip, which is worth saying out loud
     * @param runnerUp     the second-nearest generator, or {@code null} if only one is known
     */
    public record Verdict(String generatorId, double distance, double confidence,
                          String runnerUp) {}

    private final List<Centroid> centroids;
    private final double[] scale;

    private GeneratorClassifier(List<Centroid> centroids, double[] scale) {
        this.centroids = List.copyOf(centroids);
        this.scale = scale.clone();
    }

    /** The generators this classifier knows, in training order. */
    public List<String> knownGenerators() {
        return centroids.stream().map(Centroid::generatorId).toList();
    }

    /**
     * Train on the given generators.
     *
     * @param generators what to learn
     * @param sizes      square edge lengths to sample at — several, so the signature is forced
     *                   to be scale-free rather than memorising one size
     * @param seeds      how many seeds per size; more is steadier, and training stays cheap
     */
    public static GeneratorClassifier train(List<MazeGenerator> generators, int[] sizes,
                                            int seeds) {
        Map<String, List<double[]>> samples = new LinkedHashMap<>();
        List<double[]> all = new ArrayList<>();

        for (MazeGenerator generator : generators) {
            List<double[]> mine = new ArrayList<>();
            for (int size : sizes) {
                for (int s = 0; s < seeds; s++) {
                    MazeGrid grid = generator.generate(size, size, trainingSeed(s), new MazeStats());
                    double[] v = MazeFingerprint.of(grid).vector();
                    mine.add(v);
                    all.add(v);
                }
            }
            samples.put(generator.id(), mine);
        }

        int dims = all.get(0).length;
        double[] scale = new double[dims];
        for (int d = 0; d < dims; d++) {
            double mean = 0;
            for (double[] v : all) {
                mean += v[d];
            }
            mean /= all.size();
            double variance = 0;
            for (double[] v : all) {
                variance += (v[d] - mean) * (v[d] - mean);
            }
            // A feature that never varies carries no information; guard against dividing by it.
            scale[d] = Math.max(1e-9, Math.sqrt(variance / all.size()));
        }

        List<Centroid> centroids = new ArrayList<>();
        samples.forEach((id, vectors) -> {
            double[] mean = new double[dims];
            for (double[] v : vectors) {
                for (int d = 0; d < dims; d++) {
                    mean[d] += v[d];
                }
            }
            for (int d = 0; d < dims; d++) {
                mean[d] /= vectors.size();
            }
            centroids.add(new Centroid(id, mean));
        });
        return new GeneratorClassifier(centroids, scale);
    }

    /** Training seeds are fixed so a classifier is reproducible run to run. */
    private static long trainingSeed(int index) {
        return 1000L + index * 7919L;
    }

    /** Which generator most likely produced this maze. */
    public Verdict classify(MazeGrid maze) {
        double[] v = MazeFingerprint.of(maze).vector();
        List<double[]> ranked = new ArrayList<>();
        for (int i = 0; i < centroids.size(); i++) {
            ranked.add(new double[] {i, distance(v, centroids.get(i).mean())});
        }
        ranked.sort(Comparator.comparingDouble(a -> a[1]));

        Centroid best = centroids.get((int) ranked.get(0)[0]);
        double bestDistance = ranked.get(0)[1];
        if (ranked.size() == 1) {
            return new Verdict(best.generatorId(), round(bestDistance), 1.0, null);
        }
        Centroid second = centroids.get((int) ranked.get(1)[0]);
        double secondDistance = ranked.get(1)[1];
        // Margin as a share of the runner-up's distance: 0 means a tie, 1 means the winner sits
        // exactly on the sample while the alternative is far away.
        double confidence = secondDistance <= 0 ? 0
                : Math.max(0, Math.min(1, (secondDistance - bestDistance) / secondDistance));
        return new Verdict(best.generatorId(), round(bestDistance), round(confidence),
                second.generatorId());
    }

    private double distance(double[] a, double[] b) {
        double sum = 0;
        for (int d = 0; d < a.length; d++) {
            double delta = (a[d] - b[d]) / scale[d];
            sum += delta * delta;
        }
        return Math.sqrt(sum);
    }

    private static double round(double v) {
        return Math.round(v * 1000.0) / 1000.0;
    }
}
