// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Desktop walk rules without a JavaFX toolkit. {@code MainController#tryMove}
 * used to be the only copy of these rules, and nothing tested them.
 */
class DesktopWalkTest {

    @Test
    void anOpenWallMovesThePlayerAndAClosedWallDoesNot() {
        MazeGrid grid = new MazeGrid(3, 3);
        Point start = new Point(1, 1);
        Point goal = new Point(1, 2);
        grid.carve(start, goal);

        DesktopWalk.Outcome blocked = DesktopWalk.step(grid, start, goal, Direction.NORTH, false);
        assertThat(blocked.moved()).isFalse();
        assertThat(blocked.position()).isEqualTo(start);

        DesktopWalk.Outcome moved = DesktopWalk.step(grid, start, goal, Direction.EAST, false);
        assertThat(moved.moved()).isTrue();
        assertThat(moved.position()).isEqualTo(goal);
        assertThat(moved.reachedGoal()).isTrue();
    }

    @Test
    void aFinishedWalkDoesNotMoveAgain() {
        MazeGrid grid = new MazeGrid(2, 2);
        grid.carve(new Point(0, 0), new Point(0, 1));
        DesktopWalk.Outcome again = DesktopWalk.step(
                grid, new Point(0, 1), new Point(0, 1), Direction.WEST, true);
        assertThat(again.moved()).isFalse();
        assertThat(again.reachedGoal()).isTrue();
        assertThat(again.position()).isEqualTo(new Point(0, 1));
    }

    @Test
    void aMissingMazeIsANoOp() {
        DesktopWalk.Outcome none = DesktopWalk.step(
                null, new Point(0, 0), new Point(1, 1), Direction.EAST, false);
        assertThat(none.moved()).isFalse();
        assertThat(none.position()).isEqualTo(new Point(0, 0));
    }

    @Test
    void aClickStepsOnlyToANeighbor() {
        Point at = new Point(1, 1);
        assertThat(DesktopWalk.toward(at, new Point(0, 1))).isEqualTo(Direction.NORTH);
        assertThat(DesktopWalk.toward(at, new Point(2, 1))).isEqualTo(Direction.SOUTH);
        assertThat(DesktopWalk.toward(at, new Point(1, 0))).isEqualTo(Direction.WEST);
        assertThat(DesktopWalk.toward(at, new Point(1, 2))).isEqualTo(Direction.EAST);
        assertThat(DesktopWalk.toward(at, new Point(2, 2)))
                .as("a diagonal is a chord through a post")
                .isNull();
        assertThat(DesktopWalk.toward(at, at)).isNull();
        assertThat(DesktopWalk.toward(at, null)).isNull();
    }
}
