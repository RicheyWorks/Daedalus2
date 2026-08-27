// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.api.dto.Hotspot;
import com.daedalus.model.Point;
import com.daedalus.model.TileType;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

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
    /** Overlay legend sits on the well — same reserve as {@code draw.js}. */
    public static final double LEGEND_RESERVE = 40;

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

        /**
         * Fit a maze above the overlay legend. Using the full pane put the
         * last row under the key.
         */
        public static Layout fitMaze(int tileRows, int tileCols, double width, double height) {
            return fit(tileRows, tileCols, width, height - LEGEND_RESERVE);
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

    /**
     * Player memory — every stood-on cell and the opening between adjacent
     * steps. A solve ribbon skips start/goal; a walk that hid those cells
     * looked like the explorer had never been there.
     */
    public static List<TileRect> walkOverlay(List<Point> walk) {
        return pathOverlay(walk, null, null);
    }

    /**
     * Name only what is on the board — same rule as {@code stage.js} {@code syncLegend}.
     */
    public static List<String> legendKeys(boolean maze, boolean path, boolean walk) {
        return legendKeys(maze, path, walk, false);
    }

    public static List<String> legendKeys(boolean maze, boolean path, boolean walk,
                                          boolean hotspot) {
        if (!maze) {
            return List.of();
        }
        List<String> keys = new ArrayList<>(List.of("floor", "wall", "start", "goal"));
        if (path) {
            keys.add("path");
        }
        if (walk) {
            keys.add("player");
        }
        if (hotspot) {
            keys.add("hotspot");
        }
        return List.copyOf(keys);
    }

    /**
     * Same placement as {@code share.js} {@code placeSpots} so a seed that
     * paints a field on the web paints the same cells here.
     */
    public static List<Hotspot> placeSpots(int rows, int cols, int count, long seed,
                                           double cost) {
        if (rows <= 0 || cols <= 0 || count <= 0) {
            return List.of();
        }
        int max = Math.min(count, rows * cols);
        int[] state = {(int) seed};
        Set<String> seen = new HashSet<>();
        List<Hotspot> out = new ArrayList<>();
        while (out.size() < max) {
            int r = (int) Math.floor(rng32(state) * rows);
            int c = (int) Math.floor(rng32(state) * cols);
            String k = r + "," + c;
            if (seen.add(k)) {
                out.add(new Hotspot(r, c, cost));
            }
        }
        return List.copyOf(out);
    }

    /**
     * Mulberry32 — bit-identical to {@code share.js} {@code rng32}.
     */
    static double rng32(int[] state) {
        int a = state[0] + 0x6D2B79F5;
        state[0] = a;
        int t = (a ^ (a >>> 15)) * (1 | a);
        t = t + ((t ^ (t >>> 7)) * (61 | t)) ^ t;
        return Integer.toUnsignedLong(t ^ (t >>> 14)) / 4294967296.0;
    }

    /**
     * Hot-spot cells and the openings between adjacent ones. Rock and wall
     * cells stay void — same skip as {@code draw.js}.
     */
    public static List<TileRect> hotspotOverlay(List<Hotspot> spots, TileType[][] tiles) {
        if (spots == null || spots.isEmpty() || tiles == null || tiles.length < 3) {
            return List.of();
        }
        int rows = (tiles.length - 1) / 2;
        int cols = (tiles[0].length - 1) / 2;
        Set<String> live = new HashSet<>();
        List<TileRect> out = new ArrayList<>();
        for (Hotspot h : spots) {
            if (h == null || h.row() < 0 || h.col() < 0 || h.row() >= rows || h.col() >= cols) {
                continue;
            }
            int tr = 2 * h.row() + 1;
            int tc = 2 * h.col() + 1;
            if (tiles[tr][tc] == TileType.WALL || rockCell(tiles, tr, tc)) {
                continue;
            }
            live.add(h.row() + "," + h.col());
            out.add(new TileRect(tr, tc));
        }
        for (String key : live) {
            String[] parts = key.split(",");
            int r = Integer.parseInt(parts[0]);
            int c = Integer.parseInt(parts[1]);
            if (live.contains(r + "," + (c + 1)) && tiles[2 * r + 1][2 * c + 2] != TileType.WALL) {
                out.add(new TileRect(2 * r + 1, 2 * c + 2));
            }
            if (live.contains((r + 1) + "," + c) && tiles[2 * r + 2][2 * c + 1] != TileType.WALL) {
                out.add(new TileRect(2 * r + 2, 2 * c + 1));
            }
        }
        return List.copyOf(out);
    }

    private static boolean rockCell(TileType[][] tiles, int r, int c) {
        if (r <= 0 || c <= 0 || r >= tiles.length - 1 || c >= tiles[0].length - 1) {
            return false;
        }
        return tiles[r][c] != TileType.START && tiles[r][c] != TileType.GOAL
                && tiles[r - 1][c] == TileType.WALL && tiles[r + 1][c] == TileType.WALL
                && tiles[r][c - 1] == TileType.WALL && tiles[r][c + 1] == TileType.WALL;
    }

    /**
     * Same unfold budget as {@code draw.js} {@code pathRevealMs} — a 300-cell
     * route should grow, not appear as a finished ribbon.
     */
    public static int pathRevealMs(int pathLength) {
        return Math.min(5000, Math.max(700, pathLength * 14));
    }

    /** Visible prefix of a route at {@code progress} in {@code [0, 1]}. */
    public static List<Point> pathPrefix(List<Point> path, double progress) {
        if (path == null || path.isEmpty() || progress <= 0) {
            return List.of();
        }
        if (progress >= 1) {
            return List.copyOf(path);
        }
        int n = Math.max(1, (int) Math.ceil(path.size() * progress));
        return List.copyOf(path.subList(0, Math.min(n, path.size())));
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
    /**
     * Backing store for a HiDPI canvas. JavaFX {@code Canvas} is a bitmap
     * in its own width×height; painting in CSS pixels on a 2× display
     * smears the same corridors the web used to.
     */
    public record Backing(double cssW, double cssH, double scaleX, double scaleY,
                          double pixelW, double pixelH) {

        public static Backing of(double cssW, double cssH, double scaleX, double scaleY) {
            if (cssW <= 0 || cssH <= 0) {
                return null;
            }
            double sx = scaleX > 0 ? scaleX : 1;
            double sy = scaleY > 0 ? scaleY : 1;
            return new Backing(cssW, cssH, sx, sy,
                    Math.round(cssW * sx), Math.round(cssH * sy));
        }
    }

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
