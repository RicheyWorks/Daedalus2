// SPDX-License-Identifier: MIT
package com.daedalus.world.labyrinth;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import com.daedalus.solver.solvers.BfsSolver;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class BrokenSurveyTest {
    @Test void deterministicAcrossSeedsAndIndependentSolver() {
        for (long seed : new long[] {0, 1, -1, Long.MIN_VALUE, Long.MAX_VALUE, 741}) {
            BrokenSurvey a = BrokenSurvey.generate(7, 9, seed);
            BrokenSurvey b = BrokenSurvey.generate(7, 9, seed);
            assertEquals(a.first(), b.first());
            assertEquals(a.second(), b.second());
            assertEquals(a.solution(), b.solution());
            assertEquals(a.solution(), new BfsSolver().solve(a.truthSnapshot()));
            assertEquals(BrokenSurvey.Verdict.VALID, a.verify(a.solution()));
            assertEquals(seed, a.seed());
            assertEquals(7, a.rows());
            assertEquals(9, a.cols());
        }
    }

    @Test void bothMapsAreWrongButTogetherContainTheTruth() {
        for (int seed = 0; seed < 30; seed++) {
            BrokenSurvey game = BrokenSurvey.generate(2 + seed % 5, 2 + seed % 7, seed);
            MazeGrid truth = game.truthSnapshot();
            assertNotEquals(game.first(), game.second());
            assertTrue(new BfsSolver().solve(rebuild(game, game.first())).isEmpty());
            assertTrue(new BfsSolver().solve(rebuild(game, game.second())).isEmpty());
            int mistakesA = 0;
            int mistakesB = 0;
            List<BrokenSurvey.Passage> a = game.first().passages();
            List<BrokenSurvey.Passage> b = game.second().passages();
            assertEquals(game.rows() * (game.cols() - 1) + game.cols() * (game.rows() - 1), a.size());
            for (int i = 0; i < a.size(); i++) {
                var edge = a.get(i);
                assertTrue(truth.inBounds(edge.a()));
                assertTrue(truth.inBounds(edge.b()));
                assertEquals(1, edge.a().manhattan(edge.b()));
                boolean real = truth.openNeighbors(edge.a()).contains(edge.b());
                if (edge.open() != real) { mistakesA++; }
                if (b.get(i).open() != real) { mistakesB++; }
                assertEquals(real, edge.open() || b.get(i).open());
            }
            assertEquals(1, mistakesA);
            assertEquals(1, mistakesB);
        }
    }

    @Test void limitsAndSmallestMaze() {
        for (int[] size : new int[][] {{0, 4}, {4, 0}, {-1, 2}, {1, 2}, {2, 1}, {65, 2}, {2, 65}}) {
            assertThrows(IllegalArgumentException.class, () -> BrokenSurvey.generate(size[0], size[1], 0));
        }
        for (int size : new int[] {2, BrokenSurvey.MAX_SIDE}) {
            BrokenSurvey game = BrokenSurvey.generate(size, size, 10);
            assertEquals(BrokenSurvey.Verdict.VALID, game.verify(game.solution()));
        }
    }

    @Test void answerAndSurveysCannotBeMutated() {
        BrokenSurvey game = BrokenSurvey.generate(4, 4, 0);
        assertThrows(UnsupportedOperationException.class, () -> game.solution().clear());
        assertThrows(UnsupportedOperationException.class, () -> game.first().passages().clear());
        List<BrokenSurvey.Passage> source = new ArrayList<>(game.second().passages());
        var survey = new BrokenSurvey.Survey(source);
        source.clear();
        assertFalse(survey.passages().isEmpty());
        MazeGrid copy = game.truthSnapshot();
        copy.seal(game.solution().get(0), game.solution().get(1));
        assertEquals(BrokenSurvey.Verdict.VALID, game.verify(game.solution()));
    }

    @Test void invalidAndReplayRoutesNeverChangeState() {
        BrokenSurvey game = BrokenSurvey.generate(5, 5, 31);
        var before = game.first();
        assertEquals(BrokenSurvey.Verdict.MISSING_ROUTE, game.verify(null));
        assertEquals(BrokenSurvey.Verdict.MISSING_ROUTE, game.verify(List.of()));
        assertEquals(BrokenSurvey.Verdict.OUT_OF_BOUNDS, game.verify(Arrays.asList(game.start(), null)));
        assertEquals(BrokenSurvey.Verdict.OUT_OF_BOUNDS, game.verify(List.of(new Point(-1, 0))));
        assertEquals(BrokenSurvey.Verdict.OUT_OF_BOUNDS, game.verify(List.of(new Point(5, 0))));
        assertEquals(BrokenSurvey.Verdict.REPEATED_CELL, game.verify(List.of(game.start(), game.start(), game.goal())));
        assertEquals(BrokenSurvey.Verdict.WRONG_ENDPOINTS, game.verify(List.of(game.goal(), game.start())));
        assertEquals(BrokenSurvey.Verdict.NON_ADJACENT, game.verify(List.of(game.start(), game.goal())));
        List<Point> huge = new ArrayList<>();
        for (int i = 0; i < 26; i++) { huge.add(game.start()); }
        assertEquals(BrokenSurvey.Verdict.TOO_LONG, game.verify(huge));
        for (int i = 0; i < 3; i++) {
            assertEquals(BrokenSurvey.Verdict.VALID, game.verify(game.solution()));
        }
        assertEquals(before, game.first());
    }

    @Test void adjacentWallCrossingIsNotAValidRoute() {
        for (int seed = 0; seed < 20; seed++) {
            BrokenSurvey game = BrokenSurvey.generate(3, 3, seed);
            List<Point> rowRoute = List.of(new Point(0, 0), new Point(0, 1), new Point(0, 2),
                    new Point(1, 2), new Point(2, 2));
            if (!rowRoute.equals(game.solution())) {
                assertEquals(BrokenSurvey.Verdict.WALL, game.verify(rowRoute));
                return;
            }
        }
        fail("Expected a seeded maze with a wall on the direct row route");
    }

    private static MazeGrid rebuild(BrokenSurvey game, BrokenSurvey.Survey survey) {
        MazeGrid grid = new MazeGrid(game.rows(), game.cols());
        for (var edge : survey.passages()) {
            if (edge.open()) { grid.carve(edge.a(), edge.b()); }
        }
        // Check exterior walls independently, including all four corners.
        for (int col = 0; col < game.cols(); col++) {
            assertFalse(grid.cell(0, col).isOpen(Direction.NORTH));
            assertFalse(grid.cell(game.rows() - 1, col).isOpen(Direction.SOUTH));
        }
        for (int row = 0; row < game.rows(); row++) {
            assertFalse(grid.cell(row, 0).isOpen(Direction.WEST));
            assertFalse(grid.cell(row, game.cols() - 1).isOpen(Direction.EAST));
        }
        return grid;
    }
}
