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
import java.util.Arrays;
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
    /** Idle wordmark fill — warm cream, not cool slate on torch stone. */
    public static final String EMPTY_WORDMARK_INK = "#f2ead8";
    /** Same 0.22 as halls — leftover even cream is not the last word on an empty well. */
    public static String emptyWordmarkInk() {
        return mixHex(EMPTY_WORDMARK_INK, FLOOR_DIM, 0.22);
    }

    /** Same 0.22 as halls — leftover even mint is not the last word on an empty well. */
    public static String emptyWordmarkMintInk() {
        return mixHex(EMPTY_WORDMARK_GLOW, FLOOR_DIM, 0.22);
    }
    public static final String EMPTY_TITLE = "Pick a generator and click Generate";
    public static final String EMPTY_DETAIL = "then Solve to watch a route";
    public static final String EMPTY_HINT = "or walk with arrows or a click";
    /** Soft mint/gold aura — same tokens as the start-gate brand breath. */
    public static final String EMPTY_WORDMARK_GLOW = "#3ee08f";
    public static final double EMPTY_WORDMARK_GLOW_ALPHA = 0.32;
    public static final double EMPTY_WORDMARK_GLOW_RADIUS = 28;
    public static final String EMPTY_WORDMARK_GOLD = "#f5c14a";
    public static final double EMPTY_WORDMARK_GOLD_ALPHA = 0.18;
    public static final double EMPTY_WORDMARK_GOLD_RADIUS = 48;
    /** Same 4.5s gateBreath cadence as {@code draw.js} / {@code #gate .gate-brand}. */
    public static final double EMPTY_BREATH_MS = 4500;

    /** Smooth 0..1 wave — matches CSS ease-in-out gateBreath. */
    public static double emptyBreathWave(long nanos) {
        double t = ((nanos / 1_000_000.0) % EMPTY_BREATH_MS) / EMPTY_BREATH_MS;
        return 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
    }

    public static double emptyMintAlpha(double wave) {
        return 0.16 + 0.16 * wave;
    }

    public static double emptyGoldAlpha(double wave) {
        return 0.08 + 0.10 * wave;
    }

    public static double emptyMintRadius(double wave) {
        return 22 + 14 * wave;
    }

    public static double emptyGoldRadius(double wave) {
        return 48 + 24 * wave;
    }

    /** Soft mid-well mint wash under the mark — same gate wave. */
    public static double emptyGlowMintAlpha(double wave) {
        return 0.08 + 0.04 * wave;
    }

    public static double emptyGlowGoldAlpha(double wave) {
        return 0.04 + 0.03 * wave;
    }

    /** Idle lattice floors — same gate wave as the wordmark. */
    public static double emptyMarkFloorAlpha(double wave) {
        return 0.36 + 0.10 * wave;
    }

    /** Idle lattice walls — soft lift against the void so the miniature silhouettes. */
    public static double emptyMarkWallAlpha(double wave) {
        return 0.22 + 0.08 * wave;
    }

    /** Idle caption ink — gold chrome, not cool slate under the wordmark. */
    public static final String EMPTY_CAPTION_TITLE = "#b88538";
    public static final String EMPTY_CAPTION_DETAIL = "#8c764e";

    /** Idle caption under the wordmark — soft gate pulse, not stuck slate. */
    public static double emptyCaptionTitleAlpha(double wave) {
        return 0.72 + 0.18 * wave;
    }

    public static double emptyCaptionDetailAlpha(double wave) {
        return 0.55 + 0.20 * wave;
    }

    /** Desktop well gold rim — same 0.48↔0.72 band as web {@code stageRimBreath}. */
    public static double canvasRimAlpha(double wave) {
        return 0.48 + 0.24 * wave;
    }

    public static double canvasRimGlowRadius(double wave) {
        return 18 + 10 * wave;
    }

    public static double canvasRimGlowAlpha(double wave) {
        return 0.06 + 0.08 * wave;
    }

    /** Overlay legend labels — warm khaki, not cool slate on torch stone. */
    public static final String LEGEND_INK = "#b09a72";
    /** Export chip labels — same khaki as the legend so overlay copy is one lamp. */
    public static final String EXPORT_INK = LEGEND_INK;
    /** Legend fade ink — same warm void as the stage lip, not cool fog-black. */
    public static final int LEGEND_FADE_R = 16;
    public static final int LEGEND_FADE_G = 11;
    public static final int LEGEND_FADE_B = 8;

    /** Legend fade — same cadence as web {@code legendFadeBreath}. */
    public static double legendFadeMidAlpha(double wave) {
        return 0.50 + 0.12 * wave;
    }

    public static double legendFadeBotAlpha(double wave) {
        return 0.88 + 0.08 * wave;
    }

    /** Status / toolbar gold lip — same band as canvas rim. */
    public static double shellRimAlpha(double wave) {
        return canvasRimAlpha(wave);
    }

    /** Toolbar brand mint — same soft band as cosmic.css brand glow. */
    public static double brandMintAlpha(double wave) {
        return 0.20 + 0.16 * wave;
    }

    public static double brandMintRadius(double wave) {
        return 12 + 8 * wave;
    }

    /** Well export chip gold lip — same band as web {@code exportsRimBreath}. */
    public static double exportsRimAlpha(double wave) {
        return 0.36 + 0.19 * wave;
    }

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
    public static final double EMPTY_MARK_BUDGET_W = 200;
    public static final double EMPTY_MARK_BUDGET_H = 140;
    /** Idle mark sits above the wordmark — same lift as {@code draw.js} paintEmpty. */
    public static final double EMPTY_MARK_LIFT = 48;
    /** Overlay legend sits on the well — same reserve as {@code draw.js}. */
    public static final double LEGEND_RESERVE = 40;
    /** PNG sits on the well — same reserve as {@code draw.js} so the first row is not under it. */
    public static final double EXPORT_RESERVE = 28;
    /** Same gold as the web victory ring ({@code --gold}). */
    public static final String VICTORY_GOLD = "#f0b429";
    /** Soft glow under the victory stroke — same 0.85·cell pad as {@code draw.js}. */
    public static final double VICTORY_GLOW_RADIUS = 0.85;
    public static final double VICTORY_GLOW_ALPHA = 0.22;
    /** Soft pad under uncollected hunt coins — same as {@code draw.js}. */
    public static final double WAYPOINT_GLOW_PAD = 0.14;
    public static final double WAYPOINT_GLOW_ALPHA = 0.22;
    /** Win place pulse — same cadence idea as empty breath, a bit faster. */
    public static final double VICTORY_BREATH_MS = 2800;
    /** Uncollected loot pad pulse — same cadence as victory. */
    public static final double WAYPOINT_BREATH_MS = VICTORY_BREATH_MS;

    public static double victoryBreathWave(long nanos) {
        double t = ((nanos / 1_000_000.0) % VICTORY_BREATH_MS) / VICTORY_BREATH_MS;
        return 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
    }

    public static double waypointBreathWave(long nanos) {
        return victoryBreathWave(nanos);
    }

    public static double waypointGlowAlpha(double wave) {
        return 0.16 + 0.14 * wave;
    }

    public static double waypointGlowPad(double wave) {
        return WAYPOINT_GLOW_PAD + 0.05 * wave;
    }

    /** Collected mint pad — quieter than uncollected gold, still held. */
    public static double waypointGotGlowAlpha(double wave) {
        return 0.10 + 0.10 * wave;
    }

    public static double waypointGotStrokeAlpha(double wave) {
        return 0.72 + 0.28 * wave;
    }

    public static double victoryGlowAlpha(double wave) {
        return 0.14 + 0.16 * wave;
    }

    public static double victoryGlowRadius(double wave) {
        return VICTORY_GLOW_RADIUS + 0.08 * wave;
    }

    public static double victoryRingRadius(double wave) {
        return 0.70 + 0.04 * wave;
    }
    /** Unseen void — same warm well edge as {@code draw.js} and {@link #WELL_VOID_EDGE}. */
    public static final String FOG_UNSEEN = "#0c0908";
    /** Soft well pocket behind a letterboxed maze — same band as web {@code #stage}. */
    public static final String WELL_VOID_CENTER = "#16120e";
    public static final String WELL_VOID_EDGE = "#0c0908";
    /** Peak mid-glow of the void pocket — same lift as web {@code stageRimBreath}. */
    public static final String WELL_VOID_CENTER_LIT = "#1a1510";

    public static String wellVoidCenterInk(double wave) {
        return mixHex(WELL_VOID_CENTER, WELL_VOID_CENTER_LIT, Math.max(0, Math.min(1, wave)));
    }
    public static final String FOG_FLOOR_DIM = "#2a2218";
    /** Clear-board edge falloff toward dim torch stone — same ink as fog dim. */
    public static final String FLOOR_DIM = FOG_FLOOR_DIM;
    public static final double FLOOR_EDGE_DIM = 0.22;
    /** Clear-board wall rim toward unseen void — same depth idea as floors. */
    public static final double WALL_EDGE_DIM = 0.28;
    public static final String FOG_FLOOR = "#40403c";
    /** Torch-warm stone underfoot — same mix as {@code draw.js} floorWarm. */
    public static final String FOG_FLOOR_WARM = "#5c4a32";
    /** Idle lattice floors — same 0.28 warm mix as fog underfoot. */
    public static final String EMPTY_MARK_FLOOR = mixHex(FOG_FLOOR, FOG_FLOOR_WARM, 0.28);
    /** Soft rim at the memory edge — same falloff as {@code draw.js} FOG_FRONTIER. */
    public static final double FOG_FRONTIER = 0.72;
    /** Same 4.5s cadence as empty / gate place breath. */
    public static final double FOG_FRONTIER_BREATH_MS = EMPTY_BREATH_MS;

    public static double fogFrontierBreathWave(long nanos) {
        return emptyBreathWave(nanos);
    }

    public static double fogFrontierDim(double wave) {
        return FOG_FRONTIER * (0.92 + 0.16 * wave);
    }
    /** Torch-dark wall ink — same token as {@code draw.js} wall. */
    public static final String FOG_WALL = "#120e0c";
    /** Theme-less fallback — same torch wall as the live well, not cool gray. */
    public static final String THEMELESS_WALL = FOG_WALL;
    /** Theme-less fallback — same torch floor as the live well, not cool gray. */
    public static final String THEMELESS_FLOOR = FOG_FLOOR;
    /** Torch-warm wall — same mix as {@code draw.js} wallWarm. */
    public static final String FOG_WALL_WARM = "#2a2218";
    /** Idle lattice walls — torch-warm stone, not the void color. */
    public static final String EMPTY_MARK_WALL = FOG_WALL_WARM;
    /** Overlay legend floor — same 0.28 warm mix the live well paints. */
    public static final String LEGEND_FLOOR = EMPTY_MARK_FLOOR;
    /** Overlay legend wall — same 0.28 warm mix as clear-board posts. */
    public static final String LEGEND_WALL = mixHex(FOG_WALL, FOG_WALL_WARM, 0.28);
    /** Legend floor chip rim — same dim as live hall edge. */
    public static final String LEGEND_FLOOR_RIM = FLOOR_DIM;
    /** Legend wall chip rim — same unseen mix as live post edge. */
    public static final String LEGEND_WALL_RIM = mixHex(LEGEND_WALL, FOG_UNSEEN, WALL_EDGE_DIM);
    /** Legend fog chip rim — same unseen as the well void edge. */
    public static final String LEGEND_FOG = WELL_VOID_EDGE;
    /** Legend fog chip core — same pocket as the well void center. */
    public static final String LEGEND_FOG_CORE = WELL_VOID_CENTER;
    /** Same 1px corridor highlight as {@code draw.js} {@code floorHi}. */
    public static final String FLOOR_HI = "#765834";
    /** Post shine — same 1px torch hairline as {@code draw.js} {@code wallHi}. */
    public static final String WALL_HI = "#4a3824";
    public static final String FOG_FLOOR_HI = FLOOR_HI;

    /** Corridor shine softens toward the board edge with the floor wash. */
    public static String floorHiInk(double edge) {
        return mixHex(FLOOR_HI, FLOOR_DIM, FLOOR_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }

    /**
     * Clear-board floor — same 0.28 torch mix as fog underfoot, then edge falloff.
     */
    public static String clearFloorInk(double edge) {
        String warm = mixHex(FOG_FLOOR, FOG_FLOOR_WARM, 0.28);
        return mixHex(warm, FLOOR_DIM, FLOOR_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }

    /** KEEP start mint / goal coral — same wash as explore {@code FLOOR_END_WEIGHT}. */
    public static final String START_INK = "#3ee08f";
    public static final String GOAL_INK = "#ff5a5f";
    public static final double FLOOR_END_WEIGHT = 0.42;

    /** Same 0.22 rim as halls — leftover even mint is not the last word on a begin. */
    public static String startInk(double edge) {
        return walkTrailInk(START_INK, edge);
    }

    /** Same 0.22 rim as halls — leftover even coral is not the last word on a finish. */
    public static String goalInk(double edge) {
        return walkTrailInk(GOAL_INK, edge);
    }

    public static String endFloorInk(String base, TileType tile) {
        if (base == null) {
            return null;
        }
        if (tile == TileType.START) {
            return mixHex(base, START_INK, FLOOR_END_WEIGHT);
        }
        if (tile == TileType.GOAL) {
            return mixHex(base, GOAL_INK, FLOOR_END_WEIGHT);
        }
        return base;
    }

    /** Clear-board hairline — warm shine, then the same edge falloff. */
    public static String clearFloorHiInk(double edge) {
        String hi = mixHex(FLOOR_HI, FOG_FLOOR_WARM, 0.28);
        return mixHex(hi, FLOOR_DIM, FLOOR_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }

    /** Fog corridor shine warms with the lamp — same 0.28 weight as underfoot. */
    public static String fogFloorHiInk(double intensity) {
        return fogFloorHiInk(intensity, 0);
    }

    public static String fogFloorHiInk(double intensity, double edge) {
        String hi = mixHex(FLOOR_HI, FOG_FLOOR_WARM,
                0.28 * Math.max(0, Math.min(1, intensity)));
        return mixHex(hi, FLOOR_DIM, FLOOR_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }

    /** Clear wall ink — torch-warm posts, then darker toward unseen at the rim. */
    public static String wallInk(double edge) {
        String warm = mixHex(FOG_WALL, FOG_WALL_WARM, 0.28);
        return mixHex(warm, FOG_UNSEEN, WALL_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }
    /** Coral wash — same token as {@code draw.js} hot spots. */
    public static final String HOTSPOT = "#e5484d";
    /** Same 0.22 rim as halls — leftover even heat is not the last word on a lamp-warm tile. */
    public static final double HOTSPOT_EDGE_DIM = 0.22;

    public static String hotspotInk(double edge) {
        return mixHex(HOTSPOT, FLOOR_DIM, HOTSPOT_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }

    /** Opening wash between adjacent spots — same alpha as {@code draw.js}. */
    public static final double HOTSPOT_OPENING_ALPHA = 0.35;
    /** Congestion pulse — same cadence as victory / hunt loot. */
    public static final double HOTSPOT_BREATH_MS = VICTORY_BREATH_MS;
    public static final double HOTSPOT_RIM_RADIUS = 0.18;

    public static double hotspotBreathWave(long nanos) {
        return victoryBreathWave(nanos);
    }

    public static double hotspotCellPaintAlpha(double cost, double wave) {
        return hotspotCellAlpha(cost) * (0.88 + 0.24 * wave);
    }

    public static double hotspotOpeningPaintAlpha(double wave) {
        return HOTSPOT_OPENING_ALPHA * (0.85 + 0.30 * wave);
    }

    public static double hotspotPadAlpha(double wave) {
        return 0.16 + 0.12 * wave;
    }

    public static double hotspotPadRadius(double wave) {
        return 0.28 + 0.04 * wave;
    }

    public static double hotspotRimAlpha(double wave) {
        return 0.45 + 0.20 * wave;
    }

    /** Soft pad / rim around a jam cell — place, not a flat coral slab. */
    public static Marker hotspotPad(Layout layout, Point cell, double wave) {
        return disc(layout, cell, hotspotPadRadius(wave));
    }

    public static Ring hotspotRim(Layout layout, Point cell) {
        if (layout == null || cell == null) {
            return null;
        }
        double cx = layout.x(2 * cell.col() + 1) + layout.cellSize() / 2.0;
        double cy = layout.y(2 * cell.row() + 1) + layout.cellSize() / 2.0;
        return new Ring(cx, cy, layout.cellSize() * HOTSPOT_RIM_RADIUS,
                Math.max(1.0, layout.cellSize() * 0.06));
    }
    /** Solver ribbon — same alpha as {@code draw.js} {@code paintWalk}. */
    public static final double PATH_ALPHA = 0.85;
    /** Same ice as well {@code COLORS.path}. */
    public static final String PATH = "#8fb8ff";

    public static String expansionInk(double edge) {
        return fieldInk(PATH, edge);
    }
    /** Same torch gold as {@code draw.js} {@code PLAYER_COLORS[0]}. */
    public static final String PLAYER = "#f5c14a";

    public static String playerInk(double edge) {
        return walkTrailInk(PLAYER, edge);
    }
    /** Same radius as {@code draw.js} session / fog player. */
    public static final double PLAYER_RADIUS = 0.42;
    /** Walker glow breath — same gate cadence as ghost / endpoints. */
    public static final double PLAYER_BREATH_MS = EMPTY_BREATH_MS;

    public static double playerBreathWave(long nanos) {
        return emptyBreathWave(nanos);
    }

    public static double playerGlowAlpha(double wave) {
        return 0.16 + 0.12 * wave;
    }

    public static double playerGlowPadFraction(double wave) {
        return 0.32 + 0.08 * wave;
    }

    public static double playerRimAlpha(double wave) {
        return 0.55 + 0.20 * wave;
    }
    /** Search wash — same alphas as {@code draw.js} expansions. */
    public static final double EXPANSION_ALPHA = 0.16;
    /** Openings louder than cells — same idea as Compare, quieter than the ribbon. */
    public static final double EXPANSION_OPENING_ALPHA = 0.26;
    public static final double EXPANSION_FRONT_ALPHA = 0.45;
    public static final int EXPANSION_FRONT = 6;
    /** Expansion-front pulse — same cadence as victory / lens. */
    public static final double EXPANSION_BREATH_MS = VICTORY_BREATH_MS;

    public static double expansionBreathWave(long nanos) {
        return victoryBreathWave(nanos);
    }

    public static double expansionFrontPaintAlpha(double wave) {
        return EXPANSION_FRONT_ALPHA * (0.88 + 0.24 * wave);
    }

    public static double expansionWashPaintAlpha(double wave) {
        return EXPANSION_ALPHA * (0.88 + 0.24 * wave);
    }

    public static double expansionOpeningPaintAlpha(double wave) {
        return EXPANSION_OPENING_ALPHA * (0.85 + 0.30 * wave);
    }
    /**
     * Sequential distance ramp — bit-identical to {@code caption.js}
     * {@code DISTANCE_RAMP}. Torch amber, monotone in lightness.
     */
    public static final String[] DISTANCE_RAMP = {
            "#4a2210", "#6e3014", "#943c18", "#b85a20",
            "#d47828", "#e09840", "#e8b868", "#f2d8a0"
    };
    /** Opening wash for the field — same alpha as {@code draw.js}. */
    public static final double FIELD_OPENING_ALPHA = 0.42;
    /** Heat wash pulse — same cadence as victory / jam. */
    public static final double FIELD_BREATH_MS = VICTORY_BREATH_MS;

    public static double fieldBreathWave(long nanos) {
        return victoryBreathWave(nanos);
    }

    public static double fieldPaintAlpha(double base, double wave) {
        return base * (0.88 + 0.24 * wave);
    }

    public static double fieldOpeningPaintAlpha(double wave) {
        return FIELD_OPENING_ALPHA * (0.85 + 0.30 * wave);
    }
    /**
     * Heuristic lens bands — bit-identical to {@code caption.js} {@code LENS_COLORS}.
     * Must, tie, never.
     */
    public static final String[] LENS_COLORS = {"#e5484d", "#f2c94c", "#8aaa50"};
    public static final double LENS_MUST_ALPHA = 0.42;
    public static final double LENS_NEVER_ALPHA = 0.16;
    public static final double LENS_OPENING_ALPHA = 0.2;
    /** Lens wash pulse — same cadence as victory / field. */
    public static final double LENS_BREATH_MS = VICTORY_BREATH_MS;

    public static double lensBreathWave(long nanos) {
        return victoryBreathWave(nanos);
    }

    public static double lensPaintAlpha(int band, double wave) {
        return lensAlpha(band) * (0.88 + 0.24 * wave);
    }

    public static double lensOpeningPaintAlpha(double wave) {
        return LENS_OPENING_ALPHA * (0.85 + 0.30 * wave);
    }
    /** Arena lanes — KEEP overlay ice, same as the solver ribbon, not leftover ice. */
    public static final String RACE_A = "#8fb8ff";
    public static final String RACE_B = "#f0b429";
    public static final double RACE_WASH = 0.13;
    /** Openings louder than cells — same idea as search wash, quieter than the ribbon. */
    public static final double RACE_OPENING_ALPHA = 0.20;
    public static final double RACE_FRONT_ALPHA = 0.4;
    public static final int RACE_FRONT = 5;
    /** Race-front pulse — same cadence as expansion front. */
    public static final double RACE_BREATH_MS = VICTORY_BREATH_MS;

    public static double raceBreathWave(long nanos) {
        return victoryBreathWave(nanos);
    }

    public static double raceFrontPaintAlpha(double wave) {
        return RACE_FRONT_ALPHA * (0.88 + 0.24 * wave);
    }

    public static double raceWashPaintAlpha(double wave) {
        return RACE_WASH * (0.88 + 0.24 * wave);
    }

    public static double raceOpeningPaintAlpha(double wave) {
        return RACE_OPENING_ALPHA * (0.85 + 0.30 * wave);
    }
    public static final double RACE_PATH_A = 0.85;
    public static final double RACE_PATH_B = 0.58;
    /**
     * Compare-all routes — first three stay overlay ice / gold / coral;
     * leftover seats wear named lamp inks, not leftover mint and purple.
     */
    public static final String[] COMPARE = {
            "#8fb8ff", "#f0b429", "#e5484d", "#8aaa50", "#c07850", "#d4b06a"
    };
    public static final double COMPARE_ALPHA = 0.22;
    /** Opening wash between adjacent compare cells — louder than the cell wash. */
    public static final double COMPARE_OPENING_ALPHA = 0.34;
    /** Compare wash pulse — same cadence as race / expansion front. */
    public static final double COMPARE_BREATH_MS = VICTORY_BREATH_MS;

    public static double compareBreathWave(long nanos) {
        return victoryBreathWave(nanos);
    }

    public static double comparePaintAlpha(double wave) {
        return COMPARE_ALPHA * (0.88 + 0.24 * wave);
    }

    public static double compareOpeningPaintAlpha(double wave) {
        return COMPARE_OPENING_ALPHA * (0.85 + 0.30 * wave);
    }
    /** Tip disc on each finished route — smaller than race so washes stay readable. */
    public static final double COMPARE_HEAD_RADIUS = 0.28;

    /**
     * Every compare seat shares the 0.22 hall rim — leftover even ice
     * is not the last word on a split.
     */
    public static String compareWashInk(String color, double edge) {
        if (color == null) {
            return color;
        }
        return walkTrailInk(color, edge);
    }
    /** Min-cut passage — same purple as {@code draw.js} chokepoints. */
    public static final String CHOKE = "#c07850";
    /** Same 0.22 rim as halls — leftover even clay is not the last word on a pinch. */
    public static final double CHOKE_EDGE_DIM = 0.22;

    public static String chokeInk(double edge) {
        return mixHex(CHOKE, FLOOR_DIM, CHOKE_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }

    /** Dead-end speck — same ice as {@code draw.js}. */
    public static final String DEAD_END = "#c8a878";
    /** Same 0.22 rim as halls — leftover even khaki is not the last word on a cul-de-sac. */
    public static final double DEAD_END_EDGE_DIM = 0.22;

    public static String deadEndInk(double edge) {
        return mixHex(DEAD_END, FLOOR_DIM, DEAD_END_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }

    public static final double DEAD_END_RADIUS = 0.14;
    public static final double DEAD_END_HALO = 0.28;
    public static final double DEAD_END_HALO_ALPHA = 0.22;
    public static final double DEAD_END_CORE_ALPHA = 0.55;
    public static final double DEAD_END_RIM_ALPHA = 0.65;
    /** Hardest simple route — same gold as {@code draw.js}. */
    public static final String HARDEST = "#f2c94c";
    public static final double HARDEST_ALPHA = 0.75;
    /** Sanctuary disc — same moss as {@code draw.js}. */
    public static final String SANCTUARY = "#8aaa50";
    /** Same 0.22 rim as halls — leftover even moss is not the last word on a hold. */
    public static final double SANCTUARY_EDGE_DIM = 0.22;

    public static String sanctuaryInk(double edge) {
        return mixHex(SANCTUARY, FLOOR_DIM, SANCTUARY_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }

    /** Loneliest cell — same coral stroke as {@code draw.js}. */
    public static final String WORST_SERVED = "#e5484d";
    /** Same k as the web Place sanctuaries button. */
    public static final int SANCTUARY_K = 5;
    /** Held-Karp corridor — same amber as {@code draw.js} {@code tourPath}. */
    public static final String TOUR = "#d4b06a";
    public static final double TOUR_ALPHA = 0.38;
    /** Uncollected coin — same gold diamond as {@code draw.js}. */
    public static final String WAYPOINT = "#f2c94c";
    public static final String WAYPOINT_GOT = "#8aaa50";
    /** Same 0.22 rim as halls — leftover even gold/moss is not the last word on a stop. */
    public static final double WAYPOINT_EDGE_DIM = 0.22;

    public static String waypointInk(boolean collected, double edge) {
        return mixHex(collected ? WAYPOINT_GOT : WAYPOINT, FLOOR_DIM,
                WAYPOINT_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }
    /** Same k as the web Hunt button. */
    public static final int WAYPOINT_K = 5;
    /** Recorded racer — warm parchment, not leftover cool white on torch stone. */
    public static final String GHOST = "#e8e0d4";
    /** Same 0.22 rim as halls — leftover even parchment is not the last word on a replay head. */
    public static final double GHOST_EDGE_DIM = 0.22;

    public static String ghostInk(double edge) {
        return mixHex(GHOST, FLOOR_DIM, GHOST_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }

    /** Ghost trail tiles share the disc rim toward floor-dim. */
    public static String walkTrailInk(String color, double edge) {
        if (color == null) {
            return null;
        }
        return mixHex(color, FLOOR_DIM, GHOST_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }

    public static final double GHOST_WALK_ALPHA = 0.28;
    /** Fog / session / ghost trail base — same as {@code draw.js}. */
    public static final double WALK_TRAIL_ALPHA = 0.32;

    /** Age fade — recent steps near the walker stay bright; older corridor softens. */
    public static double walkTrailAlpha(double base, int index, int length) {
        if (length <= 1) {
            return base;
        }
        double fade = 0.35 + 0.65 * ((index + 1.0) / length);
        return base * fade;
    }

    /** Solver ribbon — softer toward the start, tip stays full (quieter than walk age-fade). */
    public static double pathRibbonAlpha(double base, int index, int length) {
        if (length <= 1) {
            return base;
        }
        double fade = 0.55 + 0.45 * ((index + 1.0) / length);
        return base * fade;
    }
    public static final double GHOST_DISC_ALPHA = 0.55;
    public static final double GHOST_GLOW_ALPHA = 0.18;
    public static final double GHOST_RIM_ALPHA = 0.65;
    public static final double GHOST_RADIUS = 0.3;
    /** Same 4.5s cadence as empty / gate / endpoint breath. */
    public static final double GHOST_BREATH_MS = EMPTY_BREATH_MS;

    public static double ghostBreathWave(long nanos) {
        return emptyBreathWave(nanos);
    }

    public static double ghostGlowAlpha(double wave) {
        return GHOST_GLOW_ALPHA + 0.08 * wave;
    }

    public static double ghostGlowPadFraction(double wave) {
        return 0.32 + 0.08 * wave;
    }

    public static double ghostDiscAlpha(double wave) {
        return GHOST_DISC_ALPHA + 0.08 * wave;
    }

    public static double ghostRimAlpha(double wave) {
        return GHOST_RIM_ALPHA + 0.1 * wave;
    }

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
        return legendKeys(maze, path, walk, hotspot, fog, choke, hardest, sanctuary, lens, race,
                waypoint, ghost, compare, false);
    }

    public static List<String> legendKeys(boolean maze, boolean path, boolean walk,
                                          boolean hotspot, Fog fog, boolean choke,
                                          boolean hardest, boolean sanctuary, boolean lens,
                                          boolean race, boolean waypoint, boolean ghost,
                                          boolean compare, boolean deadend) {
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
        if (deadend && fog == null) {
            keys.add("deadend");
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
            keys.add("tour");
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

    public static final double FIELD_EDGE_DIM = 0.22;

    public static String fieldInk(String color, double edge) {
        if (color == null) {
            return null;
        }
        return mixHex(color, FLOOR_DIM, FIELD_EDGE_DIM * Math.max(0, Math.min(1, edge)));
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

    /** Soft place ring on a cut — same language as {@code draw.js} choke arcs. */
    public static final double CHOKE_CORE = 0.55;
    public static final double CHOKE_HALO_PAD = 0.18;
    public static final double CHOKE_HALO_ALPHA = 0.22;
    public static final double CHOKE_RING_ALPHA = 0.72;
    /** Same 4.5s cadence as empty / gate / sanctuary place breath. */
    public static final double CUTS_BREATH_MS = EMPTY_BREATH_MS;

    public static double cutsBreathWave(long nanos) {
        return emptyBreathWave(nanos);
    }

    public static double chokeHaloPad(double wave) {
        return CHOKE_HALO_PAD + 0.05 * wave;
    }

    public static double chokeHaloAlpha(double wave) {
        return 0.16 + 0.12 * wave;
    }

    public static double chokeRingAlpha(double wave) {
        return CHOKE_RING_ALPHA + 0.18 * wave;
    }

    public static double deadEndHaloRadius(double wave) {
        return DEAD_END_HALO + 0.04 * wave;
    }

    public static double deadEndHaloAlpha(double wave) {
        return 0.16 + 0.12 * wave;
    }

    public static double deadEndCoreAlpha(double wave) {
        return DEAD_END_CORE_ALPHA + 0.10 * wave;
    }

    public static double deadEndRimAlpha(double wave) {
        return DEAD_END_RIM_ALPHA + 0.15 * wave;
    }

    public static Ring chokeHalo(Layout layout, MazeFlow.Passage passage) {
        return chokeHalo(layout, passage, 0);
    }

    public static Ring chokeHalo(Layout layout, MazeFlow.Passage passage, double wave) {
        ChokeMark mark = chokeMark(layout, passage);
        if (layout == null || mark == null) {
            return null;
        }
        double cx = mark.x() + mark.w() / 2.0;
        double cy = mark.y() + mark.h() / 2.0;
        double core = Math.max(mark.w(), mark.h()) * CHOKE_CORE;
        return new Ring(cx, cy, core + layout.cellSize() * chokeHaloPad(wave),
                Math.max(1.5, layout.cellSize() * 0.1));
    }

    public static Ring chokeRing(Layout layout, MazeFlow.Passage passage) {
        ChokeMark mark = chokeMark(layout, passage);
        if (layout == null || mark == null) {
            return null;
        }
        double cx = mark.x() + mark.w() / 2.0;
        double cy = mark.y() + mark.h() / 2.0;
        double core = Math.max(mark.w(), mark.h()) * CHOKE_CORE;
        return new Ring(cx, cy, core, Math.max(1.5, layout.cellSize() * 0.1));
    }

    public static Marker deadEndMarker(Layout layout, Point cell) {
        return disc(layout, cell, DEAD_END_RADIUS);
    }

    public static Marker deadEndHalo(Layout layout, Point cell) {
        return deadEndHalo(layout, cell, 0);
    }

    public static Marker deadEndHalo(Layout layout, Point cell, double wave) {
        return disc(layout, cell, deadEndHaloRadius(wave));
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

    /** Same 4.5s cadence as empty / gate / endpoint breath. */
    public static final double SANCTUARY_BREATH_MS = EMPTY_BREATH_MS;

    public static double sanctuaryBreathWave(long nanos) {
        return emptyBreathWave(nanos);
    }

    public static double sanctuaryRingRadius(double wave) {
        return 0.48 + 0.05 * wave;
    }

    public static double sanctuaryRingAlpha(double wave) {
        return 0.26 + 0.16 * wave;
    }

    /** Soft pad under the mint disc — same band as web {@code marker} glow. */
    public static double sanctuaryGlowAlpha(double wave) {
        return 0.16 + 0.12 * wave;
    }

    public static double sanctuaryGlowPad(double wave) {
        return 0.22 + 0.04 * wave;
    }

    public static Marker sanctuaryGlow(Layout layout, Point cell, double wave) {
        return disc(layout, cell, 0.32 + sanctuaryGlowPad(wave));
    }

    public static double worstServedRingRadius(double wave) {
        return 0.36 + 0.05 * wave;
    }

    public static double worstServedRingAlpha(double wave) {
        return 0.72 + 0.28 * wave;
    }

    public static Ring sanctuaryRing(Layout layout, Point cell) {
        return sanctuaryRing(layout, cell, 0);
    }

    public static Ring sanctuaryRing(Layout layout, Point cell, double wave) {
        if (layout == null || cell == null) {
            return null;
        }
        double cx = layout.x(2 * cell.col() + 1) + layout.cellSize() / 2.0;
        double cy = layout.y(2 * cell.row() + 1) + layout.cellSize() / 2.0;
        return new Ring(cx, cy, layout.cellSize() * sanctuaryRingRadius(wave),
                Math.max(1.5, layout.cellSize() * 0.08));
    }

    public static Ring worstServedRing(Layout layout, Point cell) {
        return worstServedRing(layout, cell, 0);
    }

    public static Ring worstServedRing(Layout layout, Point cell, double wave) {
        if (layout == null || cell == null) {
            return null;
        }
        double cx = layout.x(2 * cell.col() + 1) + layout.cellSize() / 2.0;
        double cy = layout.y(2 * cell.row() + 1) + layout.cellSize() / 2.0;
        return new Ring(cx, cy, layout.cellSize() * worstServedRingRadius(wave),
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

    /** Outer ring around start / goal — same 0.55·cell as {@code draw.js} endpoint. */
    public static Ring endpointRing(Layout layout, Point cell) {
        return endpointRing(layout, cell, 0);
    }

    public static Ring endpointRing(Layout layout, Point cell, double wave) {
        if (layout == null || cell == null) {
            return null;
        }
        double cx = layout.x(2 * cell.col() + 1) + layout.cellSize() / 2.0;
        double cy = layout.y(2 * cell.row() + 1) + layout.cellSize() / 2.0;
        return new Ring(cx, cy, layout.cellSize() * endpointRingRadius(wave),
                Math.max(1.5, layout.cellSize() * 0.09));
    }

    /** Same 4.5s cadence as empty / gate breath. */
    public static final double ENDPOINT_BREATH_MS = EMPTY_BREATH_MS;

    public static double endpointBreathWave(long nanos) {
        return emptyBreathWave(nanos);
    }

    public static double endpointRingRadius(double wave) {
        return 0.55 + 0.06 * wave;
    }

    public static double endpointRingAlpha(double wave) {
        return 0.32 + 0.18 * wave;
    }

    /** Soft pad under start / goal — same band as web {@code marker} glow. */
    public static double endpointGlowAlpha(double wave) {
        return 0.16 + 0.12 * wave;
    }

    public static double endpointGlowPadFraction(double wave) {
        return 0.32 + 0.08 * wave;
    }

    public static double endpointCoreRimAlpha(double wave) {
        return 0.55 + 0.20 * wave;
    }

    /** Living tip pulse — same cadence as victory / hunt loot. */
    public static final double PATH_HEAD_BREATH_MS = VICTORY_BREATH_MS;

    public static double pathHeadBreathWave(long nanos) {
        return victoryBreathWave(nanos);
    }

    public static double pathHeadHaloRadius(double wave) {
        return 0.5 + 0.05 * wave;
    }

    public static double pathHeadHaloAlpha(double wave) {
        return 0.28 + 0.16 * wave;
    }

    public static double pathHeadGlowAlpha(double wave) {
        return 0.22 + 0.10 * wave;
    }

    public static double pathHeadGlowPadFraction(double wave) {
        return 0.32 + 0.08 * wave;
    }

    public static double pathHeadRimAlpha(double wave) {
        return 0.65 + 0.15 * wave;
    }

    /** Soft halo at the tip of an unfolding route — same band as {@code draw.js} pathHead. */
    public static Ring pathHeadHalo(Layout layout, Point cell) {
        return pathHeadHalo(layout, cell, 0);
    }

    public static Ring pathHeadHalo(Layout layout, Point cell, double wave) {
        if (layout == null || cell == null) {
            return null;
        }
        double cx = layout.x(2 * cell.col() + 1) + layout.cellSize() / 2.0;
        double cy = layout.y(2 * cell.row() + 1) + layout.cellSize() / 2.0;
        return new Ring(cx, cy, layout.cellSize() * pathHeadHaloRadius(wave),
                Math.max(1.5, layout.cellSize() * 0.1));
    }

    /** Soft gold wash under the victory stroke — same pad as {@code draw.js}. */
    public static Marker victoryGlow(Layout layout, Point goal) {
        return victoryGlow(layout, goal, 0);
    }

    public static Marker victoryGlow(Layout layout, Point goal, double wave) {
        return disc(layout, goal, victoryGlowRadius(wave));
    }

    public static Ring victoryRing(Layout layout, Point goal) {
        return victoryRing(layout, goal, 0);
    }

    public static Ring victoryRing(Layout layout, Point goal, double wave) {
        if (layout == null || goal == null) {
            return null;
        }
        double cx = layout.x(2 * goal.col() + 1) + layout.cellSize() / 2.0;
        double cy = layout.y(2 * goal.row() + 1) + layout.cellSize() / 2.0;
        return new Ring(cx, cy, layout.cellSize() * victoryRingRadius(wave),
                Math.max(2.0, layout.wall()));
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

    /** Soft rim at the memory edge — light falloff, not a hard stencil. */
    public static double fogFrontier(Fog fog, int tileRow, int tileCol) {
        return fogFrontier(fog, tileRow, tileCol, fogFrontierBreathWave(System.nanoTime()));
    }

    public static double fogFrontier(Fog fog, int tileRow, int tileCol, double wave) {
        if (fog == null || !fogRevealsTile(fog, tileRow, tileCol)) {
            return 1;
        }
        int[][] n = {{0, 1}, {0, -1}, {1, 0}, {-1, 0}};
        for (int[] d : n) {
            if (!fogRevealsTile(fog, tileRow + d[0], tileCol + d[1])) {
                return fogFrontierDim(wave);
            }
        }
        return 1;
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
        return fogFloor(fog, tileRow, tileCol, 0);
    }

    public static String fogFloor(Fog fog, int tileRow, int tileCol, double edge) {
        double lamp = fogLamp(fog, tileRow, tileCol) * fogFrontier(fog, tileRow, tileCol);
        String lit = mixHex(FOG_FLOOR, FOG_FLOOR_WARM, 0.28 * lamp);
        String lampFloor = mixHex(FOG_FLOOR_DIM, lit, lamp);
        return mixHex(lampFloor, FLOOR_DIM, FLOOR_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }

    /** Revealed wall near the lamp warms toward torch-brown — same as {@code draw.js}. */
    public static String fogWall(Fog fog, int tileRow, int tileCol) {
        return fogWall(fog, tileRow, tileCol, 0);
    }

    public static String fogWall(Fog fog, int tileRow, int tileCol, double edge) {
        double lamp = fogLamp(fog, tileRow, tileCol) * fogFrontier(fog, tileRow, tileCol);
        String lampWall = mixHex(FOG_WALL, FOG_WALL_WARM, 0.45 * lamp);
        return mixHex(lampWall, FOG_UNSEEN, WALL_EDGE_DIM * Math.max(0, Math.min(1, edge)));
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

    /**
     * 0 at maze center → 1 at the far corner — drives clear-board floor falloff.
     */
    public static double floorEdge(Layout layout, int tileRow, int tileCol) {
        if (layout == null || layout.tileRows() < 2 || layout.tileCols() < 2) {
            return 0;
        }
        double cx = (layout.tileCols() - 1) / 2.0;
        double cy = (layout.tileRows() - 1) / 2.0;
        double dx = (tileCol - cx) / Math.max(1.0, layout.tileCols() / 2.0);
        double dy = (tileRow - cy) / Math.max(1.0, layout.tileRows() / 2.0);
        return Math.min(1.0, Math.sqrt(dx * dx + dy * dy));
    }

    public static boolean fogFloorHi(Layout layout, Fog fog, int tileRow, int tileCol) {
        return floorHi(layout, tileRow, tileCol, fogFloorIntensity(fog, tileRow, tileCol));
    }

    /** Lamp × frontier — same product that warms fog floors and walls. */
    public static double fogFloorIntensity(Fog fog, int tileRow, int tileCol) {
        if (fog == null) {
            return 1;
        }
        return fogLamp(fog, tileRow, tileCol) * fogFrontier(fog, tileRow, tileCol);
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

    public static String clearWallHiInk(double edge) {
        String hi = mixHex(WALL_HI, FOG_WALL_WARM, 0.28);
        return mixHex(hi, FOG_UNSEEN, WALL_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }

    public static String fogWallHiInk(double lamp) {
        return fogWallHiInk(lamp, 0);
    }

    public static String fogWallHiInk(double lamp, double edge) {
        String hi = mixHex(WALL_HI, FOG_WALL_WARM, 0.28 * Math.max(0, Math.min(1, lamp)));
        return mixHex(hi, FOG_UNSEEN, WALL_EDGE_DIM * Math.max(0, Math.min(1, edge)));
    }

    public static Hairline wallHiStroke(Layout layout, int tileRow, int tileCol) {
        if (layout == null || layout.cellSize() < 10) {
            return null;
        }
        double w = layout.w(tileCol);
        double h = layout.h(tileRow);
        if (w < 3 || h < 3) {
            return null;
        }
        return new Hairline(layout.x(tileCol) + 1, layout.y(tileRow) + 1, Math.max(1, w - 2), 1);
    }

    public static int hexArgb(String hex) {
        int[] c = rgb(hex);
        return 0xFF000000 | (c[0] << 16) | (c[1] << 8) | c[2];
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
     * Well bitmap stays crisp — leftover bilinear smear is not torch stone.
     * Same lamp as web {@code image-rendering: pixelated}.
     */
    public static final boolean CANVAS_IMAGE_SMOOTHING = false;

    /** Scene void — leftover Modena white is not the lamp around the well. */
    public static final String SCENE_FILL = "#0c0908";
    /** PNG snapshot void — leftover JavaFX white is not the lamp under the well. */
    public static final String SNAPSHOT_FILL = SCENE_FILL;

    /** Stage icon void — leftover Java chrome is not the lamp on the taskbar. */
    public static final int STAGE_ICON_SIZE = 32;
    public static final int STAGE_ICON_ARGB = 0xFF0C0908;
    /** Same gold lip as the well rim — leftover unrimmed void is not the lamp. */
    public static final int STAGE_ICON_LIP_ARGB = 0xFFB88538;
    /** Idle-maze stamp — same 2px tiles as the well tab icon. */
    public static final int STAGE_ICON_CELL = 2;
    /** Torch-warm posts — same as {@code EMPTY_MARK_WALL}. */
    public static final int STAGE_ICON_WALL_ARGB = 0xFF2A2218;
    /** Idle floors — same 0.28 mix as {@code EMPTY_MARK_FLOOR}. */
    public static final int STAGE_ICON_FLOOR_ARGB = 0xFF484339;
    /** Start mint — same brand as the well tab gate; stamp uses startInk. */
    public static final int STAGE_ICON_START_ARGB = 0xFF3EE08F;
    /** Exit coral — same brand as the well tab goal; stamp uses goalInk. */
    public static final int STAGE_ICON_GOAL_ARGB = 0xFFFF5A5F;

    public static int[] stageIconPixels() {
        int[] px = new int[STAGE_ICON_SIZE * STAGE_ICON_SIZE];
        Arrays.fill(px, STAGE_ICON_ARGB);
        int rows = EMPTY_MARK.length;
        int cols = EMPTY_MARK[0].length();
        int ox = (STAGE_ICON_SIZE - cols * STAGE_ICON_CELL) / 2;
        int oy = (STAGE_ICON_SIZE - rows * STAGE_ICON_CELL) / 2;
        int startTr = 2 * EMPTY_MARK_START.row() + 1;
        int startTc = 2 * EMPTY_MARK_START.col() + 1;
        int goalTr = 2 * EMPTY_MARK_GOAL.row() + 1;
        int goalTc = 2 * EMPTY_MARK_GOAL.col() + 1;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                int ink;
                if (r == startTr && c == startTc) {
                    ink = hexArgb(startInk(emptyMarkEdge(r, c)));
                } else if (r == goalTr && c == goalTc) {
                    ink = hexArgb(goalInk(emptyMarkEdge(r, c)));
                } else if (EMPTY_MARK[r].charAt(c) == '#') {
                    ink = hexArgb(emptyMarkWallInk(r, c));
                } else {
                    ink = hexArgb(clearFloorInk(emptyMarkEdge(r, c)));
                }
                fillStageIconCell(px, ox + c * STAGE_ICON_CELL, oy + r * STAGE_ICON_CELL, ink);
            }
        }
        int last = STAGE_ICON_SIZE - 1;
        for (int i = 0; i < STAGE_ICON_SIZE; i++) {
            px[i] = STAGE_ICON_LIP_ARGB;
            px[last * STAGE_ICON_SIZE + i] = STAGE_ICON_LIP_ARGB;
            px[i * STAGE_ICON_SIZE] = STAGE_ICON_LIP_ARGB;
            px[i * STAGE_ICON_SIZE + last] = STAGE_ICON_LIP_ARGB;
        }
        return px;
    }

    private static void fillStageIconCell(int[] px, int x, int y, int argb) {
        for (int dy = 0; dy < STAGE_ICON_CELL; dy++) {
            for (int dx = 0; dx < STAGE_ICON_CELL; dx++) {
                int xx = x + dx;
                int yy = y + dy;
                if (xx >= 0 && yy >= 0 && xx < STAGE_ICON_SIZE && yy < STAGE_ICON_SIZE) {
                    px[yy * STAGE_ICON_SIZE + xx] = argb;
                }
            }
        }
    }

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
                Math.floor(canvasH / 2.0 - EMPTY_MARK_LIFT - drawH / 2.0),
                fitted.tileRows(),
                fitted.tileCols(),
                fitted.offX(),
                fitted.offY());
    }

    /** Corridor shine on the idle mark — same 1px hairline as the live board. */
    public static List<Hairline> emptyMarkHairlines(Layout mark) {
        if (mark == null) {
            return List.of();
        }
        List<Hairline> out = new ArrayList<>();
        for (TileRect tile : emptyMarkFloors()) {
            Hairline stroke = floorHiStroke(mark, tile.tileRow(), tile.tileCol());
            if (stroke != null) {
                out.add(stroke);
            }
        }
        return List.copyOf(out);
    }

    /** Post shine on the idle mark — same 1px hairline as live walls. */
    public static List<Hairline> emptyMarkWallHairlines(Layout mark) {
        if (mark == null) {
            return List.of();
        }
        List<Hairline> out = new ArrayList<>();
        for (TileRect tile : emptyMarkWalls()) {
            Hairline stroke = wallHiStroke(mark, tile.tileRow(), tile.tileCol());
            if (stroke != null) {
                out.add(stroke);
            }
        }
        return List.copyOf(out);
    }

    /** Idle start / goal floors — same 0.42 wash as the live well. */
    public static TileType emptyMarkTile(int tileRow, int tileCol) {
        int startRow = 2 * EMPTY_MARK_START.row() + 1;
        int startCol = 2 * EMPTY_MARK_START.col() + 1;
        int goalRow = 2 * EMPTY_MARK_GOAL.row() + 1;
        int goalCol = 2 * EMPTY_MARK_GOAL.col() + 1;
        if (tileRow == startRow && tileCol == startCol) {
            return TileType.START;
        }
        if (tileRow == goalRow && tileCol == goalCol) {
            return TileType.GOAL;
        }
        return TileType.PASSAGE;
    }

    /**
     * Rim distance on the idle mark — same falloff the live well uses.
     */
    public static double emptyMarkEdge(int tileRow, int tileCol) {
        int rows = EMPTY_MARK.length;
        int cols = EMPTY_MARK[0].length();
        double cx = (cols - 1) / 2.0;
        double cy = (rows - 1) / 2.0;
        double dx = (tileCol - cx) / Math.max(1, cols / 2.0);
        double dy = (tileRow - cy) / Math.max(1, rows / 2.0);
        return Math.min(1, Math.hypot(dx, dy));
    }

    public static String emptyMarkWallInk(int tileRow, int tileCol) {
        return wallInk(emptyMarkEdge(tileRow, tileCol));
    }

    public static String emptyMarkWallHiInk(int tileRow, int tileCol) {
        return clearWallHiInk(emptyMarkEdge(tileRow, tileCol));
    }

    public static String emptyMarkFloorInk(int tileRow, int tileCol) {
        return endFloorInk(clearFloorInk(emptyMarkEdge(tileRow, tileCol)),
                emptyMarkTile(tileRow, tileCol));
    }

    /** Idle corridor shine — same mint / coral wash as the live hairline. */
    public static String emptyMarkFloorHiInk(int tileRow, int tileCol) {
        return endFloorInk(clearFloorHiInk(emptyMarkEdge(tileRow, tileCol)),
                emptyMarkTile(tileRow, tileCol));
    }

    /** Passage tiles of the idle mark. */
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

    /** Wall tiles of the idle mark — soft silhouette against the void. */
    public static List<TileRect> emptyMarkWalls() {
        List<TileRect> out = new ArrayList<>();
        for (int r = 0; r < EMPTY_MARK.length; r++) {
            String row = EMPTY_MARK[r];
            for (int c = 0; c < row.length(); c++) {
                if (row.charAt(c) == '#') {
                    out.add(new TileRect(r, c));
                }
            }
        }
        return List.copyOf(out);
    }
}
