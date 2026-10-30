// SPDX-License-Identifier: MIT

package com.daedalus.visualize;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.model.TileType;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.List;

/**
 * Terminal renderer — the reference {@link MazeVisualizer}.
 *
 * <p>Projects the grid through {@code MazeGrid#toTileGrid()} so glyphs stay in lockstep with
 * what the REST surface ships ({@link TileType} is the single source of truth for both), then
 * overlays the path with {@link TileType#PATH} glyphs, leaving start and goal visible.
 */
public final class AsciiMazeVisualizer implements MazeVisualizer {

    private final Appendable out;

    /** @param out render target, e.g. {@code System.out} or a {@code StringBuilder} */
    public AsciiMazeVisualizer(Appendable out) {
        this.out = out;
    }

    @Override
    public void render(MazeGrid grid, MazeStats stats, List<Point> path) {
        try {
            out.append(renderToString(grid, path));
            if (stats != null) {
                out.append(stats.toString()).append(System.lineSeparator());
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    /** Pure-string form, also backing {@code MazeGrid#toString()}. */
    public static String renderToString(MazeGrid grid, List<Point> path) {
        TileType[][] tiles = grid.toTileGrid();
        char[][] glyphs = new char[tiles.length][tiles[0].length];
        for (int r = 0; r < tiles.length; r++) {
            for (int c = 0; c < tiles[r].length; c++) {
                glyphs[r][c] = tiles[r][c].glyph();
            }
        }
        for (Point p : path) {
            int r = 2 * p.row() + 1;
            int c = 2 * p.col() + 1;
            if (glyphs[r][c] == TileType.PASSAGE.glyph()) {
                glyphs[r][c] = TileType.PATH.glyph();
            }
        }
        StringBuilder sb = new StringBuilder(glyphs.length * (glyphs[0].length + 1));
        for (char[] row : glyphs) {
            sb.append(row).append(System.lineSeparator());
        }
        return sb.toString();
    }
}
