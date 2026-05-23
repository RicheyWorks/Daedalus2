// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Unit tests for {@link WeightedMazeGrid}: weight defaults, get/set roundtrip, validation,
 * bulk fill, structural copy from a source {@link MazeGrid}.
 */
class WeightedMazeGridTest {

    @Test
    void defaultWeightIsOneForEveryCell() {
        WeightedMazeGrid grid = new WeightedMazeGrid(4, 5);

        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point p = new Point(r, c);
                assertThat(grid.weightOf(p)).isEqualTo(1.0);
                assertThat(grid.getWeight(p)).isEqualTo(1.0);
            }
        }
    }

    @Test
    void setWeightThenGetWeightRoundTrips() {
        WeightedMazeGrid grid = new WeightedMazeGrid(3, 3);
        Point hot = new Point(1, 2);

        grid.setWeight(hot, 7.5);

        assertThat(grid.getWeight(hot)).isEqualTo(7.5);
        assertThat(grid.weightOf(hot)).isEqualTo(7.5);
        // Unrelated cells must remain untouched.
        assertThat(grid.weightOf(new Point(0, 0))).isEqualTo(1.0);
        assertThat(grid.weightOf(new Point(2, 2))).isEqualTo(1.0);
    }

    @Test
    void setAllWeightsAppliesUniformly() {
        WeightedMazeGrid grid = new WeightedMazeGrid(2, 4);

        grid.setAllWeights(3.0);

        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                assertThat(grid.weightOf(new Point(r, c))).isEqualTo(3.0);
            }
        }
    }

    @Test
    void zeroIsAcceptedAsAValidWeight() {
        // Edge case: 0 is non-negative finite, so it must be accepted. Solvers handle
        // it correctly (it just means "free to enter") and we never want a setter
        // surprise for legitimate boundary values.
        WeightedMazeGrid grid = new WeightedMazeGrid(2, 2);
        grid.setWeight(new Point(0, 0), 0.0);
        assertThat(grid.weightOf(new Point(0, 0))).isEqualTo(0.0);
    }

    @Test
    void negativeWeightIsRejected() {
        WeightedMazeGrid grid = new WeightedMazeGrid(2, 2);

        assertThatThrownBy(() -> grid.setWeight(new Point(0, 0), -0.5))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("non-negative");
    }

    @Test
    void naNAndInfinityAreRejected() {
        WeightedMazeGrid grid = new WeightedMazeGrid(2, 2);

        assertThatThrownBy(() -> grid.setWeight(new Point(0, 0), Double.NaN))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> grid.setWeight(new Point(0, 0), Double.POSITIVE_INFINITY))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> grid.setWeight(new Point(0, 0), Double.NEGATIVE_INFINITY))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> grid.setAllWeights(Double.NaN))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void outOfBoundsAccessThrows() {
        WeightedMazeGrid grid = new WeightedMazeGrid(2, 2);

        assertThatThrownBy(() -> grid.setWeight(new Point(5, 5), 1.0))
                .isInstanceOf(IndexOutOfBoundsException.class);
        assertThatThrownBy(() -> grid.getWeight(new Point(-1, 0)))
                .isInstanceOf(IndexOutOfBoundsException.class);
    }

    @Test
    void copyConstructorPreservesTopologyAndStartsAtUnitWeights() {
        // Build a tiny source maze with a single carved passage (0,0)<->(0,1).
        MazeGrid source = new MazeGrid(2, 2);
        source.carve(new Point(0, 0), new Point(0, 1));
        source.setStart(new Point(1, 1));
        source.setGoal(new Point(0, 0));

        WeightedMazeGrid copy = new WeightedMazeGrid(source);

        assertThat(copy.rows()).isEqualTo(2);
        assertThat(copy.cols()).isEqualTo(2);
        assertThat(copy.start()).isEqualTo(new Point(1, 1));
        assertThat(copy.goal()).isEqualTo(new Point(0, 0));
        // Carved passage survived the copy.
        assertThat(copy.cell(new Point(0, 0)).isOpen(Direction.EAST)).isTrue();
        assertThat(copy.cell(new Point(0, 1)).isOpen(Direction.WEST)).isTrue();
        // Walls that were never carved stay closed.
        assertThat(copy.cell(new Point(0, 0)).isOpen(Direction.SOUTH)).isFalse();
        // Weights initialise at the uniform default.
        assertThat(copy.weightOf(new Point(0, 0))).isEqualTo(1.0);
        assertThat(copy.weightOf(new Point(1, 1))).isEqualTo(1.0);
    }

    @Test
    void plainMazeGridReportsUniformWeight() {
        // Locks in the polymorphic contract: callers (Dijkstra/A*) can read weightOf
        // off any MazeGrid and get sane uniform-cost behavior on the unweighted base class.
        MazeGrid plain = new MazeGrid(3, 3);
        for (int r = 0; r < plain.rows(); r++) {
            for (int c = 0; c < plain.cols(); c++) {
                assertThat(plain.weightOf(new Point(r, c))).isEqualTo(1.0);
            }
        }
    }
}
