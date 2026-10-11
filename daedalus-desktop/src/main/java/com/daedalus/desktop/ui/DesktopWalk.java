// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;

/**
 * Player movement for the desktop shell, without JavaFX.
 *
 * <p>ADR-003: logic that grew in {@code MainController} moves here (or into
 * core) so it can be tested without TestFX. Canvas layout lives on
 * {@link DesktopPaint}; the controller still owns key translation and
 * {@code GraphicsContext}.
 */
public final class DesktopWalk {

    private DesktopWalk() {
    }

    public record Outcome(Point position, boolean reachedGoal, boolean moved) {
    }

    /**
     * One legal step, or the same cell if the wall is closed, the maze is
     * missing, or the player already finished.
     */
    public static Outcome step(MazeGrid grid, Point from, Point goal, Direction dir,
                               boolean alreadyDone) {
        if (grid == null || from == null || dir == null || alreadyDone) {
            return new Outcome(from, alreadyDone, false);
        }
        if (!grid.cell(from).isOpen(dir)) {
            return new Outcome(from, false, false);
        }
        Point next = from.step(dir);
        if (!grid.inBounds(next)) {
            return new Outcome(from, false, false);
        }
        return new Outcome(next, next.equals(goal), true);
    }

    /**
     * Direction of a one-cell click, or {@code null} when the hit is not
     * a neighbor — same refuse as {@code stage.js} (no chords, no teleports).
     */
    public static Direction toward(Point from, Point hit) {
        if (from == null || hit == null) {
            return null;
        }
        int dr = hit.row() - from.row();
        int dc = hit.col() - from.col();
        if (Math.abs(dr) + Math.abs(dc) != 1) {
            return null;
        }
        if (dr == -1) {
            return Direction.NORTH;
        }
        if (dr == 1) {
            return Direction.SOUTH;
        }
        return dc == -1 ? Direction.WEST : Direction.EAST;
    }
}
