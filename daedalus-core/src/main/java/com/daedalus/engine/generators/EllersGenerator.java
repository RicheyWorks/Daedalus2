// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.*;

/**
 * Eller's. Row-by-row generator using disjoint sets per row. Memory cost is O(width)
 * — the only generator that can produce mazes of unbounded height in constant memory.
 *
 * <p>Bias: subtle horizontal bias but well-distributed; visually clean.
 */
public class EllersGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "ellers"; }
    @Override public String displayName() { return "Eller's"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(width) memory",
                "Subtle horizontal bias; row-streaming friendly",
                "The 'infinite scroll' generator — row-by-row with set merging.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        int[] rowSets = new int[cols];
        int nextSetId = 0;
        for (int c = 0; c < cols; c++) rowSets[c] = nextSetId++;

        for (int r = 0; r < rows; r++) {
            // Step 1: randomly merge adjacent cells in different sets.
            for (int c = 0; c < cols - 1; c++) {
                boolean lastRow = (r == rows - 1);
                if (rowSets[c] != rowSets[c + 1] && (lastRow || rng.nextBoolean())) {
                    grid.carve(grid.cell(new Point(r, c)), Direction.EAST);
                    int oldSet = rowSets[c + 1];
                    int newSet = rowSets[c];
                    for (int k = 0; k < cols; k++) if (rowSets[k] == oldSet) rowSets[k] = newSet;
                    stats.incVisited();
                }
            }

            if (r == rows - 1) break;

            // Step 2: each set must drop at least one passage south.
            Map<Integer, List<Integer>> setMembers = new HashMap<>();
            for (int c = 0; c < cols; c++) {
                setMembers.computeIfAbsent(rowSets[c], k -> new ArrayList<>()).add(c);
            }

            int[] nextRowSets = new int[cols];
            Arrays.fill(nextRowSets, -1);

            for (Map.Entry<Integer, List<Integer>> e : setMembers.entrySet()) {
                List<Integer> members = e.getValue();
                Collections.shuffle(members, rng);
                int drops = 1 + rng.nextInt(members.size());
                for (int i = 0; i < drops; i++) {
                    int c = members.get(i);
                    grid.carve(grid.cell(new Point(r, c)), Direction.SOUTH);
                    nextRowSets[c] = e.getKey();
                    stats.incVisited();
                }
            }
            for (int c = 0; c < cols; c++) {
                if (nextRowSets[c] == -1) nextRowSets[c] = nextSetId++;
            }
            rowSets = nextRowSets;
        }

        stats.finish(true);
        return grid;
    }
}
