// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.*;

/**
 * Kraken Generator — Eden Growth Model (statistical physics / cluster growth).
 * Starts with a single random "seed" cell and repeatedly attaches a random unvisited
 * neighbor directly to the existing cluster. This is mathematically equivalent to
 * a random spanning tree grown by pure surface attachment.
 *
 * <p>Visual result: wildly organic, coral-like, heavily branched "tentacle" mazes with
 * chaotic natural texture. Extremely different aesthetic from everything else in your
 * collection (no long rivers like backtracker, no clean layers like BFS, no uniform
 * bushiness like Prim's/Kruskal).
 *
 * <p>Pirate flavor: the Kraken awakens and devours the grid one cell at a time.
 * Pure math + pure fun. Original to this project.
 */
public class KrakenGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "kraken"; }
    @Override public String displayName() { return "Kraken (Eden Growth)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(n) space",
                "Chaotic coral / tentacle texture — maximum organic branching",
                "Eden cluster growth model from statistical physics. The Kraken has arrived.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        // Seed the beast
        Point start = new Point(rng.nextInt(rows), rng.nextInt(cols));
        grid.cell(start).markVisited();
        stats.incVisited();

        // Frontier = all unvisited cells touching the current "kraken"
        List<Point> frontier = new ArrayList<>();
        addUnvisitedNeighbors(grid, start, frontier, rng);

        while (!frontier.isEmpty()) {
            stats.recordFrontier(frontier.size());

            // Randomly pick which part of the frontier gets eaten next
            int idx = rng.nextInt(frontier.size());
            Point candidate = frontier.remove(idx);

            if (grid.cell(candidate).isVisited()) continue;

            // Find every visited neighbor (there will be at least one)
            List<Point> visitedNbrs = getVisitedNeighbors(grid, candidate);

            if (!visitedNbrs.isEmpty()) {
                // Attach to a random living tentacle
                Point from = visitedNbrs.get(rng.nextInt(visitedNbrs.size()));
                grid.carve(from, candidate);               // exact same style as Aldous-Broder

                grid.cell(candidate).markVisited();
                stats.incVisited();

                // Expose any new flesh (new frontier cells)
                addUnvisitedNeighbors(grid, candidate, frontier, rng);
            }
        }

        grid.clearVisited();
        stats.finish(true);
        return grid;
    }

    private void addUnvisitedNeighbors(MazeGrid grid, Point p, List<Point> frontier, Random rng) {
        List<Point> nbrs = new ArrayList<>(grid.neighbors(p));
        Collections.shuffle(nbrs, rng);                    // extra organic randomness
        for (Point n : nbrs) {
            if (!grid.cell(n).isVisited() && !frontier.contains(n)) {
                frontier.add(n);
            }
        }
    }

    private List<Point> getVisitedNeighbors(MazeGrid grid, Point p) {
        List<Point> visited = new ArrayList<>();
        for (Point n : grid.neighbors(p)) {
            if (grid.cell(n).isVisited()) {
                visited.add(n);
            }
        }
        return visited;
    }
}
