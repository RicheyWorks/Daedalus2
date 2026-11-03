// SPDX-License-Identifier: MIT

package com.daedalus.mazegame;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * One play of one maze. Pure state: moves, hints, position and the seen set for fog of war.
 * Time is supplied by the caller (elapsed millis at finish), so the model stays deterministic.
 */
public final class MazeRun {

    private final long seed;
    private final Difficulty difficulty;
    private final MazeFactory factory;
    private final MazeGrid grid;
    private final int par;
    private final Set<Point> seen = new HashSet<>();
    private Point position;
    private int moves;
    private int hints;

    public MazeRun(long seed, Difficulty difficulty, MazeFactory factory) {
        this.seed = seed;
        this.difficulty = difficulty;
        this.factory = factory;
        this.grid = factory.build(seed, difficulty);
        this.par = factory.par(grid);
        this.position = grid.start();
        reveal();
    }

    public long seed() { return seed; }
    public Difficulty difficulty() { return difficulty; }
    public int par() { return par; }
    public int moves() { return moves; }
    public int hints() { return hints; }
    public Point position() { return position; }
    public int size() { return grid.rows(); }
    public Point exit() { return grid.goal(); }
    public ShareCode shareCode() { return new ShareCode(seed, difficulty); }
    public String mazeHash() { return MazeFactory.hash(grid); }

    public boolean isOpen(int row, int col, Direction d) {
        return grid.isOpen(row, col, d);
    }

    public boolean isWon() {
        return position.equals(grid.goal());
    }

    /** Tries one step; walls and moves after the win are refused and not counted. */
    public boolean move(Direction d) {
        if (isWon() || !grid.isOpen(position.row(), position.col(), d)) {
            return false;
        }
        position = position.step(d);
        moves++;
        reveal();
        return true;
    }

    /** True when the cell is drawn: always without fog, otherwise once it came within the fog radius. */
    public boolean isVisible(int row, int col) {
        return !difficulty.fog() || seen.contains(new Point(row, col));
    }

    /** Next steps of the optimal route from here (up to {@code count}); each call costs one hint. */
    public List<Point> hint(int count) {
        hints++;
        List<Point> path = factory.solve(grid, position, "bfs");
        return List.copyOf(path.subList(1, Math.min(path.size(), count + 1)));
    }

    /** Full route from the entrance by any registered solver, for the post-win ghost replay. */
    public List<Point> ghost(String solverId) {
        return List.copyOf(factory.solve(grid, grid.start(), solverId));
    }

    public int stars(long millis) {
        return Scoring.stars(par, moves, millis, hints);
    }

    public int score(long millis) {
        return Scoring.score(par, moves, millis, hints);
    }

    private void reveal() {
        if (!difficulty.fog()) {
            return;
        }
        int r = Difficulty.FOG_RADIUS;
        for (int dr = -r; dr <= r; dr++) {
            for (int dc = -r; dc <= r; dc++) {
                Point p = position.translate(dr, dc);
                if (grid.inBounds(p)) {
                    seen.add(p);
                }
            }
        }
    }
}
