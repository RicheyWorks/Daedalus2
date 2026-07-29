// SPDX-License-Identifier: MIT

package com.daedalus.visualize;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.model.TileType;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.theory.MazeMetrics;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The reference {@link MazeVisualizer}. Glyph fidelity is the contract that matters: the ASCII
 * output must agree with {@code toTileGrid()} — the same projection the REST surface ships —
 * or a terminal user and an API user are looking at two different mazes.
 */
class AsciiMazeVisualizerTest {

    private static MazeGrid maze() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(6, 9, 11L, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        return grid;
    }

    @Test
    void rendersTheExactTileProjectionTheRestSurfaceShips() {
        MazeGrid grid = maze();
        String art = AsciiMazeVisualizer.renderToString(grid, List.of());

        String[] lines = art.split(System.lineSeparator());
        TileType[][] tiles = grid.toTileGrid();
        assertThat(lines).hasSize(tiles.length);
        for (int r = 0; r < tiles.length; r++) {
            for (int c = 0; c < tiles[r].length; c++) {
                assertThat(lines[r].charAt(c))
                        .as("tile (%d,%d)", r, c)
                        .isEqualTo(tiles[r][c].glyph());
            }
        }
    }

    @Test
    void overlaysASolverPathWithoutErasingStartAndGoal() {
        MazeGrid grid = maze();
        List<Point> path = new BfsSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());
        String art = AsciiMazeVisualizer.renderToString(grid, path);

        assertThat(art).contains(String.valueOf(TileType.PATH.glyph()));
        assertThat(art).contains(String.valueOf(TileType.START.glyph()));
        assertThat(art).contains(String.valueOf(TileType.GOAL.glyph()));
        // Interior path cells (not start/goal) render as PATH.
        Point mid = path.get(path.size() / 2);
        String[] lines = art.split(System.lineSeparator());
        assertThat(lines[2 * mid.row() + 1].charAt(2 * mid.col() + 1))
                .isEqualTo(TileType.PATH.glyph());
    }

    @Test
    void theInterfaceRendersToAnyAppendableWithStats() {
        MazeGrid grid = maze();
        MazeStats stats = new MazeStats();
        stats.finish(true);
        StringBuilder out = new StringBuilder();

        new AsciiMazeVisualizer(out).render(grid, stats, List.of());

        assertThat(out.toString())
                .contains(String.valueOf(TileType.START.glyph()))
                .contains("MazeStats"); // the stats line rides along
    }

    @Test
    void mazeGridToStringIsTheAsciiArt() {
        MazeGrid grid = maze();
        assertThat(grid.toString())
                .isEqualTo(AsciiMazeVisualizer.renderToString(grid, List.of()));
    }
}
