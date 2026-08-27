// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.model.Point;
import com.daedalus.model.TileType;

import java.util.ArrayList;
import java.util.List;

/**
 * Canvas layout for the desktop shell, without JavaFX.
 *
 * <p>ADR-003: {@code MainController#redraw} used to be the only copy of
 * letterboxing, path-connector tiles, and the inset player disc. Those
 * rules are geometry, not FXML glue, so a 1-pixel drift on resize was
 * invisible to the suite. The controller still calls {@code GraphicsContext}.
 *
 * <p>Thin-wall track matches the web painter: even tiles are walls
 * ({@code cell/4}), odd tiles are passages. A uniform 2r+1 square grid
 * made every dungeon look like a chunky bitmap.
 */
public final class DesktopPaint {

    /** Copy for an empty canvas — the well should speak, not stay a blank void. */
    public static final String EMPTY_WORDMARK = "DAEDALUS";
    public static final String EMPTY_TITLE = "Pick a generator and click Generate";
    public static final String EMPTY_DETAIL = "then Solve to watch a route";
    public static final String EMPTY_HINT = "or walk with the arrow keys";

    /**
     * Same miniature as {@code draw.js} {@code IDLE_TILES} — one product empty well.
     */
    public static final String[] EMPTY_MARK = {
            "###########",
            "# #   #   #",
            "# ### ### #",
            "#   #   # #",
            "### ### # #",
            "#     #   #",
            "###########",
    };
    public static final Point EMPTY_MARK_START = new Point(0, 0);
    public static final Point EMPTY_MARK_GOAL = new Point(2, 4);
    public static final double EMPTY_MARK_BUDGET_W = 132;
    public static final double EMPTY_MARK_BUDGET_H = 92;

    private DesktopPaint() {
    }

    /**
     * Thin-wall cells, centered in the canvas so a non-square window letterboxes.
     */
    public record Layout(double cellSize, double wall, double offsetX, double offsetY,
                         int tileRows, int tileCols, double[] offX, double[] offY) {

        /**
         * Fit a tile grid into {@code width}×{@code height}. {@code null} when
         * there is nothing to paint (empty canvas or empty grid).
         */
        public static Layout fit(int tileRows, int tileCols, double width, double height) {
            if (tileRows <= 0 || tileCols <= 0 || width <= 0 || height <= 0) {
                return null;
            }
            int cols = Math.max(1, (tileCols - 1) / 2);
            int rows = Math.max(1, (tileRows - 1) / 2);
            double cell = Math.max(2.0, Math.floor(Math.min(
                    width / (cols * 1.25 + 0.25),
                    height / (rows * 1.25 + 0.25))));
            double wall = Math.max(1.0, Math.round(cell / 4.0));
            double[] offX = track(tileCols, wall, cell);
            double[] offY = track(tileRows, wall, cell);
            double drawW = offX[tileCols];
            double drawH = offY[tileRows];
            return new Layout(
                    cell,
                    wall,
                    Math.floor((width - drawW) / 2),
                    Math.floor((height - drawH) / 2),
                    tileRows,
                    tileCols,
                    offX,
                    offY);
        }

        private static double[] track(int n, double wall, double cell) {
            double[] off = new double[n + 1];
            for (int i = 0; i < n; i++) {
                off[i + 1] = off[i] + (i % 2 == 0 ? wall : cell);
            }
            return off;
        }

        public double x(int tileCol) {
            return offsetX + offX[tileCol];
        }

        public double y(int tileRow) {
            return offsetY + offY[tileRow];
        }

        public double w(int tileCol) {
            return offX[tileCol + 1] - offX[tileCol];
        }

        public double h(int tileRow) {
            return offY[tileRow + 1] - offY[tileRow];
        }
    }

    /** One filled square in the 2r+1 / 2c+1 tile projection. */
    public record TileRect(int tileRow, int tileCol) {
    }

    /** Axis-aligned box for the player disc (inset from the passage tile). */
    public record Marker(double x, double y, double size) {
    }

