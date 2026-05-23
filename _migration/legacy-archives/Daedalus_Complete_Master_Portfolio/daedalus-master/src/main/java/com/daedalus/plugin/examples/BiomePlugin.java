package com.daedalus.plugin.examples;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;
import com.daedalus.plugin.*;

import java.util.Random;

/**
 * Example plugin: Biome-themed generators.
 * Demonstrates how to extend Daedalus with custom generators.
 */
public class BiomePlugin extends AbstractPlugin {

    @Override
    public PluginManifest manifest() {
        return new PluginManifest(
            "biome-generators",
            "Biome Generators",
            "1.0.0",
            "Daedalus Team",
            "Adds forest, desert, and cave biome generators"
        );
    }

    @Override
    public void registerAlgorithms(PluginContext ctx) {
        ctx.generators().register(new ForestGenerator());
        ctx.generators().register(new DesertGenerator());
        ctx.generators().register(new CaveGenerator());
    }

    // ==================== CUSTOM GENERATORS ====================

    static class ForestGenerator extends AbstractMazeGenerator {
        @Override public String id() { return "forest"; }
        @Override public String displayName() { return "Forest Biome"; }

        @Override
        public AlgorithmDescriptor descriptor() {
            return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time",
                "Dense branching with many small clearings",
                "Generates forest-like mazes with organic branching"
            );
        }

        @Override
        public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
            Random rng = new Random(seed);
            MazeGrid grid = new MazeGrid(rows, cols);

            // Simple growing tree with high branching
            java.util.List<Point> active = new java.util.ArrayList<>();
            Point start = new Point(rng.nextInt(rows), rng.nextInt(cols));
            active.add(start);
            grid.cell(start).markVisited();
            stats.incVisited();

            while (!active.isEmpty()) {
                int idx = rng.nextInt(active.size());
                Point cur = active.get(idx);

                java.util.List<Direction> dirs = java.util.Arrays.asList(Direction.values());
                java.util.Collections.shuffle(dirs, rng);

                Point chosen = null;
                for (Direction d : dirs) {
                    Point n = cur.step(d);
                    if (grid.inBounds(n) && !grid.cell(n).isVisited()) {
                        grid.carve(grid.cell(cur), d);
                        grid.cell(n).markVisited();
                        stats.incVisited();
                        chosen = n;
                        break;
                    }
                }

                if (chosen == null) active.remove(idx);
                else active.add(chosen);
            }

            grid.clearVisited();
            stats.finish(true);
            return grid;
        }
    }

    static class DesertGenerator extends AbstractMazeGenerator {
        @Override public String id() { return "desert"; }
        @Override public String displayName() { return "Desert Dunes"; }

        @Override
        public AlgorithmDescriptor descriptor() {
            return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time",
                "Long straight passages with occasional dunes",
                "Creates desert-like mazes with long corridors"
            );
        }

        @Override
        public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
            Random rng = new Random(seed);
            MazeGrid grid = new MazeGrid(rows, cols);

            // Sidewinder-like with longer runs
            for (int r = 0; r < rows; r++) {
                java.util.List<Point> run = new java.util.ArrayList<>();
                for (int c = 0; c < cols; c++) {
                    Point p = new Point(r, c);
                    run.add(p);
                    boolean closeOut = (c == cols - 1) || rng.nextInt(4) == 0;
                    if (closeOut) {
                        Point member = run.get(rng.nextInt(run.size()));
                        if (r > 0) grid.carve(grid.cell(member), Direction.NORTH);
                        run.clear();
                    } else {
                        grid.carve(grid.cell(p), Direction.EAST);
                    }
                    stats.incVisited();
                }
            }
            stats.finish(true);
            return grid;
        }
    }

    static class CaveGenerator extends AbstractMazeGenerator {
        @Override public String id() { return "cave"; }
        @Override public String displayName() { return "Limestone Cave"; }

        @Override
        public AlgorithmDescriptor descriptor() {
            return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time",
                "Winding passages with occasional chambers",
                "Creates cave-like mazes using recursive backtracker"
            );
        }

        @Override
        public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
            return new RecursiveBacktrackerGenerator().generate(rows, cols, seed, stats);
        }
    }
}