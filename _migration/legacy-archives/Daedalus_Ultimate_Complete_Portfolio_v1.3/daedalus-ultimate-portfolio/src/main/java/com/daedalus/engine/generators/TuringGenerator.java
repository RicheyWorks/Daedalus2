package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.*;

/**
 * Turing State-Machine Generator.
 *
 * Inspired directly by Alan Turing’s finite-state machines and universal computation.
 * We maintain an "active" list of frontier cells (like Growing Tree), but a simple
 * 4-state machine dictates HOW we pick the next cell to expand. Simple rules → wildly
 * complex, ever-shifting textures. Exactly the kind of emergent behavior Turing loved.
 *
 * <p>Visually unique: hybrid of backtracker rivers, Prim bushiness, and chaotic
 * state-driven branching. No other generator in your collection behaves this way.
 */
public class TuringGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "turing"; }
    @Override public String displayName() { return "Turing (State Machine)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(n) space",
                "Simple rules → complex emergent patterns (pure Turing spirit)",
                "Finite-state machine controls cell selection. Honors Alan Turing’s legacy of computation & morphogenesis.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        List<Point> active = new ArrayList<>();
        Point first = new Point(rng.nextInt(rows), rng.nextInt(cols));
        active.add(first);
        grid.cell(first).markVisited();
        stats.incVisited();

        int state = 0;   // Turing machine "head" state — cycles 0-3

        while (!active.isEmpty()) {
            stats.recordFrontier(active.size());

            int idx;
            switch (state) {
                case 0 -> idx = active.size() - 1;           // newest (backtracker style)
                case 1 -> idx = 0;                           // oldest (BFS-like)
                case 2 -> idx = rng.nextInt(active.size());  // pure random (Prim-like)
                default -> idx = active.size() / 2;          // middle — chaotic shift
            }
            state = (state + 1) % 4;   // advance the machine state

            Point cur = active.get(idx);

            // Try random directions (Fisher-Yates style, same as RecursiveBacktracker)
            List<Direction> dirs = new ArrayList<>(Arrays.asList(Direction.values()));
            Collections.shuffle(dirs, rng);

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

            if (chosen == null) {
                active.remove(idx);
                stats.incBacktrack();
            } else {
                active.add(chosen);
            }
        }

        grid.clearVisited();
        stats.finish(true);
        return grid;
    }
}