    /**
     * Floor role for a tile. Start and goal paint as passage so the discs
     * can sit on the corridor — a neon slab was louder than the maze.
     */
    public static TileType floorRole(TileType tile) {
        TileType role = roleFor(tile);
        return role == TileType.START || role == TileType.GOAL ? TileType.PASSAGE : role;
    }

    /**
     * Disc inset inside a passage cell. {@code radiusFrac} is a fraction of
     * {@link Layout#cellSize()} — the web painter uses 0.34 for endpoints.
     */
    public static Marker disc(Layout layout, Point cell, double radiusFrac) {
        if (layout == null || cell == null) {
            return null;
        }
        double diameter = layout.cellSize() * radiusFrac * 2.0;
        double inset = (layout.cellSize() - diameter) / 2.0;
        return new Marker(
                layout.x(2 * cell.col() + 1) + inset,
                layout.y(2 * cell.row() + 1) + inset,
                diameter);
    }

    /**
     * Solve-path tiles, skipping start and goal cells so those keep their
     * endpoint discs. Adjacent steps also paint the carved wall between them.
     */
    public static List<TileRect> pathOverlay(List<Point> path, Point start, Point goal) {
        if (path == null || path.isEmpty()) {
            return List.of();
        }
        List<TileRect> out = new ArrayList<>();
        for (int i = 0; i < path.size(); i++) {
            Point p = path.get(i);
            boolean endpoint = (start != null && p.equals(start))
                    || (goal != null && p.equals(goal));
            if (!endpoint) {
                out.add(new TileRect(2 * p.row() + 1, 2 * p.col() + 1));
            }
            if (i > 0) {
                Point prev = path.get(i - 1);
                if (Math.abs(prev.row() - p.row()) + Math.abs(prev.col() - p.col()) == 1) {
                    out.add(new TileRect(prev.row() + p.row() + 1, prev.col() + p.col() + 1));
                }
            }
        }
        return List.copyOf(out);
    }

    public static Marker playerMarker(Layout layout, Point player) {
        return disc(layout, player, 0.4);
    }

    public static Marker endpointMarker(Layout layout, Point cell) {
        return disc(layout, cell, 0.34);
    }

    /** Unknown or null tiles paint as passage — the same fallback the controller used. */
    public static TileType roleFor(TileType tile) {
        return tile == null ? TileType.PASSAGE : tile;
    }

    /**
     * Fit the idle maze into a small budget, then center it above the copy
     * so a large window does not blow the mark up into a real dungeon.
     */
    public static Layout emptyMarkLayout(double canvasW, double canvasH) {
        if (canvasW <= 0 || canvasH <= 0) {
            return null;
        }
        Layout fitted = Layout.fit(
                EMPTY_MARK.length, EMPTY_MARK[0].length(),
                EMPTY_MARK_BUDGET_W, EMPTY_MARK_BUDGET_H);
        if (fitted == null) {
            return null;
        }
        double drawW = fitted.offX()[fitted.tileCols()];
        double drawH = fitted.offY()[fitted.tileRows()];
        return new Layout(
                fitted.cellSize(),
                fitted.wall(),
                Math.floor(canvasW / 2.0 - drawW / 2.0),
                Math.floor(canvasH / 2.0 - 28.0 - drawH / 2.0),
                fitted.tileRows(),
                fitted.tileCols(),
                fitted.offX(),
                fitted.offY());
    }

    /** Passage tiles of the idle mark — walls stay the void. */
    public static List<TileRect> emptyMarkFloors() {
        List<TileRect> out = new ArrayList<>();
        for (int r = 0; r < EMPTY_MARK.length; r++) {
            String row = EMPTY_MARK[r];
            for (int c = 0; c < row.length(); c++) {
                if (row.charAt(c) != '#') {
                    out.add(new TileRect(r, c));
                }
            }
        }
        return List.copyOf(out);
    }
}
