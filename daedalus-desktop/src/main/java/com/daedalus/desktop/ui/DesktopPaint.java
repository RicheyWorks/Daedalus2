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
 */
public final class DesktopPaint {

    private DesktopPaint() {
    }

    /** Square cells, centered in the canvas so a non-square window letterboxes. */
    public record Layout(double cellSize, double offsetX, double offsetY,
                         int tileRows, int tileCols) {

        /**
         * Fit a tile grid into {@code width}×{@code height}. {@code null} when
         * there is nothing to paint (empty canvas or empty grid).
         */
        public static Layout fit(int tileRows, int tileCols, double width, double height) {
            if (tileRows <= 0 || tileCols <= 0 || width <= 0 || height <= 0) {
                return null;
            }
            double cellSize = Math.max(1.0, Math.floor(Math.min(width / tileCols, height / tileRows)));
            double drawW = cellSize * tileCols;
            double drawH = cellSize * tileRows;
            return new Layout(
                    cellSize,
                    Math.floor((width - drawW) / 2),
                    Math.floor((height - drawH) / 2),
                    tileRows,
                    tileCols);
        }

        public double x(int tileCol) {
            return offsetX + tileCol * cellSize;
        }

        public double y(int tileRow) {
            return offsetY + tileRow * cellSize;
        }
    }

    /** One filled square in the 2r+1 / 2c+1 tile projection. */
    public record TileRect(int tileRow, int tileCol) {
    }

    /** Axis-aligned box for the player disc (inset from the passage tile). */
    public record Marker(double x, double y, double size) {
    }

    /**
     * Solve-path tiles, skipping start and goal cells so those keep their
     * endpoint colors. Adjacent steps also paint the carved wall between them.
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
                out.add(new TileRect(prev.row() + p.row() + 1, prev.col() + p.col() + 1));
            }
        }
        return List.copyOf(out);
    }

    public static Marker playerMarker(Layout layout, Point player) {
        if (layout == null || player == null) {
            return null;
        }
        double inset = Math.max(1.0, layout.cellSize() * 0.1);
        return new Marker(
                layout.x(2 * player.col() + 1) + inset,
                layout.y(2 * player.row() + 1) + inset,
                layout.cellSize() - 2 * inset);
    }

    /** Unknown or null tiles paint as passage — the same fallback the controller used. */
    public static TileType roleFor(TileType tile) {
        return tile == null ? TileType.PASSAGE : tile;
    }
}
