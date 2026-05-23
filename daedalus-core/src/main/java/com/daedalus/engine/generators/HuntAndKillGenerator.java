// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.*;

/**
 * Hunt-and-Kill. Like recursive backtracker but instead of backtracking via stack,
 * it scans the grid linearly for any unvisited cell adjacent to a visited one and
 * resumes from there. Lower memory than DFS, similar river-y bias.
 */
public class HuntAndKillGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "hunt-and-kill"; }
    @Override public String displayName() { return "Hunt-and-Kill"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n²) worst case, O(1) auxiliary",
                "Long corridors with horizontal scanning bias",
                "DFS-like carving with linear scan to resume — minimal memory.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        Point cur = new Point(rng.nextInt(rows), rng.nextInt(cols));
        grid.cell(cur).markVisited();
        stats.incVisited();

        while (cur != null) {
            // KILL phase: random walk into unvisited cells.
            List<Direction> dirs = new ArrayList<>(Arrays.asList(Direction.values()));
            Collections.shuffle(dirs, rng);
            Point next = null;
            for (Direction d : dirs) {
                Point n = cur.step(d);
                if (grid.inBounds(n) && !grid.cell(n).isVisited()) {
                    grid.carve(grid.cell(cur), d);
                    grid.cell(n).markVisited();
                    stats.incVisited();
                    next = n;
                    break;
                }
            }

            if (next != null) {
                cur = next;
                continue;
            }

            // HUNT phase: scan for any unvisited cell with a visited neighbor.
            cur = null;
            outer:
            for (int r = 0; r < rows; r++) {
                for (int c = 0; c < cols; c++) {
                    Point p = new Point(r, c);
                    if (grid.cell(p).isVisited()) continue;
                    List<Direction> visitedDirs = new ArrayList<>();
                    for (Direction d : Direction.values()) {
                        Point n = p.step(d);
                        if (grid.inBounds(n) && grid.cell(n).isVisited()) visitedDirs.add(d);
                    }
                    if (!visitedDirs.isEmpty()) {
                        Direction d = visitedDirs.get(rng.nextInt(visitedDirs.size()));
                        grid.carve(grid.cell(p), d);
                        grid.cell(p).markVisited();
                        stats.incVisited();
                        cur = p;
                        break outer;
                    }
                }
            }
        }

        grid.clearVisited();
        stats.finish(true);
        return grid;
    }
}
