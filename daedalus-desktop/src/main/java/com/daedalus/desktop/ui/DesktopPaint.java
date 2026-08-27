// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.api.dto.Hotspot;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.GameSession;
import com.daedalus.model.Point;
import com.daedalus.model.TileType;
import com.daedalus.theory.FacilityPlacement;
import com.daedalus.theory.MazeFlow;
import com.daedalus.theory.MazeMetrics;
import com.daedalus.theory.WaypointTour;

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
    public static final String EMPTY_HINT = "or walk with arrows or a click";

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
    /** PNG sits on the well — same reserve as {@code draw.js} so the first row is not under it. */
    public static final double EXPORT_RESERVE = 28;
    /** Same gold as the web victory ring ({@code --gold}). */
    public static final String VICTORY_GOLD = "#f0b429";
    /** ADR-006 unseen void — same tokens as {@code draw.js}. */
    public static final String FOG_UNSEEN = "#05070a";
    public static final String FOG_FLOOR_DIM = "#2a333c";
    public static final String FOG_FLOOR = "#3d4a58";
    /** Same 1px corridor highlight as {@code draw.js} {@code floorHi}. */
    public static final String FLOOR_HI = "#536272";
    public static final String FOG_FLOOR_HI = FLOOR_HI;
    /** Coral wash — same token as {@code draw.js} hot spots. */
    public static final String HOTSPOT = "#e5484d";
    /** Opening wash between adjacent spots — same alpha as {@code draw.js}. */
    public static final double HOTSPOT_OPENING_ALPHA = 0.35;
    /** Solver ribbon — same alpha as {@code draw.js} {@code paintWalk}. */
    public static final double PATH_ALPHA = 0.85;
    /** Same radius as {@code draw.js} session / fog player. */
    public static final double PLAYER_RADIUS = 0.42;
    /** Search wash — same alphas as {@code draw.js} expansions. */
    public static final double EXPANSION_ALPHA = 0.16;
    public static final double EXPANSION_FRONT_ALPHA = 0.45;
    public static final int EXPANSION_FRONT = 6;
    /**
     * Sequential distance ramp — bit-identical to {@code caption.js}
     * {@code DISTANCE_RAMP}. One hue, monotone in lightness.
     */
    public static final String[] DISTANCE_RAMP = {
            "#1c5cab", "#2a78d6", "#3987e5", "#5598e7",
            "#6da7ec", "#86b6ef", "#9ec5f4", "#cde2fb"
    };
    /** Opening wash for the field — same alpha as {@code draw.js}. */
    public static final double FIELD_OPENING_ALPHA = 0.42;
    /**
     * Heuristic lens bands — bit-identical to {@code caption.js} {@code LENS_COLORS}.
     * Must, tie, never.
     */
    public static final String[] LENS_COLORS = {"#e5484d", "#f2c94c", "#4cc38a"};
    public static final double LENS_MUST_ALPHA = 0.42;
    public static final double LENS_NEVER_ALPHA = 0.16;
    public static final double LENS_OPENING_ALPHA = 0.2;
    /** Arena lanes — same tokens as {@code solve.js}. */
    public static final String RACE_A = "#82b1ff";
    public static final String RACE_B = "#f0b429";
    public static final double RACE_WASH = 0.13;
    public static final double RACE_FRONT_ALPHA = 0.4;
    public static final int RACE_FRONT = 5;
    public static final double RACE_PATH_A = 0.85;
    public static final double RACE_PATH_B = 0.58;
    /**
     * Compare-all routes — same tokens the web table hover would paint,
     * stacked so agreement reads brighter than a lone corridor.
     */
    public static final String[] COMPARE = {
            "#8fb8ff", "#f0b429", "#e5484d", "#4cc38a", "#c084fc", "#9ecbff"
    };
    public static final double COMPARE_ALPHA = 0.22;
    /** Min-cut passage — same purple as {@code draw.js} chokepoints. */
    public static final String CHOKE = "#c084fc";
    /** Dead-end speck — same ice as {@code draw.js}. */
    public static final String DEAD_END = "#9ecbff";
    /** Hardest simple route — same gold as {@code draw.js}. */
    public static final String HARDEST = "#f2c94c";
    public static final double HARDEST_ALPHA = 0.75;
    /** Sanctuary disc — same mint as {@code draw.js}. */
    public static final String SANCTUARY = "#4cc38a";
    /** Loneliest cell — same coral stroke as {@code draw.js}. */
    public static final String WORST_SERVED = "#e5484d";
    /** Same k as the web Place sanctuaries button. */
    public static final int SANCTUARY_K = 5;
    /** Held-Karp corridor — same ice as {@code draw.js} {@code tourPath}. */
    public static final String TOUR = "#9ecbff";
    public static final double TOUR_ALPHA = 0.38;
    /** Uncollected coin — same gold diamond as {@code draw.js}. */
    public static final String WAYPOINT = "#f2c94c";
    public static final String WAYPOINT_GOT = "#4cc38a";
    /** Same k as the web Hunt button. */
    public static final int WAYPOINT_K = 5;
    /** Recorded racer — same tokens as {@code draw.js} ghost walk / disc. */
    public static final String GHOST = "#e6edf3";
    public static final double GHOST_WALK_ALPHA = 0.28;
    public static final double GHOST_DISC_ALPHA = 0.55;
    public static final double GHOST_RADIUS = 0.3;

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
         * Fit a maze between the PNG control and the overlay legend.
         * Using the full pane put the first row under the export and the
         * last row under the key.
         */
        public static Layout fitMaze(int tileRows, int tileCols, double width, double height) {
            Layout fitted = fit(tileRows, tileCols, width,
                    height - LEGEND_RESERVE - EXPORT_RESERVE);
            if (fitted == null) {
                return null;
            }
            return new Layout(
                    fitted.cellSize(),
                    fitted.wall(),
                    fitted.offsetX(),
                    fitted.offsetY() + EXPORT_RESERVE,
                    fitted.tileRows(),
                    fitted.tileCols(),
                    fitted.offX(),
                    fitted.offY());
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

    /**
     * Passage cell under a canvas point — same odd-tile track as
     * {@code draw.js} {@code hitCell}. Walls and the letterbox miss.
     * {@code canvasX}/{@code canvasY} are the JavaFX local coords
     * (bitmap pixels on a HiDPI backing store).
     */
    public static Point hitCell(Layout layout, Backing store, double canvasX, double canvasY) {
        if (layout == null) {
            return null;
        }
        double sx = store != null ? store.scaleX() : 1;
        double sy = store != null ? store.scaleY() : 1;
        return hitCell(layout, canvasX / sx, canvasY / sy);
    }

    public static Point hitCell(Layout layout, double x, double y) {
        if (layout == null) {
            return null;
        }
        int col = trackHit(layout.offX(), x - layout.offsetX());
        int row = trackHit(layout.offY(), y - layout.offsetY());
        if (row < 0 || col < 0) {
            return null;
        }
        return new Point(row, col);
    }

    private static int trackHit(double[] off, double v) {
        for (int i = 1; i < off.length; i += 2) {
            if (v >= off[i] && v < off[i + 1]) {
                return (i - 1) / 2;
            }
        }
        return -1;
    }

    /** One filled square in the 2r+1 / 2c+1 tile projection. */
    public record TileRect(int tileRow, int tileCol) {
    }

    /** Axis-aligned box for the player disc (inset from the passage tile). */
    public record Marker(double x, double y, double size) {
    }

    /** Stroke around the goal when the walk arrives — same 0.7·cell as {@code draw.js}. */
    public record Ring(double cx, double cy, double radius, double width) {
    }

    /** 1px highlight on a passage — same inset as {@code draw.js}. */
    public record Hairline(double x, double y, double w, double h) {
    }

    /**
     * Fog memory for a local walk. Stood-on cells plus the explorer —
     * same reveal contract as {@code draw.js} {@code fogRevealsTile}.
     */
    public record Fog(Set<String> seen, Point position, Point goal) {

        public static Fog of(List<Point> walk, Point position, Point goal) {
            Set<String> next = new HashSet<>();
            if (walk != null) {
                for (Point cell : walk) {
                    remember(next, cell);
                }
            }
            remember(next, position);
            return new Fog(Set.copyOf(next), position, goal);
        }

        public boolean seen(int row, int col) {
            return seen.contains(row + "," + col);
        }

        private static void remember(Set<String> into, Point cell) {
            if (cell != null) {
                into.add(cell.row() + "," + cell.col());
            }
        }
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
        return legendKeys(maze, path, walk, hotspot, null);
    }

    public static List<String> legendKeys(boolean maze, boolean path, boolean walk,
                                          boolean hotspot, Fog fog) {
        return legendKeys(maze, path, walk, hotspot, fog, false);
    }

    public static List<String> legendKeys(boolean maze, boolean path, boolean walk,
                                          boolean hotspot, Fog fog, boolean choke) {
        return legendKeys(maze, path, walk, hotspot, fog, choke, false);
    }

    public static List<String> legendKeys(boolean maze, boolean path, boolean walk,
                                          boolean hotspot, Fog fog, boolean choke,
                                          boolean hardest) {
        return legendKeys(maze, path, walk, hotspot, fog, choke, hardest, false);
    }

    public static List<String> legendKeys(boolean maze, boolean path, boolean walk,
                                          boolean hotspot, Fog fog, boolean choke,
                                          boolean hardest, boolean sanctuary) {
        return legendKeys(maze, path, walk, hotspot, fog, choke, hardest, sanctuary, false);
    }

    public static List<String> legendKeys(boolean maze, boolean path, boolean walk,
                                          boolean hotspot, Fog fog, boolean choke,
                                          boolean hardest, boolean sanctuary, boolean lens) {
        return legendKeys(maze, path, walk, hotspot, fog, choke, hardest, sanctuary, lens, false);
    }

    public static List<String> legendKeys(boolean maze, boolean path, boolean walk,
                                          boolean hotspot, Fog fog, boolean choke,
                                          boolean hardest, boolean sanctuary, boolean lens,
                                          boolean race) {
        return legendKeys(maze, path, walk, hotspot, fog, choke, hardest, sanctuary, lens, race,
                false);
    }

    public static List<String> legendKeys(boolean maze, boolean path, boolean walk,
                                          boolean hotspot, Fog fog, boolean choke,
                                          boolean hardest, boolean sanctuary, boolean lens,
                                          boolean race, boolean waypoint) {
        return legendKeys(maze, path, walk, hotspot, fog, choke, hardest, sanctuary, lens, race,
                waypoint, false);
    }

    public static List<String> legendKeys(boolean maze, boolean path, boolean walk,
                                          boolean hotspot, Fog fog, boolean choke,
                                          boolean hardest, boolean sanctuary, boolean lens,
                                          boolean race, boolean waypoint, boolean ghost) {
        return legendKeys(maze, path, walk, hotspot, fog, choke, hardest, sanctuary, lens, race,
                waypoint, ghost, false);
    }

    public static List<String> legendKeys(boolean maze, boolean path, boolean walk,
                                          boolean hotspot, Fog fog, boolean choke,
                                          boolean hardest, boolean sanctuary, boolean lens,
                                          boolean race, boolean waypoint, boolean ghost,
                                          boolean compare) {
        if (!maze) {
            return List.of();
        }
        List<String> keys = new ArrayList<>(List.of("floor", "wall"));
        if (fog == null || fog.position() != null || !fog.seen().isEmpty()) {
            keys.add("start");
        }
        if (fog == null || fog.goal() != null) {
            keys.add("goal");
        }
        if ((path || race || compare) && fog == null) {
            keys.add("path");
        }
        if (walk) {
            keys.add("player");
        }
        if (hotspot && fog == null) {
            keys.add("hotspot");
        }
        if (choke && fog == null) {
            keys.add("choke");
        }
        if (hardest && fog == null) {
            keys.add("hardest");
        }
        if (sanctuary && fog == null) {
            keys.add("sanctuary");
        }
        if (lens && fog == null) {
            keys.add("lens");
        }
        if (race && fog == null) {
            keys.add("race");
        }
        if (waypoint && fog == null) {
            keys.add("waypoint");
        }
        if (ghost && fog == null) {
            keys.add("ghost");
        }
        if (compare && fog == null) {
            keys.add("compare");
        }
        if (fog != null) {
            keys.add("fog");
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

    /** Cell wash plus the quieter openings — same two-pass as {@code draw.js}. */
    public record HotWash(List<Hotspot> cells, List<TileRect> openings) {
    }

    /**
     * Cell alpha from cost — {@code min(0.7, 0.2 + cost/200)}, same as the web.
     * A flat 0.4 made a cheap trap and an expensive one look identical.
     */
    public static double hotspotCellAlpha(double cost) {
        return Math.min(0.7, 0.2 + cost / 200.0);
    }

    /**
     * Hot-spot cells and the openings between adjacent ones. Rock and wall
     * cells stay void — same skip as {@code draw.js}.
     */
    public static HotWash hotspotWash(List<Hotspot> spots, TileType[][] tiles) {
        if (spots == null || spots.isEmpty() || tiles == null || tiles.length < 3) {
            return new HotWash(List.of(), List.of());
        }
        int rows = (tiles.length - 1) / 2;
        int cols = (tiles[0].length - 1) / 2;
        Set<String> live = new HashSet<>();
        List<Hotspot> cells = new ArrayList<>();
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
            cells.add(h);
        }
        List<TileRect> openings = new ArrayList<>();
        for (String key : live) {
            String[] parts = key.split(",");
            int r = Integer.parseInt(parts[0]);
            int c = Integer.parseInt(parts[1]);
            if (live.contains(r + "," + (c + 1)) && tiles[2 * r + 1][2 * c + 2] != TileType.WALL) {
                openings.add(new TileRect(2 * r + 1, 2 * c + 2));
            }
            if (live.contains((r + 1) + "," + c) && tiles[2 * r + 2][2 * c + 1] != TileType.WALL) {
                openings.add(new TileRect(2 * r + 2, 2 * c + 1));
            }
        }
        return new HotWash(List.copyOf(cells), List.copyOf(openings));
    }

    public static List<TileRect> hotspotOverlay(List<Hotspot> spots, TileType[][] tiles) {
        HotWash wash = hotspotWash(spots, tiles);
        List<TileRect> out = new ArrayList<>();
        for (Hotspot h : wash.cells()) {
            out.add(new TileRect(2 * h.row() + 1, 2 * h.col() + 1));
        }
        out.addAll(wash.openings());
        return List.copyOf(out);
    }

    /** Breadth-first field from the goal — same shape as {@code draw.js} {@code scene.field}. */
    public record Field(int maxDistance, int[][] distances) {

        public static Field of(int[][] distances) {
            if (distances == null || distances.length == 0) {
                return null;
            }
            int max = 0;
            for (int[] row : distances) {
                for (int d : row) {
                    if (d > max) {
                        max = d;
                    }
                }
            }
            return new Field(max, distances);
        }
    }

    /** One cell of the sequential ramp. {@code null} when the cell is unreachable rock. */
    public record FieldTone(String color, double alpha) {
    }

    public static FieldTone fieldCell(int distance, int maxDistance) {
        if (distance < 0) {
            return null;
        }
        int max = Math.max(1, maxDistance);
        double t = distance / (double) max;
        int i = Math.min(DISTANCE_RAMP.length - 1,
                (int) Math.round(t * (DISTANCE_RAMP.length - 1)));
        return new FieldTone(DISTANCE_RAMP[i], 0.12 + 0.68 * t);
    }

    public static String fieldOpeningColor() {
        int i = Math.min(DISTANCE_RAMP.length - 1,
                (int) Math.round(0.55 * (DISTANCE_RAMP.length - 1)));
        return DISTANCE_RAMP[i];
    }

    /**
     * Openings between reachable cells so the heat reads as a field, not
     * graph paper — same live-neighbor rule as {@code paintWashOpenings}.
     */
    public static List<TileRect> fieldOpenings(int[][] distances, TileType[][] tiles) {
        if (distances == null || tiles == null || distances.length == 0) {
            return List.of();
        }
        List<TileRect> out = new ArrayList<>();
        int rows = distances.length;
        int cols = distances[0].length;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (distances[r][c] < 0) {
                    continue;
                }
                if (c + 1 < cols && distances[r][c + 1] >= 0
                        && tiles[2 * r + 1][2 * c + 2] != TileType.WALL) {
                    out.add(new TileRect(2 * r + 1, 2 * c + 2));
                }
                if (r + 1 < rows && distances[r + 1][c] >= 0
                        && tiles[2 * r + 2][2 * c + 1] != TileType.WALL) {
                    out.add(new TileRect(2 * r + 2, 2 * c + 1));
                }
            }
        }
        return List.copyOf(out);
    }

    /**
     * Three A* bands — same wash as {@code draw.js} {@code scene.lens}.
     * Band 0 must expand, 1 tie, 2 never, −1 unreachable.
     */
    public record LensWash(int[][] bands, int mustExpand, int tie, int never,
                           int actualExpansions, int routeLength, int optimalCost,
                           boolean routeOptimal) {
    }

    /** Two recorded searches — same arena as {@code draw.js} {@code scene.race}. */
    public record RaceLane(String id, String color, List<Point> expansions, List<Point> path) {
        public RaceLane {
            expansions = expansions == null ? List.of() : List.copyOf(expansions);
            path = path == null ? List.of() : List.copyOf(path);
        }
    }

    public record Race(RaceLane first, RaceLane second) {
    }

    /** One solver's finished walk in a compare-all wash. */
    public record CompareLane(String id, String color, List<Point> path, boolean ok) {
        public CompareLane {
            path = path == null ? List.of() : List.copyOf(path);
        }
    }

    public record Compare(List<CompareLane> lanes) {
        public Compare {
            lanes = lanes == null ? List.of() : List.copyOf(lanes);
        }
    }

    /** Expansions per second — biggest lane takes at most 3.5s, same as {@code solve.js}. */
    public static double raceRate(int maxExpansions) {
        return Math.max(150.0, Math.max(1, maxExpansions) / 3.5);
    }

    public static List<Point> raceFront(List<Point> shown) {
        if (shown == null || shown.isEmpty()) {
            return List.of();
        }
        return List.copyOf(shown.subList(Math.max(0, shown.size() - RACE_FRONT), shown.size()));
    }

    public static String lensColor(int band) {
        if (band < 0 || band >= LENS_COLORS.length) {
            return null;
        }
        return LENS_COLORS[band];
    }

    public static double lensAlpha(int band) {
        if (band < 0) {
            return 0;
        }
        return band == 2 ? LENS_NEVER_ALPHA : LENS_MUST_ALPHA;
    }

    public static List<TileRect> lensOpenings(int[][] bands, TileType[][] tiles) {
        if (bands == null || tiles == null || bands.length == 0) {
            return List.of();
        }
        List<TileRect> out = new ArrayList<>();
        int rows = bands.length;
        int cols = bands[0].length;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (bands[r][c] < 0) {
                    continue;
                }
                if (c + 1 < cols && bands[r][c + 1] >= 0
                        && tiles[2 * r + 1][2 * c + 2] != TileType.WALL) {
                    out.add(new TileRect(2 * r + 1, 2 * c + 2));
                }
                if (r + 1 < rows && bands[r + 1][c] >= 0
                        && tiles[2 * r + 2][2 * c + 1] != TileType.WALL) {
                    out.add(new TileRect(2 * r + 2, 2 * c + 1));
                }
            }
        }
        return List.copyOf(out);
    }

    /** Min-cut passages plus dead-end specks — same overlay as {@code draw.js} analysis. */
    public record Cuts(int cutSize, List<MazeFlow.Passage> chokepoints, List<Point> deadEnds) {
    }

    /**
     * Halo plus core for one cut edge. Web paints the opening tile, then a
     * wall-width pad so the pinch reads as a seal, not a pixel.
     */
    public record ChokeMark(double x, double y, double w, double h,
                            double haloX, double haloY, double haloW, double haloH) {
    }

    public static TileRect chokeTile(MazeFlow.Passage passage) {
        if (passage == null || passage.a() == null || passage.b() == null) {
            return null;
        }
        return new TileRect(
                passage.a().row() + passage.b().row() + 1,
                passage.a().col() + passage.b().col() + 1);
    }

    public static ChokeMark chokeMark(Layout layout, MazeFlow.Passage passage) {
        TileRect tile = chokeTile(passage);
        if (layout == null || tile == null) {
            return null;
        }
        double x = layout.x(tile.tileCol());
        double y = layout.y(tile.tileRow());
        double w = layout.w(tile.tileCol());
        double h = layout.h(tile.tileRow());
        double pad = layout.wall();
        return new ChokeMark(x, y, w, h, x - pad, y - pad, w + 2 * pad, h + 2 * pad);
    }

    public static Marker deadEndMarker(Layout layout, Point cell) {
        return disc(layout, cell, 0.12);
    }

    /** k-center safe points — same mint discs and loneliest ring as {@code draw.js}. */
    public record Sanctuaries(List<Point> placements, int coveringRadius, Point worstServed) {
        public Sanctuaries {
            placements = placements == null ? List.of() : List.copyOf(placements);
        }

        public static Sanctuaries of(MazeGrid grid) {
            return of(grid, SANCTUARY_K);
        }

        public static Sanctuaries of(MazeGrid grid, int k) {
            FacilityPlacement.Placement placed = FacilityPlacement.kCenter(grid, k);
            return new Sanctuaries(placed.facilities(), placed.coveringRadius(),
                    loneliestCell(grid, placed.facilities()));
        }
    }

    /**
     * Waypoint hunt — same k-center coins and Held-Karp corridor as the web.
     * Start and goal are never coins.
     */
    public record Hunt(List<Point> waypoints, List<Point> path, int optimalCost,
                       boolean feasible) {
        public Hunt {
            waypoints = waypoints == null ? List.of() : List.copyOf(waypoints);
            path = path == null ? List.of() : List.copyOf(path);
        }

        public static Hunt of(MazeGrid grid) {
            return of(grid, WAYPOINT_K);
        }

        public static Hunt of(MazeGrid grid, int k) {
            FacilityPlacement.Placement placed = FacilityPlacement.kCenter(grid, k + 2);
            List<Point> coins = new ArrayList<>();
            for (Point cell : placed.facilities()) {
                if (cell.equals(grid.start()) || cell.equals(grid.goal())) {
                    continue;
                }
                coins.add(cell);
                if (coins.size() == k) {
                    break;
                }
            }
            List<Point> stops = new ArrayList<>(coins);
            stops.add(grid.goal());
            WaypointTour.Tour tour = WaypointTour.shortestTour(grid, grid.start(), stops);
            return new Hunt(coins, tour.path(), tour.totalCost(), tour.feasible());
        }

        /**
         * Placement is frozen; the optimum is not (ADR-014). A living tick
         * may open a cheaper corridor without moving the coins.
         */
        public static Hunt retarget(MazeGrid grid, List<Point> coins) {
            List<Point> kept = coins == null ? List.of() : List.copyOf(coins);
            if (grid == null) {
                return new Hunt(kept, List.of(), -1, false);
            }
            List<Point> stops = new ArrayList<>(kept);
            stops.add(grid.goal());
            WaypointTour.Tour tour = WaypointTour.shortestTour(grid, grid.start(), stops);
            return new Hunt(kept, tour.path(), tour.totalCost(), tour.feasible());
        }
    }

    /** Gold diamond — same 0.3·cell radius as {@code draw.js} waypoints. */
    public record Diamond(double cx, double cy, double radius, double stroke) {
    }

    public static Diamond waypointDiamond(Layout layout, Point cell) {
        if (layout == null || cell == null) {
            return null;
        }
        double cx = layout.x(2 * cell.col() + 1) + layout.cellSize() / 2.0;
        double cy = layout.y(2 * cell.row() + 1) + layout.cellSize() / 2.0;
        return new Diamond(cx, cy, layout.cellSize() * 0.3,
                Math.max(1.5, layout.cellSize() * 0.09));
    }

    public static Marker sanctuaryMarker(Layout layout, Point cell) {
        return disc(layout, cell, 0.32);
    }

    public static Ring worstServedRing(Layout layout, Point cell) {
        if (layout == null || cell == null) {
            return null;
        }
        double cx = layout.x(2 * cell.col() + 1) + layout.cellSize() / 2.0;
        double cy = layout.y(2 * cell.row() + 1) + layout.cellSize() / 2.0;
        return new Ring(cx, cy, layout.cellSize() * 0.36,
                Math.max(1.5, layout.cellSize() * 0.16));
    }

    /** The cell that owns the covering radius — same scan as the web topography note. */
    static Point loneliestCell(MazeGrid grid, List<Point> facilities) {
        if (grid == null || facilities == null || facilities.isEmpty()) {
            return null;
        }
        List<int[][]> fields = new ArrayList<>(facilities.size());
        for (Point facility : facilities) {
            fields.add(MazeMetrics.distancesFrom(grid, facility));
        }
        Point worst = facilities.get(0);
        int worstDistance = -1;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (grid.openNeighbors(new Point(r, c)).isEmpty()) {
                    continue;
                }
                int nearest = Integer.MAX_VALUE;
                for (int[][] field : fields) {
                    int d = field[r][c];
                    if (d >= 0 && d < nearest) {
                        nearest = d;
                    }
                }
                if (nearest != Integer.MAX_VALUE && nearest > worstDistance) {
                    worstDistance = nearest;
                    worst = new Point(r, c);
                }
            }
        }
        return worst;
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

    /**
     * First act of a recorded search — same budget as {@code solve.js}
     * {@code searchMs}. Zero expansions skips straight to the path.
     */
    public static int searchRevealMs(int expansionCount) {
        if (expansionCount <= 0) {
            return 0;
        }
        return Math.min(2200, Math.max(600, expansionCount * 6));
    }

    public static List<TileRect> expansionCells(List<Point> shown) {
        if (shown == null || shown.isEmpty()) {
            return List.of();
        }
        List<TileRect> out = new ArrayList<>();
        for (Point cell : shown) {
            if (cell != null) {
                out.add(new TileRect(2 * cell.row() + 1, 2 * cell.col() + 1));
            }
        }
        return List.copyOf(out);
    }

    /**
     * Openings between adjacent expanded cells — same live-neighbor rule
     * as {@code draw.js} {@code paintWashOpenings}.
     */
    public static List<TileRect> expansionOpenings(List<Point> shown, TileType[][] tiles) {
        if (shown == null || shown.isEmpty() || tiles == null || tiles.length < 3) {
            return List.of();
        }
        Set<String> live = new HashSet<>();
        for (Point cell : shown) {
            if (cell != null) {
                live.add(cell.row() + "," + cell.col());
            }
        }
        List<TileRect> openings = new ArrayList<>();
        for (Point cell : shown) {
            if (cell == null) {
                continue;
            }
            int r = cell.row();
            int c = cell.col();
            int east = 2 * c + 2;
            int south = 2 * r + 2;
            if (live.contains(r + "," + (c + 1)) && east < tiles[0].length
                    && tiles[2 * r + 1][east] != TileType.WALL) {
                openings.add(new TileRect(2 * r + 1, east));
            }
            if (live.contains((r + 1) + "," + c) && south < tiles.length
                    && tiles[south][2 * c + 1] != TileType.WALL) {
                openings.add(new TileRect(south, 2 * c + 1));
            }
        }
        return List.copyOf(openings);
    }

    /** Last six expanded cells — the moving front in {@code draw.js}. */
    public static List<Point> expansionFront(List<Point> shown) {
        if (shown == null || shown.isEmpty()) {
            return List.of();
        }
        return List.copyOf(shown.subList(Math.max(0, shown.size() - EXPANSION_FRONT),
                shown.size()));
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

    /**
     * Tip of a visible prefix — same cell as {@code draw.js} {@code walkHead}.
     */
    public static Point walkHead(List<Point> path) {
        if (path == null || path.isEmpty()) {
            return null;
        }
        return path.get(path.size() - 1);
    }

    public static Marker pathHeadMarker(Layout layout, List<Point> path) {
        return disc(layout, walkHead(path), 0.38);
    }

    public static Marker raceHeadMarker(Layout layout, List<Point> path) {
        return disc(layout, walkHead(path), 0.36);
    }

    public static Marker playerMarker(Layout layout, Point player) {
        return disc(layout, player, PLAYER_RADIUS);
    }

    public static Marker ghostMarker(Layout layout, Point cell) {
        return disc(layout, cell, GHOST_RADIUS);
    }

    /**
     * Walked prefix of a recording — same clock as {@code share.js} {@code ghostPrefix}.
     */
    public static List<Point> ghostPrefix(Point start, List<GameSession.TimedMove> moves,
                                          long elapsedMs) {
        if (start == null) {
            return List.of();
        }
        List<Point> pts = new ArrayList<>();
        pts.add(start);
        if (moves != null) {
            for (GameSession.TimedMove step : moves) {
                if (step == null || step.tMs() > elapsedMs) {
                    break;
                }
                pts.add(step.to());
            }
        }
        return List.copyOf(pts);
    }

    public static Point ghostHead(List<Point> prefix) {
        return walkHead(prefix);
    }

    public static Marker endpointMarker(Layout layout, Point cell) {
        return disc(layout, cell, 0.34);
    }

    public static Ring victoryRing(Layout layout, Point goal) {
        if (layout == null || goal == null) {
            return null;
        }
        double cx = layout.x(2 * goal.col() + 1) + layout.cellSize() / 2.0;
        double cy = layout.y(2 * goal.row() + 1) + layout.cellSize() / 2.0;
        return new Ring(cx, cy, layout.cellSize() * 0.7, Math.max(2.0, layout.wall()));
    }

    /**
     * Memory of stood-on cells, plus the wall segments that touch them.
     * Unseen stays void — same rules as {@code draw.js}.
     */
    public static boolean fogRevealsTile(Fog fog, int tileRow, int tileCol) {
        if (fog == null) {
            return true;
        }
        if (tileRow % 2 == 1 && tileCol % 2 == 1) {
            return fog.seen((tileRow - 1) / 2, (tileCol - 1) / 2);
        }
        if (tileRow % 2 == 1 && tileCol % 2 == 0) {
            int row = (tileRow - 1) / 2;
            int col = tileCol / 2;
            return fog.seen(row, col - 1) || fog.seen(row, col);
        }
        if (tileRow % 2 == 0 && tileCol % 2 == 1) {
            int row = tileRow / 2;
            int col = (tileCol - 1) / 2;
            return fog.seen(row - 1, col) || fog.seen(row, col);
        }
        int row = tileRow / 2;
        int col = tileCol / 2;
        return fog.seen(row - 1, col - 1) || fog.seen(row - 1, col)
                || fog.seen(row, col - 1) || fog.seen(row, col);
    }

    /**
     * Lamp falloff from the explorer. Stood-on memory stays visible;
     * cells underfoot read as the bright end of the corridor.
     */
    public static double fogLamp(Fog fog, int tileRow, int tileCol) {
        if (fog == null || fog.position() == null) {
            return 1;
        }
        Point at = fog.position();
        if (tileRow % 2 == 1 && tileCol % 2 == 1) {
            return nearestLamp(manhattan(at, (tileRow - 1) / 2, (tileCol - 1) / 2));
        }
        if (tileRow % 2 == 1 && tileCol % 2 == 0) {
            int row = (tileRow - 1) / 2;
            int col = tileCol / 2;
            return nearestLamp(manhattan(at, row, col - 1), manhattan(at, row, col));
        }
        if (tileRow % 2 == 0 && tileCol % 2 == 1) {
            int row = tileRow / 2;
            int col = (tileCol - 1) / 2;
            return nearestLamp(manhattan(at, row - 1, col), manhattan(at, row, col));
        }
        int row = tileRow / 2;
        int col = tileCol / 2;
        return nearestLamp(
                manhattan(at, row - 1, col - 1), manhattan(at, row - 1, col),
                manhattan(at, row, col - 1), manhattan(at, row, col));
    }

    public static String fogFloor(Fog fog, int tileRow, int tileCol) {
        return mixHex(FOG_FLOOR_DIM, FOG_FLOOR, fogLamp(fog, tileRow, tileCol));
    }

    public static boolean floorHi(Layout layout, int tileRow, int tileCol) {
        return floorHi(layout, tileRow, tileCol, 1);
    }

    public static boolean floorHi(Layout layout, int tileRow, int tileCol, double lamp) {
        return layout != null
                && tileRow % 2 == 1 && tileCol % 2 == 1
                && layout.cellSize() >= 10
                && lamp > 0.7;
    }

    public static boolean fogFloorHi(Layout layout, Fog fog, int tileRow, int tileCol) {
        return floorHi(layout, tileRow, tileCol, fogLamp(fog, tileRow, tileCol));
    }

    public static Hairline floorHiStroke(Layout layout, int tileRow, int tileCol) {
        return floorHiStroke(layout, tileRow, tileCol, 1);
    }

    public static Hairline floorHiStroke(Layout layout, int tileRow, int tileCol, double lamp) {
        if (!floorHi(layout, tileRow, tileCol, lamp)) {
            return null;
        }
        return new Hairline(
                layout.x(tileCol) + 1,
                layout.y(tileRow) + 1,
                Math.max(0, layout.cellSize() - 2),
                1);
    }

    static String mixHex(String from, String to, double t) {
        int[] a = rgb(from);
        int[] b = rgb(to);
        double u = Math.max(0, Math.min(1, t));
        return String.format("#%02x%02x%02x",
                (int) Math.round(a[0] + (b[0] - a[0]) * u),
                (int) Math.round(a[1] + (b[1] - a[1]) * u),
                (int) Math.round(a[2] + (b[2] - a[2]) * u));
    }

    private static int[] rgb(String hex) {
        String h = hex.charAt(0) == '#' ? hex.substring(1) : hex;
        return new int[] {
                Integer.parseInt(h.substring(0, 2), 16),
                Integer.parseInt(h.substring(2, 4), 16),
                Integer.parseInt(h.substring(4, 6), 16)
        };
    }

    private static int manhattan(Point at, int row, int col) {
        return Math.abs(row - at.row()) + Math.abs(col - at.col());
    }

    private static double nearestLamp(int... dists) {
        int min = Integer.MAX_VALUE;
        for (int d : dists) {
            min = Math.min(min, d);
        }
        return Math.max(0.38, 1 - 0.12 * min);
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
