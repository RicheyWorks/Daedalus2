// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The two input contracts {@link MazeGrid} documents and nothing enforced.
 *
 * <p>Found by mutation on 2026-08-02. 63 test files reference this class and none of them
 * assert what it does with bad input, which is the standard shape of a substrate blind spot:
 * every caller tests its own concern and takes the foundation for granted. Widening
 * {@code directionBetween} to accept a non-adjacent pair, and deleting the constructor's
 * dimension check outright, both passed the entire suite.
 *
 * <p>Neither is a live bug — no caller in the engine passes non-adjacent points or a zero
 * dimension. That is precisely why they are worth pinning rather than leaving: an unenforced
 * contract on a class this widely used degrades silently, and the first caller to violate it
 * gets a wrong maze instead of an exception. {@code carve} with a bad pair would open a wall
 * between two cells that are not neighbours, which is a corrupt grid every layer above trusts.
 */
class MazeGridContractTest {

    @Test
    void carvingBetweenNonAdjacentCellsIsRefused() {
        MazeGrid grid = new MazeGrid(5, 5);

        assertThatThrownBy(() -> grid.carve(new Point(0, 0), new Point(2, 0)))
                .as("two rows apart is not a shared wall; opening one would corrupt the grid")
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("not adjacent");

        // Both orderings, deliberately. The first version of this test checked only the
        // downward pair, and the mutation harness caught the omission: `directionBetween`
        // decides on a signed delta, so widening the NORTH branch to `dr <= -1` is invisible
        // to a case whose delta is positive. A rejection test that samples one sign of an
        // asymmetric comparison is half a test.
        assertThatThrownBy(() -> grid.carve(new Point(2, 0), new Point(0, 0)))
                .as("distance is not direction — two rows above is no more adjacent than "
                        + "two rows below")
                .isInstanceOf(IllegalArgumentException.class);

        assertThatThrownBy(() -> grid.carve(new Point(0, 0), new Point(0, 3)))
                .as("and the same on the column axis")
                .isInstanceOf(IllegalArgumentException.class);

        assertThatThrownBy(() -> grid.carve(new Point(1, 1), new Point(2, 2)))
                .as("diagonals share a corner, not a wall")
                .isInstanceOf(IllegalArgumentException.class);

        assertThatThrownBy(() -> grid.carve(new Point(3, 3), new Point(3, 3)))
                .as("a cell is not its own neighbour")
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void carvingOffTheGridIsRefused() {
        // carve(Cell, Direction) used to return silently when the step left the grid, so a
        // generator bug that walked off an edge produced a wall that looked intentional.
        // carve(Point, Point) already threw; the two overloads now agree.
        MazeGrid grid = new MazeGrid(3, 3);

        assertThatThrownBy(() -> grid.carve(grid.cell(0, 0), Direction.NORTH))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("out of bounds");
        assertThatThrownBy(() -> grid.carve(grid.cell(0, 0), Direction.WEST))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("out of bounds");

        grid.carve(grid.cell(0, 0), Direction.EAST);
        assertThat(grid.openNeighbors(new Point(0, 0))).contains(new Point(0, 1));
    }

    @Test
    void adjacentCarvingStillWorksInBothDirections() {
        // The other half of the contract: refusing bad pairs must not cost the good ones, and
        // the wall has to fall from both sides — a one-way passage is the failure this grid's
        // whole neighbour model would hide.
        MazeGrid grid = new MazeGrid(5, 5);
        Point a = new Point(2, 2);
        Point b = new Point(2, 3);

        grid.carve(a, b);

        assertThat(grid.openNeighbors(a)).contains(b);
        assertThat(grid.openNeighbors(b)).contains(a);
    }

    @Test
    void nonPositiveDimensionsAreRefused() {
        assertThatThrownBy(() -> new MazeGrid(0, 5))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("positive");
        assertThatThrownBy(() -> new MazeGrid(5, 0))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new MazeGrid(-1, -1))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void theGridAndCellViewsOfVisitedAreTheSameFlag() {
        // This class used to keep a boolean[][] beside the cells and a line in markVisited to
        // hold the two in step. Nothing read the array (mutants/gridteeth.py: removing that
        // synchronisation was inert, because grid.isVisited(Point) had no caller), and removing
        // it measured no slower — see the class javadoc for the numbers. What it removed that
        // matters is the possibility of the two views disagreeing, so that is what this pins:
        // there is one flag, reachable two ways, and a second copy cannot be reintroduced
        // without failing here.
        MazeGrid grid = new MazeGrid(4, 5);
        Point p = new Point(2, 3);

        grid.markVisited(p);
        assertThat(grid.isVisited(p)).isTrue();
        assertThat(grid.cell(p).isVisited())
                .as("the Cell must see a mark made through the grid")
                .isTrue();

        grid.cell(p).clearVisited();
        assertThat(grid.isVisited(p))
                .as("and the grid must see a mark cleared through the Cell")
                .isFalse();

        grid.cell(p).markVisited();
        assertThat(grid.isVisited(p)).isTrue();
        grid.clearVisited();
        assertThat(grid.cell(p).isVisited()).isFalse();
        assertThat(grid.isVisited(p)).isFalse();
    }
}
