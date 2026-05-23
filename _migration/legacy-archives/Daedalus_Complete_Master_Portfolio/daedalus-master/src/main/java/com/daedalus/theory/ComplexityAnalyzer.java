package com.daedalus.theory;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeStats;

import java.util.*;

/**
 * Analyzes empirical complexity of generators and solvers.
 * Uses MazeStats to estimate time/space behavior.
 */
public class ComplexityAnalyzer {

    public record ComplexityResult(
            String algorithmId,
            double avgTimeMs,
            double avgVisited,
            double avgFrontier,
            String estimatedBigO
    ) {}

    public List<ComplexityResult> analyzeGenerators(List<MazeGenerator> generators, int[] sizes) {
        List<ComplexityResult> results = new ArrayList<>();

        for (MazeGenerator gen : generators) {
            List<Long> times = new ArrayList<>();
            List<Long> visited = new ArrayList<>();
            List<Long> frontier = new ArrayList<>();

            for (int size : sizes) {
                MazeStats stats = new MazeStats();
                long start = System.nanoTime();
                gen.generate(size, size, 42, stats);
                long end = System.nanoTime();

                times.add((end - start) / 1_000_000);
                visited.add(stats.cellsVisited());
                frontier.add(stats.maxFrontierSize());
            }

            double avgTime = times.stream().mapToLong(Long::longValue).average().orElse(0);
            double avgVisited = visited.stream().mapToLong(Long::longValue).average().orElse(0);
            double avgFrontier = frontier.stream().mapToLong(Long::longValue).average().orElse(0);

            String bigO = estimateBigO(avgTime, sizes);

            results.add(new ComplexityResult(gen.id(), avgTime, avgVisited, avgFrontier, bigO));
        }

        return results;
    }

    private String estimateBigO(double avgTime, int[] sizes) {
        if (avgTime < 50) return "O(n)";
        if (avgTime < 200) return "O(n log n)";
        return "O(n²) or worse";
    }
}