// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.model.Point;
import com.daedalus.model.TileType;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Parcel;
import com.daedalus.world.World;
import com.daedalus.world.auto.WorldOps;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Flat Doom-like tints for extruded faces. GLFW only applies these;
 * tests lock the palette so the well stays a maze, not a void.
 */
public final class ExplorePaint {

    public static final float SKY_R = 0.10f;
    public static final float SKY_G = 0.08f;
    public static final float SKY_B = 0.07f;

    /** Window icon void — leftover OS chrome is not the lamp on the taskbar. */
    public static final int WINDOW_ICON_SIZE = 32;
    public static final int WINDOW_ICON_R = 12;
    public static final int WINDOW_ICON_G = 9;
    public static final int WINDOW_ICON_B = 8;
    /** Same gold lip as the well rim — leftover unrimmed void is not the lamp. */
    public static final int WINDOW_ICON_LIP_R = 184;
    public static final int WINDOW_ICON_LIP_G = 133;
    public static final int WINDOW_ICON_LIP_B = 56;
    /** Idle-maze stamp — same 2px tiles as the well tab / desktop stage icons. */
    public static final int WINDOW_ICON_CELL = 2;
    public static final String[] WINDOW_ICON_MARK = {
            "###########",
            "# #   #   #",
            "# ### ### #",
            "#   #   # #",
            "### ### # #",
            "#     #   #",
            "###########",
    };
    public static final int WINDOW_ICON_START_ROW = 0;
    public static final int WINDOW_ICON_START_COL = 0;
    public static final int WINDOW_ICON_GOAL_ROW = 2;
    public static final int WINDOW_ICON_GOAL_COL = 4;
    /** Torch-warm posts — same as well {@code wallWarm}. */
    public static final int WINDOW_ICON_WALL_R = 0x2a;
    public static final int WINDOW_ICON_WALL_G = 0x22;
    public static final int WINDOW_ICON_WALL_B = 0x18;
    /** Idle floors — same 0.28 mix as the well idle mark. */
    public static final int WINDOW_ICON_FLOOR_R = 0x48;
    public static final int WINDOW_ICON_FLOOR_G = 0x43;
    public static final int WINDOW_ICON_FLOOR_B = 0x39;
    /** Start mint — KEEP, same as the well tab gate. */
    public static final int WINDOW_ICON_START_R = 0x3e;
    public static final int WINDOW_ICON_START_G = 0xe0;
    public static final int WINDOW_ICON_START_B = 0x8f;
    /** Exit coral — same as the well tab goal. */
    public static final int WINDOW_ICON_GOAL_R = 0xff;
    public static final int WINDOW_ICON_GOAL_G = 0x5a;
    public static final int WINDOW_ICON_GOAL_B = 0x5f;

    /** Same 0.28 rim as live / idle well posts. */
    public static double windowIconEdge(int tileRow, int tileCol) {
        int rows = WINDOW_ICON_MARK.length;
        int cols = WINDOW_ICON_MARK[0].length();
        double cx = (cols - 1) / 2.0;
        double cy = (rows - 1) / 2.0;
        double dx = (tileCol - cx) / Math.max(1, cols / 2.0);
        double dy = (tileRow - cy) / Math.max(1, rows / 2.0);
        return Math.min(1, Math.hypot(dx, dy));
    }

    public static int[] windowIconFloorRgb(int tileRow, int tileCol) {
        double edge = windowIconEdge(tileRow, tileCol);
        return new int[] {
                mixByte(WINDOW_ICON_FLOOR_R, 0x2a, 0.22 * edge),
                mixByte(WINDOW_ICON_FLOOR_G, 0x22, 0.22 * edge),
                mixByte(WINDOW_ICON_FLOOR_B, 0x18, 0.22 * edge)
        };
    }

    public static int[] windowIconWallRgb(int tileRow, int tileCol) {
        double edge = windowIconEdge(tileRow, tileCol);
        return new int[] {
                mixByte(mixByte(0x12, WINDOW_ICON_WALL_R, 0.28), WINDOW_ICON_R, 0.28 * edge),
                mixByte(mixByte(0x0e, WINDOW_ICON_WALL_G, 0.28), WINDOW_ICON_G, 0.28 * edge),
                mixByte(mixByte(0x0c, WINDOW_ICON_WALL_B, 0.28), WINDOW_ICON_B, 0.28 * edge)
        };
    }

    private static int mixByte(int from, int to, double t) {
        double u = Math.max(0, Math.min(1, t));
        return (int) Math.round(from + (to - from) * u);
    }

    public static byte[] windowIconRgba() {
        byte[] px = new byte[WINDOW_ICON_SIZE * WINDOW_ICON_SIZE * 4];
        for (int i = 0; i < px.length; i += 4) {
            px[i] = (byte) WINDOW_ICON_R;
            px[i + 1] = (byte) WINDOW_ICON_G;
            px[i + 2] = (byte) WINDOW_ICON_B;
            px[i + 3] = (byte) 0xFF;
        }
        int rows = WINDOW_ICON_MARK.length;
        int cols = WINDOW_ICON_MARK[0].length();
        int ox = (WINDOW_ICON_SIZE - cols * WINDOW_ICON_CELL) / 2;
        int oy = (WINDOW_ICON_SIZE - rows * WINDOW_ICON_CELL) / 2;
        int startTr = 2 * WINDOW_ICON_START_ROW + 1;
        int startTc = 2 * WINDOW_ICON_START_COL + 1;
        int goalTr = 2 * WINDOW_ICON_GOAL_ROW + 1;
        int goalTc = 2 * WINDOW_ICON_GOAL_COL + 1;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                int red;
                int green;
                int blue;
                if (r == startTr && c == startTc) {
                    red = WINDOW_ICON_START_R;
                    green = WINDOW_ICON_START_G;
                    blue = WINDOW_ICON_START_B;
                } else if (r == goalTr && c == goalTc) {
                    red = WINDOW_ICON_GOAL_R;
                    green = WINDOW_ICON_GOAL_G;
                    blue = WINDOW_ICON_GOAL_B;
                } else if (WINDOW_ICON_MARK[r].charAt(c) == '#') {
                    int[] wall = windowIconWallRgb(r, c);
                    red = wall[0];
                    green = wall[1];
                    blue = wall[2];
                } else {
                    int[] floor = windowIconFloorRgb(r, c);
                    red = floor[0];
                    green = floor[1];
                    blue = floor[2];
                }
                fillWindowIconCell(px, ox + c * WINDOW_ICON_CELL, oy + r * WINDOW_ICON_CELL,
                        red, green, blue);
            }
        }
        int last = WINDOW_ICON_SIZE - 1;
        for (int i = 0; i < WINDOW_ICON_SIZE; i++) {
            putIconPixel(px, i, 0, WINDOW_ICON_LIP_R, WINDOW_ICON_LIP_G, WINDOW_ICON_LIP_B);
            putIconPixel(px, i, last, WINDOW_ICON_LIP_R, WINDOW_ICON_LIP_G, WINDOW_ICON_LIP_B);
            putIconPixel(px, 0, i, WINDOW_ICON_LIP_R, WINDOW_ICON_LIP_G, WINDOW_ICON_LIP_B);
            putIconPixel(px, last, i, WINDOW_ICON_LIP_R, WINDOW_ICON_LIP_G, WINDOW_ICON_LIP_B);
        }
        return px;
    }

    private static void fillWindowIconCell(byte[] px, int x, int y, int r, int g, int b) {
        for (int dy = 0; dy < WINDOW_ICON_CELL; dy++) {
            for (int dx = 0; dx < WINDOW_ICON_CELL; dx++) {
                int xx = x + dx;
                int yy = y + dy;
                if (xx >= 0 && yy >= 0 && xx < WINDOW_ICON_SIZE && yy < WINDOW_ICON_SIZE) {
                    putIconPixel(px, xx, yy, r, g, b);
                }
            }
        }
    }

    private static void putIconPixel(byte[] px, int x, int y, int r, int g, int b) {
        int i = (y * WINDOW_ICON_SIZE + x) * 4;
        px[i] = (byte) r;
        px[i + 1] = (byte) g;
        px[i + 2] = (byte) b;
        px[i + 3] = (byte) 0xFF;
    }
    /** Fog silhouette — same warm dark for every unseen face, not a dusk hole. */
    public static final float UNSEEN_R = 0.09f;
    public static final float UNSEEN_G = 0.07f;
    public static final float UNSEEN_B = 0.06f;
    /** Linear distance fog — same warm dark as unseen faces, not dusk. */
    public static final float FOG_R = UNSEEN_R;
    public static final float FOG_G = UNSEEN_G;
    public static final float FOG_B = UNSEEN_B;
    public static final int TEX = 64;
    public static final int MAP = 36;
    public static final int GLYPH_W = 5;
    public static final int GLYPH_H = 7;
    /** Soft pad around the automap HERE cell — place, not a single pixel. */
    public static final float MAP_HERE_HALO = 0.7f;
    public static final float MAP_HERE_SOFT_R = 0.55f;
    public static final float MAP_HERE_SOFT_G = 0.40f;
    public static final float MAP_HERE_SOFT_B = 0.12f;
    public static final float MAP_HERE_R = 0.95f;
    public static final float MAP_HERE_G = 0.86f;
    public static final float MAP_HERE_B = 0.28f;
    /** Same 0.22 rim as halls — leftover even gold is not the last word on you-are-here. */
    public static final float MAP_HERE_EDGE_DIM = 0.22f;
    /** HERE pad breath — same cadence idea as victory (~2.8s). */
    public static final float MAP_HERE_BREATH_MS = 2800f;

    public static float mapHereHalo(double seconds) {
        double t = ((seconds * 1000.0) % MAP_HERE_BREATH_MS) / MAP_HERE_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return MAP_HERE_HALO * (float) (0.85 + 0.30 * wave);
    }

    /** HERE on start / goal — gold you-are-here, washed toward well mint / coral. */
    public static void mapHereTint(ExploreBody body, ExploreMesh mesh, float[] rgb) {
        mapHereTint(body, mesh, null, rgb);
    }

    public static void mapHereTint(ExploreBody body, ExploreMesh mesh, WorldMesh blocks,
                                  float[] rgb) {
        mapHereTint(body, mesh, blocks, rgb, 0);
    }

    public static void mapHereTint(ExploreBody body, ExploreMesh mesh, WorldMesh blocks,
                                  float[] rgb, double edge) {
        washHere(body, mesh, blocks, rgb, MAP_HERE_R, MAP_HERE_G, MAP_HERE_B);
        mixHereEdge(edge, rgb);
    }

    public static void mapHereSoftTint(ExploreBody body, ExploreMesh mesh, float[] rgb) {
        mapHereSoftTint(body, mesh, null, rgb);
    }

    public static void mapHereSoftTint(ExploreBody body, ExploreMesh mesh, WorldMesh blocks,
                                      float[] rgb) {
        mapHereSoftTint(body, mesh, blocks, rgb, 0);
    }

    public static void mapHereSoftTint(ExploreBody body, ExploreMesh mesh, WorldMesh blocks,
                                      float[] rgb, double edge) {
        washHere(body, mesh, blocks, rgb, MAP_HERE_SOFT_R, MAP_HERE_SOFT_G, MAP_HERE_SOFT_B);
        mixHereEdge(edge, rgb);
    }

    public static void mixHereEdge(double edge, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        float t = (float) (MAP_HERE_EDGE_DIM * Math.min(1, Math.max(0, edge)));
        rgb[0] += (MAP_FLOOR_DIM_R - rgb[0]) * t;
        rgb[1] += (MAP_FLOOR_DIM_G - rgb[1]) * t;
        rgb[2] += (MAP_FLOOR_DIM_B - rgb[2]) * t;
    }

    public static void mixWallEdge(double edge, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        float t = (float) (MAP_WALL_EDGE_DIM * Math.min(1, Math.max(0, edge)));
        rgb[0] += (UNSEEN_R - rgb[0]) * t;
        rgb[1] += (UNSEEN_G - rgb[1]) * t;
        rgb[2] += (UNSEEN_B - rgb[2]) * t;
    }

    private static void washHere(ExploreBody body, ExploreMesh mesh, WorldMesh blocks,
                                float[] rgb, float r, float g, float b) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        set(rgb, r, g, b);
        String place = endPlaceName(body, mesh);
        if ("START".equals(place)) {
            rgb[0] += (MAP_START_R - rgb[0]) * FLOOR_END_WEIGHT;
            rgb[1] += (MAP_START_G - rgb[1]) * FLOOR_END_WEIGHT;
            rgb[2] += (MAP_START_B - rgb[2]) * FLOOR_END_WEIGHT;
        } else if ("GOAL".equals(place)) {
            rgb[0] += (MAP_GOAL_R - rgb[0]) * FLOOR_END_WEIGHT;
            rgb[1] += (MAP_GOAL_G - rgb[1]) * FLOOR_END_WEIGHT;
            rgb[2] += (MAP_GOAL_B - rgb[2]) * FLOOR_END_WEIGHT;
        } else if (parcelPlaceName(blocks, body) != null) {
            rgb[0] += (MAP_BLOCK_R - rgb[0]) * FLOOR_END_WEIGHT;
            rgb[1] += (MAP_BLOCK_G - rgb[1]) * FLOOR_END_WEIGHT;
            rgb[2] += (MAP_BLOCK_B - rgb[2]) * FLOOR_END_WEIGHT;
        }
    }
    /** Soft pad under automap story marks — presence, not a flat red pixel. */
    public static final float MAP_MARK_HALO = 0.55f;
    /** Story-mark pad breath — same cadence as HERE. */
    public static final float MAP_MARK_BREATH_MS = MAP_HERE_BREATH_MS;

    public static float mapMarkHalo(double seconds) {
        double t = ((seconds * 1000.0) % MAP_MARK_BREATH_MS) / MAP_MARK_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return MAP_MARK_HALO * (float) (0.85 + 0.30 * wave);
    }

    public static final float MAP_MARK_SOFT_R = 0.45f;
    public static final float MAP_MARK_SOFT_G = 0.12f;
    public static final float MAP_MARK_SOFT_B = 0.08f;
    public static final float MAP_MARK_R = 0.78f;
    public static final float MAP_MARK_G = 0.22f;
    public static final float MAP_MARK_B = 0.16f;
    /** Same 0.22 rim as halls — leftover even story ink is not the last word on a mark. */
    public static final float MAP_MARK_EDGE_DIM = 0.22f;
    /** Halo under a story mark — same dim as the old leftover-red pad. */
    public static final float MAP_MARK_SOFT_WEIGHT = 0.58f;
    /** Earned-map stone — same corridor tints, not a separate admin brown. */
    public static final float MAP_FLOOR_R = 0.34f;
    public static final float MAP_FLOOR_G = 0.24f;
    public static final float MAP_FLOOR_B = 0.14f;
    /** Same 0.22 rim as live / idle well halls. */
    public static final float MAP_FLOOR_EDGE_DIM = 0.22f;
    public static final float MAP_FLOOR_DIM_R = 0x2a / 255f;
    public static final float MAP_FLOOR_DIM_G = 0x22 / 255f;
    public static final float MAP_FLOOR_DIM_B = 0x18 / 255f;
    public static final float MAP_WALL_R = 0.64f;
    public static final float MAP_WALL_G = 0.40f;
    public static final float MAP_WALL_B = 0.22f;
    /** Same 0.28 rim as live / idle well posts. */
    public static final float MAP_WALL_EDGE_DIM = 0.28f;
    /** Occupied cube on the earned map — torch wood, not leftover ice. */
    public static final float MAP_BLOCK_R = 0.58f;
    public static final float MAP_BLOCK_G = 0.38f;
    public static final float MAP_BLOCK_B = 0.18f;
    /** Occupied-cube rim — same 0.22 as halls so leftover even wood is not the last word. */
    public static final float MAP_BLOCK_EDGE_DIM = 0.22f;
    /** Soft pad under an earned cube — presence, not a flat wood pixel. */
    public static final float MAP_BLOCK_HALO = MAP_MARK_HALO;
    public static final float MAP_BLOCK_BREATH_MS = MAP_HERE_BREATH_MS;

    public static float mapBlockHalo(double seconds) {
        double t = ((seconds * 1000.0) % MAP_BLOCK_BREATH_MS) / MAP_BLOCK_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return MAP_BLOCK_HALO * (float) (0.85 + 0.30 * wave);
    }

    public static void mapBlockSoftTint(float[] rgb) {
        mapBlockSoftTint(0, rgb);
    }

    public static void mapBlockSoftTint(double edge, float[] rgb) {
        mapStoneTint(MapKind.BLOCK, 0, edge, rgb);
        if (rgb == null || rgb.length < 3) {
            return;
        }
        rgb[0] *= MAP_MARK_SOFT_WEIGHT;
        rgb[1] *= MAP_MARK_SOFT_WEIGHT;
        rgb[2] *= MAP_MARK_SOFT_WEIGHT;
    }
    /** Map stone breath — same cadence as the gold frame. */
    public static final float MAP_STONE_BREATH_MS = MAP_HERE_BREATH_MS;

    public static float mapStoneBreath(double seconds) {
        double t = ((seconds * 1000.0) % MAP_STONE_BREATH_MS) / MAP_STONE_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return (float) (0.90 + 0.12 * wave);
    }

    public static void mapStoneTint(MapKind kind, double seconds, float[] rgb) {
        mapStoneTint(kind, seconds, 0, rgb);
    }

    public static void mapStoneTint(MapKind kind, double seconds, double edge, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        float breath = mapStoneBreath(seconds);
        if (kind == MapKind.WALL) {
            float t = MAP_WALL_EDGE_DIM * (float) Math.max(0, Math.min(1, edge));
            set(rgb,
                    (MAP_WALL_R + (UNSEEN_R - MAP_WALL_R) * t) * breath,
                    (MAP_WALL_G + (UNSEEN_G - MAP_WALL_G) * t) * breath,
                    (MAP_WALL_B + (UNSEEN_B - MAP_WALL_B) * t) * breath);
        } else if (kind == MapKind.BLOCK) {
            float t = MAP_BLOCK_EDGE_DIM * (float) Math.max(0, Math.min(1, edge));
            set(rgb,
                    (MAP_BLOCK_R + (MAP_FLOOR_DIM_R - MAP_BLOCK_R) * t) * breath,
                    (MAP_BLOCK_G + (MAP_FLOOR_DIM_G - MAP_BLOCK_G) * t) * breath,
                    (MAP_BLOCK_B + (MAP_FLOOR_DIM_B - MAP_BLOCK_B) * t) * breath);
        } else {
            float t = MAP_FLOOR_EDGE_DIM * (float) Math.max(0, Math.min(1, edge));
            set(rgb,
                    (MAP_FLOOR_R + (MAP_FLOOR_DIM_R - MAP_FLOOR_R) * t) * breath,
                    (MAP_FLOOR_G + (MAP_FLOOR_DIM_G - MAP_FLOOR_G) * t) * breath,
                    (MAP_FLOOR_B + (MAP_FLOOR_DIM_B - MAP_FLOOR_B) * t) * breath);
        }
    }

    /** Automap gold frame — same ink as the status lip. */
    public static final float MAP_FRAME_OUT = 0.022f;
    public static final float MAP_FRAME_IN = 0.014f;
    /** Frame breath — same cadence as HERE / story pads. */
    public static final float MAP_FRAME_BREATH_MS = MAP_HERE_BREATH_MS;

    public static float mapFrameOut(double seconds) {
        double t = ((seconds * 1000.0) % MAP_FRAME_BREATH_MS) / MAP_FRAME_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return MAP_FRAME_OUT * (float) (0.88 + 0.24 * wave);
    }

    public static float mapFrameIn(double seconds) {
        double t = ((seconds * 1000.0) % MAP_FRAME_BREATH_MS) / MAP_FRAME_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return MAP_FRAME_IN * (float) (0.88 + 0.24 * wave);
    }
    /** Ortho strip under the crosshair — Doom status height in NDC. */
    public static final float STATUS_H = 0.28f;
    /** Warm HUD void — status fill and automap pocket share this well. */
    public static final float HUD_VOID_R = 0.12f;
    public static final float HUD_VOID_G = 0.08f;
    public static final float HUD_VOID_B = 0.06f;
    /** Status rim — same pocket mid so the strip sits in a well, not leftover flat. */
    public static final float HUD_VOID_RIM_R = 0.06f;
    public static final float HUD_VOID_RIM_G = 0.04f;
    public static final float HUD_VOID_RIM_B = 0.03f;

    /** Mid strip at 0, pocket rim at 1 so leftover flat HUD is not the last word. */
    public static void hudVoidTint(float edge, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        float t = Math.max(0f, Math.min(1f, edge));
        rgb[0] = HUD_VOID_R + (HUD_VOID_RIM_R - HUD_VOID_R) * t;
        rgb[1] = HUD_VOID_G + (HUD_VOID_RIM_G - HUD_VOID_G) * t;
        rgb[2] = HUD_VOID_B + (HUD_VOID_RIM_B - HUD_VOID_B) * t;
    }
    /** Automap inset — a shade deeper than the strip, same brown family. */
    public static final float MAP_POCKET_R = 0.06f;
    public static final float MAP_POCKET_G = 0.04f;
    public static final float MAP_POCKET_B = 0.03f;
    /** Pocket rim — same well-void edge as legend fog / ASCII dump. */
    public static final float MAP_POCKET_RIM_R = 0x0c / 255f;
    public static final float MAP_POCKET_RIM_G = 0x09 / 255f;
    public static final float MAP_POCKET_RIM_B = 0x08 / 255f;

    /** Mid pocket at 0, well-void rim at 1 so leftover flat inset is not the last word. */
    public static void mapPocketTint(float edge, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        float t = Math.max(0f, Math.min(1f, edge));
        rgb[0] = MAP_POCKET_R + (MAP_POCKET_RIM_R - MAP_POCKET_R) * t;
        rgb[1] = MAP_POCKET_G + (MAP_POCKET_RIM_G - MAP_POCKET_G) * t;
        rgb[2] = MAP_POCKET_B + (MAP_POCKET_RIM_B - MAP_POCKET_B) * t;
    }
    /** Gold lip — same ink as the automap frame. */
    public static final float STATUS_GOLD_R = 0.72f;
    public static final float STATUS_GOLD_G = 0.52f;
    public static final float STATUS_GOLD_B = 0.22f;
    public static final float STATUS_GOLD_H = 0.014f;
    /** Dark under the gold lip — same brown as the automap inset. */
    public static final float STATUS_GOLD_UNDER_R = 0.16f;
    public static final float STATUS_GOLD_UNDER_G = 0.11f;
    public static final float STATUS_GOLD_UNDER_B = 0.08f;
    public static final float STATUS_GOLD_UNDER_H = 0.022f;
    /** Status lip breath — same cadence as automap frame chrome. */
    public static final float STATUS_BREATH_MS = MAP_HERE_BREATH_MS;

    /** Soft screen-edge shade — corridor tunnel, not a flat ortho box. */
    public static final float VIGNETTE_INSET = 0.16f;
    public static final float VIGNETTE_ALPHA = 0.26f;
    public static final float VIGNETTE_R = 0.02f;
    public static final float VIGNETTE_G = 0.015f;
    public static final float VIGNETTE_B = 0.01f;
    public static final float VIGNETTE_BREATH_MS = MAP_HERE_BREATH_MS;

    public static float vignetteAlpha(double seconds) {
        double t = ((seconds * 1000.0) % VIGNETTE_BREATH_MS) / VIGNETTE_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return VIGNETTE_ALPHA * (float) (0.88 + 0.24 * wave);
    }

    public static float statusGoldH(double seconds) {
        double t = ((seconds * 1000.0) % STATUS_BREATH_MS) / STATUS_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return STATUS_GOLD_H * (float) (0.88 + 0.24 * wave);
    }

    public static float statusGoldUnderH(double seconds) {
        double t = ((seconds * 1000.0) % STATUS_BREATH_MS) / STATUS_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return STATUS_GOLD_UNDER_H * (float) (0.88 + 0.24 * wave);
    }
    public static final double TORCH_REACH = 11.0;
    /** Torch-brown mix — same tokens as 2D fog {@code floorWarm} / {@code wallWarm}. */
    public static final float TORCH_FLOOR_WARM_R = 0x5c / 255f;
    public static final float TORCH_FLOOR_WARM_G = 0x4a / 255f;
    public static final float TORCH_FLOOR_WARM_B = 0x32 / 255f;
    public static final float TORCH_WALL_WARM_R = 0x2a / 255f;
    public static final float TORCH_WALL_WARM_G = 0x22 / 255f;
    public static final float TORCH_WALL_WARM_B = 0x18 / 255f;
    public static final float TORCH_FLOOR_WARM_WEIGHT = 0.28f;
    public static final float TORCH_WALL_WARM_WEIGHT = 0.45f;
    /** Lid catches the lamp a little harder so looking up is fire, not a cool slate. */
    public static final float TORCH_CEILING_WARM_WEIGHT = 0.36f;
    public static final float CEILING_R = 0.26f;
    public static final float CEILING_G = 0.18f;
    public static final float CEILING_B = 0.12f;
    /** Soft wall–floor contact — dark near the skirting, full by this height fraction. */
    public static final double CONTACT_BOOT_FRAC = 0.28;
    public static final float CONTACT_BOOT_MIN = 0.55f;
    /** Soft wall–ceiling contact — dark near the crown, same band as the boot. */
    public static final double CONTACT_CROWN_FRAC = CONTACT_BOOT_FRAC;
    public static final float CONTACT_CROWN_MIN = CONTACT_BOOT_MIN;
    /** Floor skirting — darken toward the tile rim where walls meet. */
    public static final float FLOOR_CONTACT_START = 0.55f;
    public static final float FLOOR_CONTACT_DIM = 0.16f;
    /** Ceiling crown — same rim falloff as the floor so the lid has weight. */
    public static final float CEILING_CONTACT_START = FLOOR_CONTACT_START;
    public static final float CEILING_CONTACT_DIM = FLOOR_CONTACT_DIM;

    public enum MapKind {
        FLOOR,
        WALL,
        HERE,
        MARK,
        /** Revealed start — same mint as the well gate. */
        START,
        /** Revealed goal — same coral as the well exit. */
        GOAL,
        /** Occupied cube — torch wood, not leftover well ice. */
        BLOCK
    }

    public record MapDot(int x, int y, MapKind kind, String story, double edge) {
        public MapDot(int x, int y, MapKind kind) {
            this(x, y, kind, "", 0);
        }

        public MapDot(int x, int y, MapKind kind, String story) {
            this(x, y, kind, story, 0);
        }
    }

    /** Corridor disc at a revealed start / goal — same place as the well endpoint. */
    public record EndPlace(double x, double z, MapKind kind, int tileRow, int tileCol) {
    }

    /**
     * Occupied cube boot — pad center is the cube middle so the disc
     * can stain the corridor around a 1×1 slab.
     */
    public record BlockPlace(double x, double z, BlockType type, int tileRow, int tileCol) {
    }

    /**
     * Bottom strip: named place, compass, how much stone is earned.
     * GLFW only paints this; tests lock the words so the bar cannot lie.
     */
    public record Status(String place, String facing, int stood, int marks, int mood,
                         boolean startSeen, boolean goalSeen, boolean blockSeen) {
        public Status(String place, String facing, int stood, int marks, int mood) {
            this(place, facing, stood, marks, mood, false, false, false);
        }

        public Status(String place, String facing, int stood, int marks, int mood,
                      boolean startSeen, boolean goalSeen) {
            this(place, facing, stood, marks, mood, startSeen, goalSeen, false);
        }
    }

    public enum HandPart {
        GRIP,
        SHAFT,
        FLAME
    }

    /** Ortho triangles for the torch hand — GLFW fills these; tests lock the silhouette. */
    public record HandTri(float x1, float y1, float x2, float y2, float x3, float y3, HandPart part) {
    }

    /** Soft ash in the torch beam — GLFW fills tiny quads; tests lock drift. */
    public record DustMote(float x, float y, float half, float a) {
    }

    /** Soft lamp wash behind the flame — the HUD is lit, not a pasted sticker. */
    public record TorchBloom(float x, float y, float rx, float ry, float a) {
    }

    public static final float BLOOM_R = 1.00f;
    public static final float BLOOM_G = 0.62f;
    public static final float BLOOM_B = 0.22f;
    public static final float BLOOM_RX = 0.18f;
    public static final float BLOOM_RY = 0.22f;
    /** Fist and shaft catch the flame so the HUD lamp lights the hand, not just the air. */
    public static final float GRIP_CATCH = 0.16f;
    public static final float SHAFT_CATCH = 0.10f;

    public static TorchBloom torchBloom(double aspect, float bob, double seconds) {
        float ox = (float) (Math.max(0.55, aspect) * 0.48);
        float oy = -1f + STATUS_H + 0.06f + bob;
        float flick = flameFlicker(seconds);
        float a = Math.max(0.06f, Math.min(0.28f, 0.10f + 0.12f * flick));
        return new TorchBloom(ox + 0.07f, oy + 0.34f, BLOOM_RX, BLOOM_RY, a);
    }

    public static final int BLOOM_RINGS = 3;

    /** Concentric wash — a lamp fade, not one hard gold stamp. */
    public static List<TorchBloom> torchBloomWash(double aspect, float bob, double seconds) {
        TorchBloom core = torchBloom(aspect, bob, seconds);
        return List.of(
                new TorchBloom(core.x(), core.y(), core.rx() * 1.50f, core.ry() * 1.50f,
                        core.a() * 0.22f),
                new TorchBloom(core.x(), core.y(), core.rx(), core.ry(), core.a() * 0.55f),
                new TorchBloom(core.x(), core.y(), core.rx() * 0.55f, core.ry() * 0.55f, core.a()));
    }

    public static final int DUST_COUNT = 8;
    public static final float DUST_HALF = 0.006f;
    public static final float DUST_R = 0.98f;
    public static final float DUST_G = 0.82f;
    public static final float DUST_B = 0.42f;

    private ExplorePaint() {
    }

    public static void tint(ExploreMesh.Triangle tri, boolean visible, float[] rgb) {
        tint(tri, visible, rgb, Double.NaN, Double.NaN, 0);
    }

    public static void tint(ExploreMesh.Triangle tri, boolean visible, float[] rgb,
                            double eyeX, double eyeZ, double yaw) {
        tint(tri, visible, rgb, eyeX, eyeZ, yaw, 0);
    }

    public static void tint(ExploreMesh.Triangle tri, boolean visible, float[] rgb,
                            double eyeX, double eyeZ, double yaw, double seconds) {
        tint(tri, visible, rgb, eyeX, eyeZ, yaw, seconds, 0);
    }

    public static void tint(ExploreMesh.Triangle tri, boolean visible, float[] rgb,
                            double eyeX, double eyeZ, double yaw, double seconds,
                            double edge) {
        if (rgb == null || rgb.length < 3 || tri == null || tri.face() == null) {
            return;
        }
        if (!visible) {
            set(rgb, UNSEEN_R, UNSEEN_G, UNSEEN_B);
            return;
        }
        switch (tri.face()) {
            case FLOOR -> floor(tri, rgb);
            case CEILING -> ceiling(tri, rgb);
            case WALL -> wall(tri, rgb);
            default -> set(rgb, SKY_R, SKY_G, SKY_B);
        }
        if (tri.face() == ExploreMesh.Face.FLOOR || tri.face() == ExploreMesh.Face.CEILING) {
            mixHereEdge(edge, rgb);
        } else if (tri.face() == ExploreMesh.Face.WALL) {
            mixWallEdge(edge, rgb);
        }
        if (!Double.isNaN(eyeX)) {
            torch(tri, eyeX, eyeZ, yaw, rgb, seconds);
        }
    }

    public static final int BRICK_TEX_HI_R = 196;
    public static final int BRICK_TEX_HI_G = 118;
    public static final int BRICK_TEX_HI_B = 64;
    /** Same 0.22 rim as floor tiles — leftover even clay is not the last word on a post. */
    public static final float BRICK_TEX_EDGE_DIM = 0.22f;

    public static float brickTexShade(int x, int y) {
        int lx = (x + ((y / 8) & 1) * 16) & 15;
        int ly = y & 7;
        int dist = Math.min(Math.min(lx, 15 - lx), Math.min(ly, 7 - ly));
        float t = Math.max(0f, 1f - dist / 3f);
        return 1f - BRICK_TEX_EDGE_DIM * t;
    }

    public static byte[] brickRgba() {
        return raster((x, y) -> {
            boolean mortar = (y % 8 == 0) || (((x + ((y / 8) & 1) * 16) % 16) == 0);
            int n = hash(x, y) & 15;
            if (mortar) {
                return rgbBytes(46, 34, 26);
            }
            int r;
            int g;
            int b;
            if ((y & 7) == 1) {
                r = BRICK_TEX_HI_R + n / 2;
                g = BRICK_TEX_HI_G + n / 3;
                b = BRICK_TEX_HI_B;
            } else {
                r = 170 + n;
                g = 98 + (n / 2);
                b = 54;
            }
            float s = brickTexShade(x, y);
            return rgbBytes(Math.round(r * s), Math.round(g * s), Math.round(b * s));
        });
    }

    public static final int FLOOR_TEX_HI_R = 118;
    public static final int FLOOR_TEX_HI_G = 88;
    public static final int FLOOR_TEX_HI_B = 52;
    /** Same 0.22 rim as live / automap halls — leftover even slate is not the last word. */
    public static final float FLOOR_TEX_EDGE_DIM = 0.22f;

    public static float floorTexShade(int x, int y) {
        int lx = x & 7;
        int ly = y & 7;
        int dist = Math.min(Math.min(lx, 7 - lx), Math.min(ly, 7 - ly));
        float t = Math.max(0f, 1f - dist / 3f);
        return 1f - FLOOR_TEX_EDGE_DIM * t;
    }

    public static byte[] floorRgba() {
        return raster((x, y) -> {
            int n = hash(x, y) & 11;
            int r;
            int g;
            int b;
            if ((y & 7) == 1) {
                r = FLOOR_TEX_HI_R + n / 2;
                g = FLOOR_TEX_HI_G + n / 3;
                b = FLOOR_TEX_HI_B;
            } else {
                int cell = ((x / 8) + (y / 8)) & 1;
                if (cell == 0) {
                    r = 92 + n;
                    g = 64 + n / 2;
                    b = 38;
                } else {
                    r = 74 + n;
                    g = 52 + n / 2;
                    b = 30;
                }
            }
            float s = floorTexShade(x, y);
            return rgbBytes(Math.round(r * s), Math.round(g * s), Math.round(b * s));
        });
    }

    public static final int CEILING_TEX_R = 72;
    public static final int CEILING_TEX_G = 52;
    public static final int CEILING_TEX_B = 36;
    public static final int CEILING_TEX_HI_R = 92;
    public static final int CEILING_TEX_HI_G = 68;
    public static final int CEILING_TEX_HI_B = 42;
    /** Same 0.22 rim as floor tiles — leftover even vault is not the last word overhead. */
    public static final float CEILING_TEX_EDGE_DIM = 0.22f;

    public static float ceilingTexShade(int x, int y) {
        int lx = x & 7;
        int ly = y & 7;
        int dist = Math.min(Math.min(lx, 7 - lx), Math.min(ly, 7 - ly));
        float t = Math.max(0f, 1f - dist / 3f);
        return 1f - CEILING_TEX_EDGE_DIM * t;
    }

    public static byte[] ceilingRgba() {
        return raster((x, y) -> {
            int n = hash(x, y) & 19;
            int r;
            int g;
            int b;
            if ((y & 7) == 1) {
                r = CEILING_TEX_HI_R + n / 2;
                g = CEILING_TEX_HI_G + n / 3;
                b = CEILING_TEX_HI_B;
            } else {
                r = CEILING_TEX_R + n / 2;
                g = CEILING_TEX_G + n / 3;
                b = CEILING_TEX_B;
            }
            float s = ceilingTexShade(x, y);
            return rgbBytes(Math.round(r * s), Math.round(g * s), Math.round(b * s));
        });
    }

    /** Same 0.22 rim as halls — leftover even sky bands are not the last word at the horizon. */
    public static final float SKY_TEX_EDGE_DIM = 0.22f;

    public static float skyTexShade(int x, int y) {
        float cx = (TEX - 1) * 0.5f;
        float cy = (TEX - 1) * 0.45f;
        float dx = (x - cx) / (TEX * 0.5f);
        float dy = (y - cy) / (TEX * 0.5f);
        float edge = Math.min(1f, (float) Math.sqrt(dx * dx + dy * dy));
        return 1f - SKY_TEX_EDGE_DIM * edge;
    }

    public static byte[] skyRgba() {
        return raster((x, y) -> {
            int n = hash(x, y) & 31;
            boolean star = y < 20 && (hash(x, y) & 63) == 0;
            if (star) {
                return rgbBytes(220, 196, 140);
            }
            int r;
            int g;
            int b;
            if (y < 18) {
                r = 78 + n / 3;
                g = 30 + n / 6;
                b = 24;
            } else if (y < 36) {
                r = 148 + n / 2;
                g = 56 + n / 4;
                b = 30;
            } else if (y < 46) {
                r = 196 + n / 3;
                g = 88 + n / 5;
                b = 34;
            } else {
                boolean hill = y > 50 && ((hash(x / 6, 3) & 15) > (64 - y));
                if (hill) {
                    r = 30 + n / 4;
                    g = 16;
                    b = 14;
                } else {
                    r = 52 + n / 3;
                    g = 24;
                    b = 20;
                }
            }
            float s = skyTexShade(x, y);
            return rgbBytes(Math.round(r * s), Math.round(g * s), Math.round(b * s));
        });
    }

    public static byte[] faceRgba(int mood) {
        int grim = Math.max(0, Math.min(2, mood));
        return raster((x, y) -> {
            int px = x / 8;
            int py = y / 8;
            if (px <= 0 || px >= 7 || py <= 0 || py >= 7) {
                return rgbBytes(34, 22, 16);
            }
            if (py == 1) {
                return rgbBytes(62, 36, 22);
            }
            if (py == 3 && (px == 2 || px == 5)) {
                return rgbBytes(18, 12, 10);
            }
            if (py == 5) {
                return mouth(grim, px);
            }
            return rgbBytes(186, 128, 78);
        });
    }

    public static void skyUv(double yaw, double pitch, float sx, float sy, float[] out) {
        skyUv(yaw, pitch, sx, sy, out, 0);
    }

    /** Slow U drift so dusk scrapes even when you stand still. */
    public static final float SKY_DRIFT = 0.008f;

    public static void skyUv(double yaw, double pitch, float sx, float sy, float[] out,
                             double seconds) {
        if (out == null || out.length < 2) {
            return;
        }
        out[0] = sx + (float) (yaw / (Math.PI * 2.0) + seconds * SKY_DRIFT);
        out[1] = sy - (float) (pitch * 0.35);
    }

    /** Soft star breath on the sky quad — not a disco strobe. */
    public static float skyTwinkle(double seconds) {
        double a = Math.sin(seconds * 2.7);
        double b = Math.sin(seconds * 4.1 + 0.8);
        return (float) (0.90 + 0.10 * (0.55 + 0.45 * a + 0.2 * b));
    }

    public static Status status(ExploreFog fog, ExploreBody body, List<ExploreMarker> markers) {
        return status(fog, body, markers, null);
    }

    public static Status status(ExploreFog fog, ExploreBody body, List<ExploreMarker> markers,
                                ExploreMesh mesh) {
        return status(fog, body, markers, mesh, null);
    }

    public static Status status(ExploreFog fog, ExploreBody body, List<ExploreMarker> markers,
                                ExploreMesh mesh, WorldMesh blocks) {
        String facing = facing(body == null ? 0 : body.yaw());
        int stood = fog == null ? 0 : fog.memorySize();
        ExploreMarker near = nearestVisible(fog, body, markers);
        int marks = countVisible(fog, markers);
        boolean startSeen = endSeen(fog, mesh, TileType.START);
        boolean goalSeen = endSeen(fog, mesh, TileType.GOAL);
        boolean cubeSeen = blockSeen(fog, blocks);
        if (near == null) {
            return new Status(placeOrBlock(body, mesh, blocks), facing, stood, marks, 0,
                    startSeen, goalSeen, cubeSeen);
        }
        return new Status(placeName(near.kind()), facing, stood, marks, mood(near.kind()),
                startSeen, goalSeen, cubeSeen);
    }

    /**
     * Story and start/goal still lead. A lamp-facing cube names the hall
     * so leftover HALL is not the last word on a slab.
     */
    static String placeOrBlock(ExploreBody body, ExploreMesh mesh, WorldMesh blocks) {
        String end = endPlaceName(body, mesh);
        if (!"HALL".equals(end)) {
            return end;
        }
        String occ = occupancyName(blocks, body);
        String street = parcelPlaceName(blocks, body);
        if (street != null) {
            String lot = parcelLotName(blocks, body);
            String box = parcelBoxName(blocks, body);
            String maze = parcelMazeName(blocks, body);
            String lease = parcelLeaseName(blocks, body);
            String named = lot == null ? street : street + " " + lot;
            if (box != null) {
                named = named + " " + box;
            }
            if (maze != null) {
                named = named + " " + maze;
            }
            if (lease != null) {
                named = named + " " + lease;
            }
            return withCellAcl(occ, named, blocks, body);
        }
        String lease = parcelLeaseName(blocks, body);
        if (lease != null) {
            String lot = parcelLotName(blocks, body);
            String box = parcelBoxName(blocks, body);
            String maze = parcelMazeName(blocks, body);
            String named = lot == null ? lease : lease + " " + lot;
            if (box != null) {
                named = named + " " + box;
            }
            if (maze != null) {
                named = named + " " + maze;
            }
            return withCellAcl(occ, named, blocks, body);
        }
        String last = lastParcelPlaceName(blocks);
        if (last != null) {
            String lot = lastParcelLots(blocks);
            String box = lastParcelBoxes(blocks);
            String maze = lastParcelMazes(blocks);
            String rent = lastParcelLeases(blocks);
            String named = lot == null ? last : last + " " + lot;
            if (box != null) {
                named = named + " " + box;
            }
            if (maze != null) {
                named = named + " " + maze;
            }
            if (rent != null) {
                named = named + " " + rent;
            }
            String extras = lastParcelAcls(blocks);
            if (extras != null) {
                named = named + " " + extras;
                return withOccupants(named, blocks);
            }
            return withAcl(withOccupants(named, blocks), blocks);
        }
        String cube = blockPlaceName(blocks, body);
        if (cube != null) {
            return withAcl(withOccupancy(occ, cube), blocks);
        }
        String who = occupantsName(blocks);
        String stands = standsName(blocks);
        if (who != null && stands != null) {
            return withAcl(who + " · " + stands, blocks);
        }
        if (who != null) {
            return withAcl(who, blocks);
        }
        return withAcl(stands != null ? stands : "HALL", blocks);
    }

    /**
     * Occupancy objects on this world. Used off a slab so leftover HALL
     * is not the last word when door-zero still exists.
     */
    public static String occupantsName(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.occupantsLine(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /**
     * Occupancy cells as kind + x,y,z. Occupants stay names-only.
     */
    public static String standsName(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.standsLine(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /**
     * Extra grants and denials. Owner stays implicit. Empty with no extras.
     */
    public static String aclName(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.aclLine(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /**
     * Last driven capability and named result. DENIED stays visible
     * after inspect. Empty until a mutation.
     */
    public static String driveName(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.driveLine(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /**
     * Account key that last drove a mutation. Empty until a mutation.
     * Never a wallet type.
     */
    public static String actorName(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.actorLine(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /**
     * Cube address of the last mutation. Empty until a mutation.
     */
    public static String atName(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.atLine(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /** Cell extra-list under the boots. Street ACL stays for leftover HALL. */
    private static String withCellAcl(String occ, String named, WorldMesh blocks,
            ExploreBody body) {
        String extra = parcelAclName(blocks, body);
        if (extra != null) {
            return withOccupancy(occ, named + " " + extra);
        }
        return withAcl(withOccupancy(occ, named), blocks);
    }

    private static String withAcl(String place, WorldMesh blocks) {
        String acl = aclName(blocks);
        String named = acl == null ? place : place + " · " + acl;
        return withDrive(named, blocks);
    }

    private static String withDrive(String place, WorldMesh blocks) {
        String drive = driveName(blocks);
        String named = drive == null ? place : place + " · " + drive;
        return withActor(named, blocks);
    }

    private static String withActor(String place, WorldMesh blocks) {
        String actor = actorName(blocks);
        String named = actor == null ? place : place + " · " + actor;
        return withAt(named, blocks);
    }

    private static String withAt(String place, WorldMesh blocks) {
        String at = atName(blocks);
        if (at == null) {
            return place;
        }
        return place + " · " + at;
    }

    private static String withOccupants(String place, WorldMesh blocks) {
        String who = occupantsName(blocks);
        String stands = standsName(blocks);
        if (who == null && stands == null) {
            return place;
        }
        if (who == null) {
            return place + " · " + stands;
        }
        if (stands == null) {
            return place + " · " + who;
        }
        return place + " · " + who + " · " + stands;
    }

    /**
     * Occupancy cell under the boots when that x,z sits on a slab.
     * Start and goal still lead.
     */
    public static String occupancyName(WorldMesh blocks, ExploreBody body) {
        if (blocks == null || body == null || blocks.world() == null) {
            return null;
        }
        World world = blocks.world();
        int x = (int) Math.floor(body.x());
        int z = (int) Math.floor(body.z());
        if (occupancyAt(world.door() == null ? null : world.door().at(), world, x, z)) {
            return "DOOR";
        }
        if (occupancyAt(world.trap() == null ? null : world.trap().at(), world, x, z)) {
            return "TRAP";
        }
        if (occupancyAt(world.portal() == null ? null : world.portal().at(), world, x, z)) {
            return "PORTAL";
        }
        if (occupancyAt(world.npc() == null ? null : world.npc().at(), world, x, z)) {
            return "NPC";
        }
        return null;
    }

    private static boolean occupancyAt(BlockCoordinate at, World world, int x, int z) {
        if (at == null || at.x() != x || at.z() != z) {
            return false;
        }
        return !WorldOps.lotAt(world, at).isEmpty();
    }

    private static String withOccupancy(String occ, String place) {
        if (occ == null || occ.isEmpty()) {
            return place;
        }
        return occ + " " + place;
    }

    /**
     * Newest inspired toponym on the street. Not GIS. Used when the
     * boots are off the slab so a Generate name still reads in the hall.
     */
    public static String lastParcelPlaceName(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.lastPlaceName(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /** Newest slab origin as {@code x,z}. Empty worlds stay null. */
    public static String lastParcelLot(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.lastLot(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /** All slab origins as {@code x,z}, oldest first. Empty worlds stay null. */
    public static String lastParcelLots(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.streetLots(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /** Inclusive AABB of the newest slab. Empty worlds stay null. */
    public static String lastParcelBox(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.lastBox(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /** All inclusive AABBs, oldest first. Empty worlds stay null. */
    public static String lastParcelBoxes(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.streetBoxes(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /** Newest lab maze id on the street. Empty worlds stay null. Not a wallet. */
    public static String lastParcelMaze(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = "";
        for (Parcel parcel : blocks.world().parcels()) {
            if (parcel != null && !parcel.mazeRef().isEmpty()) {
                found = parcel.mazeRef();
            }
        }
        return found.isEmpty() ? null : found;
    }

    /** All lab maze ids, oldest first. Empty worlds stay null. Not a wallet. */
    public static String lastParcelMazes(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.streetMazes(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /** Newest account key on the street. Empty worlds stay null. Not a wallet. */
    public static String lastParcelLease(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.lastLeaseId(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /** Newest extra-list on the street. Empty until a grant or deny. */
    public static String lastParcelAcl(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = "";
        for (Parcel parcel : blocks.world().parcels()) {
            if (parcel == null) {
                continue;
            }
            String one = WorldOps.aclOf(blocks.world(), parcel.id());
            if (!one.isEmpty()) {
                found = one;
            }
        }
        return found.isEmpty() ? null : found;
    }

    /** All extra-lists, oldest first. Empty until a grant or deny. */
    public static String lastParcelAcls(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.aclLine(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /** All account keys on rented slabs, oldest first. Empty worlds stay null. */
    public static String lastParcelLeases(WorldMesh blocks) {
        if (blocks == null || blocks.world() == null) {
            return null;
        }
        String found = WorldOps.streetLeases(blocks.world());
        return found.isEmpty() ? null : found;
    }

    /** Slab origin under the boots as {@code x,z}. */
    public static String parcelLotName(WorldMesh blocks, ExploreBody body) {
        if (blocks == null || body == null || blocks.world() == null) {
            return null;
        }
        BlockCoordinate at = new BlockCoordinate(
                (int) Math.floor(body.x()), 0, (int) Math.floor(body.z()));
        String found = WorldOps.lotAt(blocks.world(), at);
        return found.isEmpty() ? null : found;
    }

    /** Lab maze id under the boots. Empty off a stamped plot. Not a wallet. */
    public static String parcelMazeName(WorldMesh blocks, ExploreBody body) {
        if (blocks == null || body == null || blocks.world() == null) {
            return null;
        }
        BlockCoordinate at = new BlockCoordinate(
                (int) Math.floor(body.x()), 0, (int) Math.floor(body.z()));
        String found = WorldOps.mazeAt(blocks.world(), at);
        return found.isEmpty() ? null : found;
    }

    /** Extra-list under the boots. Empty off a granted slab. */
    public static String parcelAclName(WorldMesh blocks, ExploreBody body) {
        if (blocks == null || body == null || blocks.world() == null) {
            return null;
        }
        BlockCoordinate at = new BlockCoordinate(
                (int) Math.floor(body.x()), 0, (int) Math.floor(body.z()));
        String found = WorldOps.aclAt(blocks.world(), at);
        return found.isEmpty() ? null : found;
    }

    /** Inclusive AABB under the boots. Empty off a stamped plot. */
    public static String parcelBoxName(WorldMesh blocks, ExploreBody body) {
        if (blocks == null || body == null || blocks.world() == null) {
            return null;
        }
        BlockCoordinate at = new BlockCoordinate(
                (int) Math.floor(body.x()), 0, (int) Math.floor(body.z()));
        String found = WorldOps.boxAt(blocks.world(), at);
        return found.isEmpty() ? null : found;
    }

    /**
     * Named parcel under the boots. Inspired toponym, not GIS.
     */
    public static String parcelPlaceName(WorldMesh blocks, ExploreBody body) {
        if (blocks == null || body == null || blocks.world() == null) {
            return null;
        }
        BlockCoordinate at = new BlockCoordinate(
                (int) Math.floor(body.x()), 0, (int) Math.floor(body.z()));
        for (Parcel parcel : blocks.world().parcels()) {
            if (parcel == null || parcel.placeName().isEmpty()) {
                continue;
            }
            if (parcel.bounds().contains(at)) {
                return parcel.placeName();
            }
        }
        return null;
    }

    /**
     * Lease string under the boots. Account key, not a wallet.
     */
    public static String parcelLeaseName(WorldMesh blocks, ExploreBody body) {
        if (blocks == null || body == null || blocks.world() == null) {
            return null;
        }
        BlockCoordinate at = new BlockCoordinate(
                (int) Math.floor(body.x()), 0, (int) Math.floor(body.z()));
        for (Parcel parcel : blocks.world().parcels()) {
            if (parcel == null || parcel.leaseId().isEmpty()) {
                continue;
            }
            if (parcel.bounds().contains(at)) {
                return parcel.leaseId();
            }
        }
        return null;
    }

    /**
     * First occupied cube in the torch beam. Discrete occupancy, not a hull.
     */
    public static String blockPlaceName(WorldMesh blocks, ExploreBody body) {
        if (blocks == null || body == null || blocks.world() == null) {
            return null;
        }
        double yaw = body.yaw();
        double sx = Math.sin(yaw);
        double sz = -Math.cos(yaw);
        for (double d = 0.45; d <= 4.0; d += 0.25) {
            double x = body.x() + sx * d;
            double z = body.z() + sz * d;
            for (double y : new double[] {0.45, ExploreBody.EYE_Y}) {
                if (!blocks.blocked(x, y, z)) {
                    continue;
                }
                BlockType type = blocks.world().get(new BlockCoordinate(
                        (int) Math.floor(x), (int) Math.floor(y), (int) Math.floor(z)));
                if (type.solid()) {
                    return type.name();
                }
            }
        }
        return null;
    }

    /**
     * Earned occupied cube — same automap BLOCK rule, not leftover empty HUD
     * on a slab the pocket already named.
     */
    public static boolean blockSeen(ExploreFog fog, WorldMesh blocks) {
        if (fog == null || blocks == null) {
            return false;
        }
        Set<BlockCoordinate> seen = new HashSet<>();
        for (WorldMesh.Triangle tri : blocks.triangles()) {
            if (tri == null || tri.at() == null || !seen.add(tri.at())) {
                continue;
            }
            int col = ExploreMesh.cellCol(tri.at().x() + 0.5);
            int row = ExploreMesh.cellRow(tri.at().z() + 0.5);
            if (fog.tileVisible(2 * row + 1, 2 * col + 1)) {
                return true;
            }
        }
        return false;
    }

    public static void keyBlockTint(float[] rgb) {
        mapStoneTint(MapKind.BLOCK, 0, rgb);
    }

    public static void keyBlockSoftTint(float[] rgb) {
        keyBlockTint(rgb);
        if (rgb == null || rgb.length < 3) {
            return;
        }
        rgb[0] *= MAP_MARK_SOFT_WEIGHT;
        rgb[1] *= MAP_MARK_SOFT_WEIGHT;
        rgb[2] *= MAP_MARK_SOFT_WEIGHT;
    }

    /** Visible start / goal — same well key, not leftover empty HUD on the ends. */
    public static boolean endSeen(ExploreFog fog, ExploreMesh mesh, TileType end) {
        if (fog == null || mesh == null || mesh.tiles() == null
                || (end != TileType.START && end != TileType.GOAL)) {
            return false;
        }
        TileType[][] tiles = mesh.tiles();
        for (int tr = 0; tr < tiles.length; tr++) {
            for (int tc = 0; tc < tiles[tr].length; tc++) {
                if (tiles[tr][tc] == end && fog.tileVisible(tr, tc)) {
                    return true;
                }
            }
        }
        return false;
    }

    /** Stood-on start / goal — same well names, not leftover HALL on the ends. */
    public static String endPlaceName(ExploreBody body, ExploreMesh mesh) {
        if (body == null || mesh == null || mesh.grid() == null || body.cell() == null) {
            return "HALL";
        }
        Point here = body.cell();
        if (here.equals(mesh.grid().start())) {
            return "START";
        }
        if (here.equals(mesh.grid().goal())) {
            return "GOAL";
        }
        return "HALL";
    }

    public static String caption(Status status) {
        if (status == null) {
            return "HALL";
        }
        return status.place() + "  " + status.facing() + "  " + status.stood();
    }

    public static String captionPlace(Status status) {
        return status == null || status.place() == null || status.place().isBlank()
                ? "HALL" : status.place();
    }

    /** START / GOAL glyphs — same well mint and coral, not leftover gold letters. */
    public static void captionPlaceTint(String place, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        if ("START".equals(place)) {
            set(rgb, MAP_START_R, MAP_START_G, MAP_START_B);
        } else if ("GOAL".equals(place)) {
            set(rgb, MAP_GOAL_R, MAP_GOAL_G, MAP_GOAL_B);
        } else if ("WOOD".equals(place)) {
            set(rgb, MAP_BLOCK_R, MAP_BLOCK_G, MAP_BLOCK_B);
        } else if ("DIRT".equals(place)) {
            set(rgb, MAP_BLOCK_R * 0.86f, MAP_BLOCK_G * 0.84f, MAP_BLOCK_B * 0.90f);
        } else if ("GLASS".equals(place)) {
            set(rgb, BLOCK_GLASS_R, BLOCK_GLASS_G, BLOCK_GLASS_B);
        } else if ("STONE".equals(place)) {
            set(rgb, MAP_WALL_R, MAP_WALL_G, MAP_WALL_B);
        } else {
            set(rgb, AIM_BRIGHT_R, AIM_BRIGHT_G, AIM_BRIGHT_B);
        }
    }

    public static void captionPlaceSoftTint(String place, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        set(rgb, CAPTION_SOFT_R, CAPTION_SOFT_G, CAPTION_SOFT_B);
        if ("START".equals(place)) {
            rgb[0] += (MAP_START_R - rgb[0]) * FLOOR_END_WEIGHT;
            rgb[1] += (MAP_START_G - rgb[1]) * FLOOR_END_WEIGHT;
            rgb[2] += (MAP_START_B - rgb[2]) * FLOOR_END_WEIGHT;
        } else if ("GOAL".equals(place)) {
            rgb[0] += (MAP_GOAL_R - rgb[0]) * FLOOR_END_WEIGHT;
            rgb[1] += (MAP_GOAL_G - rgb[1]) * FLOOR_END_WEIGHT;
            rgb[2] += (MAP_GOAL_B - rgb[2]) * FLOOR_END_WEIGHT;
        } else if ("WOOD".equals(place) || "DIRT".equals(place)
                || "GLASS".equals(place) || "STONE".equals(place)) {
            float[] ink = new float[3];
            captionPlaceTint(place, ink);
            rgb[0] += (ink[0] - rgb[0]) * FLOOR_END_WEIGHT;
            rgb[1] += (ink[1] - rgb[1]) * FLOOR_END_WEIGHT;
            rgb[2] += (ink[2] - rgb[2]) * FLOOR_END_WEIGHT;
        } else if (place != null && !place.isBlank() && !"HALL".equals(place)) {
            rgb[0] += (MAP_BLOCK_R - rgb[0]) * FLOOR_END_WEIGHT;
            rgb[1] += (MAP_BLOCK_G - rgb[1]) * FLOOR_END_WEIGHT;
            rgb[2] += (MAP_BLOCK_B - rgb[2]) * FLOOR_END_WEIGHT;
        }
    }

    public static String captionMeta(Status status) {
        if (status == null) {
            return "";
        }
        return status.facing() + "  " + status.stood();
    }

    /** Glyph advance for one caption character — same spacing as {@code paintCaptionPass}. */
    public static float captionAdvance(float cell, float gap) {
        return (GLYPH_W + 1) * cell + gap;
    }

    public static float captionWidth(String text, float cell, float gap) {
        if (text == null || text.isEmpty()) {
            return 0f;
        }
        return text.length() * captionAdvance(cell, gap);
    }

    /**
     * Crosshair Y in ortho NDC. Status eats the bottom strip, so aim sits in
     * the center of what is left — not the window midpoint.
     */
    public static float aimY() {
        return STATUS_H * 0.5f;
    }

    /** Bright gold core — same ink as status caption glyphs. */
    public static final float AIM_BRIGHT_R = 0.94f;
    public static final float AIM_BRIGHT_G = 0.78f;
    public static final float AIM_BRIGHT_B = 0.32f;
    /** Place name leads the strip — slightly larger than facing / stood. */
    public static final float CAPTION_PLACE_CELL = 0.026f;
    public static final float CAPTION_META_CELL = 0.018f;
    public static final float CAPTION_META_R = 0.62f;
    public static final float CAPTION_META_G = 0.52f;
    public static final float CAPTION_META_B = 0.28f;
    /** Caption glyph underglow — readable chrome on the dark strip. */
    public static final float CAPTION_SOFT_R = 0.42f;
    public static final float CAPTION_SOFT_G = 0.30f;
    public static final float CAPTION_SOFT_B = 0.10f;
    public static final float CAPTION_SOFT_PAD = 0.35f;
    /** Caption soft breath — same cadence as status / key chrome. */
    public static final float CAPTION_BREATH_MS = MAP_HERE_BREATH_MS;

    public static float captionSoftPad(double seconds) {
        double t = ((seconds * 1000.0) % CAPTION_BREATH_MS) / CAPTION_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return CAPTION_SOFT_PAD * (float) (0.88 + 0.24 * wave);
    }
    /** Dim underglow so the cross reads as chrome, not a hairline. */
    public static final float AIM_SOFT_R = 0.45f;
    public static final float AIM_SOFT_G = 0.32f;
    public static final float AIM_SOFT_B = 0.10f;
    public static final float AIM_ARM = 0.03f;
    public static final float AIM_SOFT_ARM = 0.048f;
    public static final float AIM_SOFT_THICK = 0.012f;
    /** Soft aim breath — same cadence as HUD key / automap presence. */
    public static final float AIM_BREATH_MS = MAP_HERE_BREATH_MS;

    public static float aimSoftArm(double seconds) {
        double t = ((seconds * 1000.0) % AIM_BREATH_MS) / AIM_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return AIM_SOFT_ARM * (float) (0.88 + 0.24 * wave);
    }

    public static float aimSoftThick(double seconds) {
        double t = ((seconds * 1000.0) % AIM_BREATH_MS) / AIM_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return AIM_SOFT_THICK * (float) (0.88 + 0.24 * wave);
    }
    /** Soft gold pad under key diamonds — same language as caption underglow. */
    public static final float KEY_SOFT_R = 0.42f;
    public static final float KEY_SOFT_G = 0.30f;
    public static final float KEY_SOFT_B = 0.10f;
    public static final float KEY_SOFT_PAD = 1.55f;
    /** Key pad breath — same cadence as automap HERE / story marks. */
    public static final float KEY_BREATH_MS = MAP_HERE_BREATH_MS;

    public static float keySoftPad(double seconds) {
        double t = ((seconds * 1000.0) % KEY_BREATH_MS) / KEY_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return KEY_SOFT_PAD * (float) (0.88 + 0.24 * wave);
    }
    /** Thin gold lip around the mood face so the portrait matches strip chrome. */
    public static final float FACE_LIP = 0.008f;
    public static final float FACE_LIP_CORE = 0.004f;
    /** Face lip breath — same cadence as aim / key presence. */
    public static final float FACE_BREATH_MS = MAP_HERE_BREATH_MS;

    public static float faceLip(double seconds) {
        double t = ((seconds * 1000.0) % FACE_BREATH_MS) / FACE_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return FACE_LIP * (float) (0.88 + 0.24 * wave);
    }

    public static float faceLipCore(double seconds) {
        double t = ((seconds * 1000.0) % FACE_BREATH_MS) / FACE_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return FACE_LIP_CORE * (float) (0.88 + 0.24 * wave);
    }

    public static void keyTint(int slot, int marks, int mood, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        boolean last = marks > 0 && slot == marks - 1;
        if (last && mood >= 2) {
            set(rgb, 0.78f, 0.22f, 0.16f);
        } else if (last && mood == 1) {
            set(rgb, 0.28f, 0.52f, 0.58f);
        } else {
            set(rgb, 0.82f, 0.62f, 0.18f);
        }
    }

    /** Idle bob so the torch is not a pasted sticker. */
    public static float handBob(double seconds) {
        return handBob(seconds, 0);
    }

    /**
     * {@code stride} in {@code [0, 1]} is how hard you are walking — a step
     * lifts the torch; standing still only breathes.
     */
    public static float handBob(double seconds, double stride) {
        double go = Math.max(0, Math.min(1, Math.abs(stride)));
        double amp = 0.018 + 0.028 * go;
        double hz = 5.2 + 5.5 * go;
        return (float) (Math.sin(seconds * hz) * amp);
    }

    /**
     * Lower-right torch above the status strip. Same band as Doom's weapon —
     * presence, not combat.
     */
    public static List<HandTri> handMesh(double aspect, float bob) {
        float ox = (float) (Math.max(0.55, aspect) * 0.48);
        float oy = -1f + STATUS_H + 0.06f + bob;
        List<HandTri> out = new ArrayList<>();
        // Fist / grip
        tri(out, ox - 0.02f, oy, ox + 0.12f, oy - 0.02f, ox + 0.10f, oy + 0.10f, HandPart.GRIP);
        tri(out, ox - 0.02f, oy, ox + 0.10f, oy + 0.10f, ox - 0.04f, oy + 0.08f, HandPart.GRIP);
        // Shaft
        tri(out, ox + 0.04f, oy + 0.08f, ox + 0.09f, oy + 0.08f, ox + 0.07f, oy + 0.28f, HandPart.SHAFT);
        tri(out, ox + 0.04f, oy + 0.08f, ox + 0.07f, oy + 0.28f, ox + 0.03f, oy + 0.26f, HandPart.SHAFT);
        // Flame
        tri(out, ox + 0.02f, oy + 0.26f, ox + 0.12f, oy + 0.26f, ox + 0.07f, oy + 0.42f, HandPart.FLAME);
        tri(out, ox + 0.04f, oy + 0.26f, ox + 0.10f, oy + 0.26f, ox + 0.07f, oy + 0.36f, HandPart.FLAME);
        return List.copyOf(out);
    }

    /** Sparse ash lofting in the torch beam — same hand anchor as {@link #handMesh}. */
    public static List<DustMote> dustMotes(double aspect, float bob, double seconds) {
        float ox = (float) (Math.max(0.55, aspect) * 0.48);
        float oy = -1f + STATUS_H + 0.06f + bob;
        List<DustMote> out = new ArrayList<>(DUST_COUNT);
        for (int i = 0; i < DUST_COUNT; i++) {
            float bx = ox + 0.02f + 0.14f * (((hash(i, 1) & 255) / 255f) - 0.15f);
            float by = oy + 0.22f + 0.28f * ((hash(i, 2) & 255) / 255f);
            float dx = (float) (0.012 * Math.sin(seconds * (1.1 + 0.17 * i) + i));
            float dy = (float) (0.018 * ((seconds * (0.08 + 0.01 * i)) % 1.0));
            if (dy < 0) {
                dy += 0.018f;
            }
            float a = 0.18f + 0.22f * flameFlicker(seconds + i * 0.07)
                    * (0.55f + 0.45f * ((hash(i, 3) & 255) / 255f));
            a = Math.max(0.08f, Math.min(0.45f, a));
            out.add(new DustMote(bx + dx, by + dy, DUST_HALF, a));
        }
        return List.copyOf(out);
    }

    public static void handTint(HandPart part, int mood, float[] rgb) {
        handTint(part, mood, rgb, 0);
    }

    public static void handTint(HandPart part, int mood, float[] rgb, double seconds) {
        if (rgb == null || rgb.length < 3 || part == null) {
            return;
        }
        int grim = Math.max(0, Math.min(2, mood));
        switch (part) {
            case GRIP -> {
                set(rgb, 0.72f, 0.48f, 0.30f);
                catchFlame(rgb, seconds, GRIP_CATCH);
            }
            case SHAFT -> {
                set(rgb, 0.28f, 0.18f, 0.12f);
                catchFlame(rgb, seconds, SHAFT_CATCH);
            }
            case FLAME -> {
                if (grim >= 2) {
                    set(rgb, 0.95f, 0.28f, 0.12f);
                } else if (grim == 1) {
                    set(rgb, 0.95f, 0.62f, 0.22f);
                } else {
                    set(rgb, 0.98f, 0.78f, 0.28f);
                }
                float flick = flameFlicker(seconds);
                rgb[0] = Math.min(1f, rgb[0] * flick);
                rgb[1] = Math.min(1f, rgb[1] * flick);
                rgb[2] = Math.min(1f, rgb[2] * Math.max(0.72f, flick * 0.92f));
            }
            default -> set(rgb, 0.5f, 0.5f, 0.5f);
        }
    }

    private static void catchFlame(float[] rgb, double seconds, float weight) {
        float flick = flameFlicker(seconds);
        float mix = Math.max(0f, Math.min(1f, weight * flick));
        rgb[0] = rgb[0] + (BLOOM_R - rgb[0]) * mix;
        rgb[1] = rgb[1] + (BLOOM_G - rgb[1]) * mix;
        rgb[2] = rgb[2] + (BLOOM_B - rgb[2]) * mix;
    }

    /** Uneven torch breath — not a metronome sine. */
    public static float flameFlicker(double seconds) {
        double a = Math.sin(seconds * 19.0);
        double b = Math.sin(seconds * 31.7 + 1.1);
        return (float) (0.82 + 0.18 * (0.55 + 0.45 * a + 0.22 * b));
    }

    /** World lamp rides the same flicker as the hand flame — soft, not strobe. */
    public static final float TORCH_BREATH_BASE = 0.92f;
    public static final float TORCH_BREATH_SPAN = 0.08f;

    public static float torchBreath(double seconds) {
        return TORCH_BREATH_BASE + TORCH_BREATH_SPAN * flameFlicker(seconds);
    }

    public static boolean glyphDot(char raw, int x, int y) {
        if (x < 0 || x >= GLYPH_W || y < 0 || y >= GLYPH_H) {
            return false;
        }
        long bits = glyphBits(Character.toUpperCase(raw));
        return ((bits >>> (y * GLYPH_W + x)) & 1L) == 1L;
    }

    public static void uv(ExploreMesh.Triangle tri, double x, double y, double z, float[] out) {
        if (tri == null || out == null || out.length < 2) {
            return;
        }
        if (tri.face() == ExploreMesh.Face.WALL) {
            double nx = (tri.y2() - tri.y1()) * (tri.z3() - tri.z1())
                    - (tri.z2() - tri.z1()) * (tri.y3() - tri.y1());
            double nz = (tri.x2() - tri.x1()) * (tri.y3() - tri.y1())
                    - (tri.y2() - tri.y1()) * (tri.x3() - tri.x1());
            double along = Math.abs(nx) > Math.abs(nz) ? z : x;
            out[0] = (float) (along / ExploreMesh.TILE);
            out[1] = (float) (y / ExploreMesh.WALL_HEIGHT);
            return;
        }
        out[0] = (float) (x / ExploreMesh.TILE);
        out[1] = (float) (z / ExploreMesh.TILE);
    }

    public static List<MapDot> automap(ExploreFog fog, ExploreMesh mesh, ExploreBody body,
                                      List<ExploreMarker> markers) {
        return automap(fog, mesh, body, markers, null);
    }

    public static List<MapDot> automap(ExploreFog fog, ExploreMesh mesh, ExploreBody body,
                                      List<ExploreMarker> markers, WorldMesh blocks) {
        if (fog == null || mesh == null || mesh.tiles() == null) {
            return List.of();
        }
        TileType[][] tiles = mesh.tiles();
        int minR = Integer.MAX_VALUE;
        int maxR = Integer.MIN_VALUE;
        int minC = Integer.MAX_VALUE;
        int maxC = Integer.MIN_VALUE;
        for (int tr = 0; tr < tiles.length; tr++) {
            for (int tc = 0; tc < tiles[tr].length; tc++) {
                if (!fog.tileVisible(tr, tc)) {
                    continue;
                }
                minR = Math.min(minR, tr);
                maxR = Math.max(maxR, tr);
                minC = Math.min(minC, tc);
                maxC = Math.max(maxC, tc);
            }
        }
        if (minR == Integer.MAX_VALUE) {
            return List.of();
        }
        List<MapDot> out = new ArrayList<>();
        for (int tr = minR; tr <= maxR; tr++) {
            for (int tc = minC; tc <= maxC; tc++) {
                if (!fog.tileVisible(tr, tc)) {
                    continue;
                }
                int x = project(tc, minC, maxC);
                int y = MAP - 1 - project(tr, minR, maxR);
                MapKind kind = mesh.solidTile(tr, tc) ? MapKind.WALL : MapKind.FLOOR;
                out.add(new MapDot(x, y, kind, "",
                        mapEdge(tr, tc, minR, maxR, minC, maxC)));
            }
        }
        if (blocks != null) {
            Set<BlockCoordinate> seen = new HashSet<>();
            for (WorldMesh.Triangle tri : blocks.triangles()) {
                if (tri == null || tri.at() == null || !seen.add(tri.at())) {
                    continue;
                }
                int col = ExploreMesh.cellCol(tri.at().x() + 0.5);
                int row = ExploreMesh.cellRow(tri.at().z() + 0.5);
                int tr = 2 * row + 1;
                int tc = 2 * col + 1;
                if (!fog.tileVisible(tr, tc)) {
                    continue;
                }
                out.add(new MapDot(project(tc, minC, maxC),
                        MAP - 1 - project(tr, minR, maxR), MapKind.BLOCK, "",
                        mapEdge(tr, tc, minR, maxR, minC, maxC)));
            }
        }
        for (int tr = minR; tr <= maxR; tr++) {
            for (int tc = minC; tc <= maxC; tc++) {
                if (!fog.tileVisible(tr, tc)) {
                    continue;
                }
                TileType tile = tiles[tr][tc];
                if (tile != TileType.START && tile != TileType.GOAL) {
                    continue;
                }
                out.add(new MapDot(project(tc, minC, maxC),
                        MAP - 1 - project(tr, minR, maxR),
                        tile == TileType.START ? MapKind.START : MapKind.GOAL, "",
                        mapEdge(tr, tc, minR, maxR, minC, maxC)));
            }
        }
        if (markers != null) {
            for (ExploreMarker mark : markers) {
                if (mark == null || mark.cell() == null) {
                    continue;
                }
                int tr = 2 * mark.cell().row() + 1;
                int tc = 2 * mark.cell().col() + 1;
                if (!fog.tileVisible(tr, tc)) {
                    continue;
                }
                out.add(new MapDot(project(tc, minC, maxC),
                        MAP - 1 - project(tr, minR, maxR), MapKind.MARK, mark.kind(),
                        mapEdge(tr, tc, minR, maxR, minC, maxC)));
            }
        }
        if (body != null) {
            int tc = (int) Math.round(body.x() / ExploreMesh.TILE + 1);
            int tr = (int) Math.round(body.z() / ExploreMesh.TILE + 1);
            out.add(new MapDot(project(tc, minC, maxC),
                    MAP - 1 - project(tr, minR, maxR), MapKind.HERE, "",
                    mapEdge(tr, tc, minR, maxR, minC, maxC)));
        }
        return List.copyOf(out);
    }

    public static List<EndPlace> endPlaces(ExploreFog fog, ExploreMesh mesh) {
        if (fog == null || mesh == null || mesh.tiles() == null) {
            return List.of();
        }
        TileType[][] tiles = mesh.tiles();
        List<EndPlace> out = new ArrayList<>();
        for (int tr = 0; tr < tiles.length; tr++) {
            for (int tc = 0; tc < tiles[tr].length; tc++) {
                TileType tile = tiles[tr][tc];
                if (tile != TileType.START && tile != TileType.GOAL) {
                    continue;
                }
                if (!fog.tileVisible(tr, tc)) {
                    continue;
                }
                out.add(new EndPlace(ExploreMesh.tileCenterX(tc), ExploreMesh.tileCenterZ(tr),
                        tile == TileType.START ? MapKind.START : MapKind.GOAL, tr, tc));
            }
        }
        return List.copyOf(out);
    }

    /**
     * Ground-facing occupied cubes. Stacked lids share the boot pad.
     * Discrete occupancy, not a hull.
     */
    public static List<BlockPlace> blockPlaces(WorldMesh blocks) {
        if (blocks == null) {
            return List.of();
        }
        List<BlockPlace> out = new ArrayList<>();
        Set<BlockCoordinate> seen = new HashSet<>();
        for (WorldMesh.Triangle tri : blocks.triangles()) {
            if (tri == null || tri.face() != WorldMesh.Face.NEG_Y || tri.at() == null) {
                continue;
            }
            if (blocks.world() != null && !blocks.world().contains(tri.at())) {
                continue;
            }
            if (!seen.add(tri.at())) {
                continue;
            }
            int col = ExploreMesh.cellCol(tri.at().x() + 0.5);
            int row = ExploreMesh.cellRow(tri.at().z() + 0.5);
            out.add(new BlockPlace(tri.at().x() + 0.5, tri.at().z() + 0.5, tri.type(),
                    2 * row + 1, 2 * col + 1));
        }
        return List.copyOf(out);
    }

    /** Automap gate — KEEP start mint, same as the well disc. */
    public static final float MAP_START_R = 0x3e / 255f;
    public static final float MAP_START_G = 0xe0 / 255f;
    public static final float MAP_START_B = 0x8f / 255f;
    /** Automap exit — same coral as the well goal. */
    public static final float MAP_GOAL_R = 0xff / 255f;
    public static final float MAP_GOAL_G = 0x5a / 255f;
    public static final float MAP_GOAL_B = 0x5f / 255f;
    /** End-pad breath — same cadence as story marks. */
    public static final float MAP_END_BREATH_MS = MAP_MARK_BREATH_MS;
    public static final float MAP_END_HALO = MAP_MARK_HALO;
    /** Same 0.22 rim as halls — leftover even mint/coral is not the last word on a gate. */
    public static final float MAP_END_EDGE_DIM = 0.22f;

    public static float mapEndHalo(double seconds) {
        return mapMarkHalo(seconds);
    }

    public static void mapEndTint(MapKind kind, float[] rgb) {
        mapEndTint(kind, rgb, 0);
    }

    public static void mapEndTint(MapKind kind, float[] rgb, double edge) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        if (kind == MapKind.GOAL) {
            set(rgb, MAP_GOAL_R, MAP_GOAL_G, MAP_GOAL_B);
        } else {
            set(rgb, MAP_START_R, MAP_START_G, MAP_START_B);
        }
        mixEndEdge(edge, rgb);
    }

    public static void mapEndSoftTint(MapKind kind, float[] rgb) {
        mapEndSoftTint(kind, rgb, 0);
    }

    public static void mapEndSoftTint(MapKind kind, float[] rgb, double edge) {
        mapEndTint(kind, rgb, 0);
        if (rgb == null || rgb.length < 3) {
            return;
        }
        rgb[0] *= MAP_MARK_SOFT_WEIGHT;
        rgb[1] *= MAP_MARK_SOFT_WEIGHT;
        rgb[2] *= MAP_MARK_SOFT_WEIGHT;
        mixEndEdge(edge, rgb);
    }

    public static void mixEndEdge(double edge, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        float t = (float) (MAP_END_EDGE_DIM * Math.min(1, Math.max(0, edge)));
        rgb[0] += (MAP_FLOOR_DIM_R - rgb[0]) * t;
        rgb[1] += (MAP_FLOOR_DIM_G - rgb[1]) * t;
        rgb[2] += (MAP_FLOOR_DIM_B - rgb[2]) * t;
    }

    /** Automap diamond — same inks as the HUD key, not leftover red on every mark. */
    public static void mapMarkTint(String kind, float[] rgb) {
        mapMarkTint(kind, rgb, 0);
    }

    public static void mapMarkTint(String kind, float[] rgb, double edge) {
        marker(kind, rgb);
        mixMarkEdge(edge, rgb);
    }

    public static void mapMarkSoftTint(String kind, float[] rgb) {
        mapMarkSoftTint(kind, rgb, 0);
    }

    public static void mapMarkSoftTint(String kind, float[] rgb, double edge) {
        mapMarkTint(kind, rgb, 0);
        if (rgb == null || rgb.length < 3) {
            return;
        }
        rgb[0] *= MAP_MARK_SOFT_WEIGHT;
        rgb[1] *= MAP_MARK_SOFT_WEIGHT;
        rgb[2] *= MAP_MARK_SOFT_WEIGHT;
        mixMarkEdge(edge, rgb);
    }

    public static void mixMarkEdge(double edge, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        float t = (float) (MAP_MARK_EDGE_DIM * Math.min(1, Math.max(0, edge)));
        rgb[0] += (MAP_FLOOR_DIM_R - rgb[0]) * t;
        rgb[1] += (MAP_FLOOR_DIM_G - rgb[1]) * t;
        rgb[2] += (MAP_FLOOR_DIM_B - rgb[2]) * t;
    }

    public static void marker(String kind, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        if ("BOSS".equals(kind)) {
            set(rgb, 0.72f, 0.18f, 0.12f);
        } else if ("ENTRANCE".equals(kind)) {
            set(rgb, 0.82f, 0.62f, 0.18f);
        } else {
            set(rgb, 0.28f, 0.52f, 0.58f);
        }
    }

    /** Story pillar — short post; boot matches wall skirting so it sits, not floats. */
    public static final float PILLAR_HALF = 0.16f;
    public static final float PILLAR_H = 0.95f;
    public static final float PILLAR_BOOT_FRAC = (float) CONTACT_BOOT_FRAC;
    public static final float PILLAR_BOOT_MIN = CONTACT_BOOT_MIN;
    /** Same lid band as corridor posts — the post meets the crown. */
    public static final float PILLAR_CROWN_FRAC = PILLAR_BOOT_FRAC;
    public static final float PILLAR_CROWN_MIN = PILLAR_BOOT_MIN;

    public record PillarTri(float x1, float y1, float z1,
                            float x2, float y2, float z2,
                            float x3, float y3, float z3,
                            boolean boot, boolean crown) {
    }

    public static List<PillarTri> pillarMesh(double cx, double cz) {
        float x0 = (float) (cx - PILLAR_HALF);
        float x1 = (float) (cx + PILLAR_HALF);
        float z0 = (float) (cz - PILLAR_HALF);
        float z1 = (float) (cz + PILLAR_HALF);
        float yb = PILLAR_H * PILLAR_BOOT_FRAC;
        float yc = PILLAR_H * (1f - PILLAR_CROWN_FRAC);
        List<PillarTri> out = new ArrayList<>();
        addPillarBox(out, x0, x1, 0, yb, z0, z1, true, false);
        addPillarBox(out, x0, x1, yb, yc, z0, z1, false, false);
        addPillarBox(out, x0, x1, yc, PILLAR_H, z0, z1, false, true);
        return List.copyOf(out);
    }

    public static void pillarTint(float[] markerRgb, boolean boot, float[] out) {
        pillarTint(markerRgb, boot, false, out);
    }

    public static void pillarTint(float[] markerRgb, boolean boot, boolean crown,
                                  float[] out) {
        if (out == null || out.length < 3) {
            return;
        }
        float s = boot ? PILLAR_BOOT_MIN : crown ? PILLAR_CROWN_MIN : 1f;
        if (markerRgb == null || markerRgb.length < 3) {
            set(out, 0.4f * s, 0.28f * s, 0.14f * s);
            return;
        }
        set(out, markerRgb[0] * s, markerRgb[1] * s, markerRgb[2] * s);
    }

    private static void addPillarBox(List<PillarTri> out, float x0, float x1,
                                    float y0, float y1, float z0, float z1,
                                    boolean boot, boolean crown) {
        // +Z / −Z / −X / +X / lid
        out.add(new PillarTri(x0, y0, z0, x1, y0, z0, x1, y1, z0, boot, crown));
        out.add(new PillarTri(x0, y0, z0, x1, y1, z0, x0, y1, z0, boot, crown));
        out.add(new PillarTri(x0, y0, z1, x1, y1, z1, x1, y0, z1, boot, crown));
        out.add(new PillarTri(x0, y0, z1, x0, y1, z1, x1, y1, z1, boot, crown));
        out.add(new PillarTri(x0, y0, z0, x0, y1, z0, x0, y1, z1, boot, crown));
        out.add(new PillarTri(x0, y0, z0, x0, y1, z1, x0, y0, z1, boot, crown));
        out.add(new PillarTri(x1, y0, z0, x1, y0, z1, x1, y1, z1, boot, crown));
        out.add(new PillarTri(x1, y0, z0, x1, y1, z1, x1, y1, z0, boot, crown));
        out.add(new PillarTri(x0, y1, z0, x1, y1, z0, x1, y1, z1, boot, crown));
        out.add(new PillarTri(x0, y1, z0, x1, y1, z1, x0, y1, z1, boot, crown));
    }

    /** Soft floor disc under corridor story pillars — place, not a furniture stick. */
    public static final float PLACE_PAD_R = 0.42f;
    /**
     * Wider than half a cube so the disc stains the corridor around the
     * slab, not leftover bare stone under a 1×1 boot.
     */
    public static final float BLOCK_PAD_R = 0.72f;
    public static final float PLACE_PAD_Y = 0.02f;
    public static final int PLACE_PAD_SEGS = 12;
    public static final float PLACE_PAD_DIM = 0.42f;
    /** Corridor place-pad breath — same cadence as automap HERE. */
    public static final float PLACE_PAD_BREATH_MS = MAP_HERE_BREATH_MS;

    public static float placePadDim(double seconds) {
        double t = ((seconds * 1000.0) % PLACE_PAD_BREATH_MS) / PLACE_PAD_BREATH_MS;
        double wave = 0.5 - 0.5 * Math.cos(t * Math.PI * 2.0);
        return PLACE_PAD_DIM * (float) (0.88 + 0.24 * wave);
    }

    public static void placePadTint(float[] markerRgb, float[] out) {
        placePadTint(markerRgb, out, 0);
    }

    public static void placePadTint(float[] markerRgb, float[] out, double seconds) {
        placePadTint(markerRgb, out, seconds, 0);
    }

    public static void placePadTint(float[] markerRgb, float[] out, double seconds, double edge) {
        if (out == null || out.length < 3) {
            return;
        }
        float dim = placePadDim(seconds);
        if (markerRgb == null || markerRgb.length < 3) {
            set(out, 0.2f * (dim / PLACE_PAD_DIM), 0.14f * (dim / PLACE_PAD_DIM),
                    0.08f * (dim / PLACE_PAD_DIM));
            mixHereEdge(edge, out);
            return;
        }
        set(out, markerRgb[0] * dim, markerRgb[1] * dim, markerRgb[2] * dim);
        mixHereEdge(edge, out);
    }

    static String facing(double yaw) {
        double a = yaw;
        while (a <= -Math.PI) {
            a += Math.PI * 2.0;
        }
        while (a > Math.PI) {
            a -= Math.PI * 2.0;
        }
        if (a > Math.PI * 0.75 || a <= -Math.PI * 0.75) {
            return "S";
        }
        if (a > Math.PI * 0.25) {
            return "E";
        }
        if (a < -Math.PI * 0.25) {
            return "W";
        }
        return "N";
    }

    private static ExploreMarker nearestVisible(ExploreFog fog, ExploreBody body,
                                               List<ExploreMarker> markers) {
        if (fog == null || markers == null) {
            return null;
        }
        Point here = body == null ? new Point(0, 0) : body.cell();
        ExploreMarker best = null;
        double bestDist = Double.POSITIVE_INFINITY;
        for (ExploreMarker mark : markers) {
            if (mark == null || mark.cell() == null) {
                continue;
            }
            int tr = 2 * mark.cell().row() + 1;
            int tc = 2 * mark.cell().col() + 1;
            if (!fog.tileVisible(tr, tc)) {
                continue;
            }
            double dist = Math.hypot(mark.cell().row() - here.row(),
                    mark.cell().col() - here.col());
            if (dist < bestDist) {
                bestDist = dist;
                best = mark;
            }
        }
        return best;
    }

    private static int countVisible(ExploreFog fog, List<ExploreMarker> markers) {
        if (fog == null || markers == null) {
            return 0;
        }
        int n = 0;
        for (ExploreMarker mark : markers) {
            if (mark == null || mark.cell() == null) {
                continue;
            }
            if (fog.tileVisible(2 * mark.cell().row() + 1, 2 * mark.cell().col() + 1)) {
                n++;
            }
        }
        return n;
    }

    private static String placeName(String kind) {
        if ("BOSS".equals(kind)) {
            return "BOSS";
        }
        if ("ENTRANCE".equals(kind)) {
            return "ENTRANCE";
        }
        if ("TREASURE".equals(kind) || "VAULT".equals(kind)) {
            return "VAULT";
        }
        return "HALL";
    }

    private static int mood(String kind) {
        if ("BOSS".equals(kind)) {
            return 2;
        }
        if ("TREASURE".equals(kind) || "VAULT".equals(kind)) {
            return 1;
        }
        return 0;
    }

    private static int[] mouth(int grim, int px) {
        if (grim == 1 && px >= 2 && px <= 5) {
            return rgbBytes(92, 36, 28);
        }
        if (grim == 2 && px >= 3 && px <= 4) {
            return rgbBytes(48, 22, 18);
        }
        if (grim == 0 && (px == 3 || px == 4)) {
            return rgbBytes(92, 48, 36);
        }
        return rgbBytes(186, 128, 78);
    }

    private static long glyphBits(char c) {
        // Exactly 35 cells (5×7), row-major. long — int only holds 32 bits.
        return switch (c) {
            case '0' -> bits(".###.#...##...##...##...##...#.###.");
            case '1' -> bits("..#....##....#....#....#....#.#####");
            case '2' -> bits(".###.#...#....#..##..#...#....#####");
            case '3' -> bits(".###.#...#....#.###.....##...#.###.");
            case '4' -> bits("#...##...#.#...######....#....#...#");
            case '5' -> bits("######....#.....####....##...#.###.");
            case '6' -> bits(".###.#....#....####.#...##...#.###.");
            case '7' -> bits("#####....#...#...#...#....#....#...");
            case '8' -> bits(".###.#...##...#.###.#...##...#.###.");
            case '9' -> bits(".###.#...##...#.####.....#....#.###");
            case 'A' -> bits(".###.#...##...#######...##...##...#");
            case 'B' -> bits("####.#...##...#####.#...##...#####.");
            case 'C' -> bits(".###.#...##....#....#....#...#.###.");
            case 'D' -> bits("####.#...##...##...##...##...#####.");
            case 'E' -> bits("######....#....####.#....#....#####");
            case 'F' -> bits("######....#....####.#....#....#....");
            case 'G' -> bits(".###.#....#....#.##.#...##...#.###.");
            case 'H' -> bits("#...##...##...#######...##...##...#");
            case 'I' -> bits("#####..#....#....#....#....#..#####");
            case 'J' -> bits(".####...#....#....#....#.#..#..##..");
            case 'K' -> bits("#...##..#.#.#..##...#.#..#..#.#...#");
            case 'L' -> bits("#....#....#....#....#....#....#####");
            case 'M' -> bits("#...###.###.#.##.#.##...##...##...#");
            case 'N' -> bits("#...###..##.#.##.#.##..###...##...#");
            case 'O' -> bits(".###.#...##...##...##...##...#.###.");
            case 'P' -> bits("####.#...##...#####.#....#....#....");
            case 'Q' -> bits(".###.#...##...##...##.#.##..#..##.#");
            case 'R' -> bits("####.#...##...#####.#.#.##..##...#.");
            case 'S' -> bits(".####.#....#....###.....#....#####.");
            case 'T' -> bits("#####..#....#....#....#....#....#..");
            case 'U' -> bits("#...##...##...##...##...##...#.###.");
            case 'V' -> bits("#...##...##...##...##...#.#.#...#..");
            case 'W' -> bits("#...##...##...##.#.##.#.##.#.#.#.#.");
            case 'X' -> bits("#...##...#.#.#...#...#.#.#...##...#");
            case 'Y' -> bits("#...##...#.#.#...#....#....#....#..");
            case 'Z' -> bits("#####....#...#...#...#...#....#####");
            case '-' -> bits("....................#####..........");
            default -> 0L;
        };
    }

    private static long bits(String pattern) {
        if (pattern == null || pattern.length() != GLYPH_W * GLYPH_H) {
            return 0L;
        }
        long out = 0L;
        for (int i = 0; i < pattern.length(); i++) {
            char ch = pattern.charAt(i);
            if (ch == '#' || ch == '1') {
                out |= 1L << i;
            }
        }
        return out;
    }

    /** Occupied-cube materials — torch lamp, not leftover well ice. */
    public static final float BLOCK_STONE_R = 0.40f;
    public static final float BLOCK_STONE_G = 0.30f;
    public static final float BLOCK_STONE_B = 0.20f;
    public static final float BLOCK_DIRT_R = 0.50f;
    public static final float BLOCK_DIRT_G = 0.32f;
    public static final float BLOCK_DIRT_B = 0.16f;
    public static final float BLOCK_WOOD_R = 0.58f;
    public static final float BLOCK_WOOD_G = 0.38f;
    public static final float BLOCK_WOOD_B = 0.18f;
    public static final float BLOCK_GLASS_R = 0.55f;
    public static final float BLOCK_GLASS_G = 0.64f;
    public static final float BLOCK_GLASS_B = 0.58f;

    public static void blockPlaceTint(BlockType type, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        blockTint(type == null ? BlockType.STONE : type, WorldMesh.Face.POS_Y, rgb);
    }

    public static void blockTint(BlockType type, WorldMesh.Face face, float[] rgb) {
        BlockType kind = type == null ? BlockType.STONE : type;
        float r;
        float g;
        float b;
        switch (kind) {
            case DIRT -> {
                r = BLOCK_DIRT_R;
                g = BLOCK_DIRT_G;
                b = BLOCK_DIRT_B;
            }
            case WOOD -> {
                r = BLOCK_WOOD_R;
                g = BLOCK_WOOD_G;
                b = BLOCK_WOOD_B;
            }
            case GLASS -> {
                r = BLOCK_GLASS_R;
                g = BLOCK_GLASS_G;
                b = BLOCK_GLASS_B;
            }
            default -> {
                r = BLOCK_STONE_R;
                g = BLOCK_STONE_G;
                b = BLOCK_STONE_B;
            }
        }
        float shade = face == null ? 1f : switch (face) {
            case POS_Y -> 1.12f;
            case NEG_Y -> 0.72f;
            case POS_X, NEG_X -> 0.88f;
            case POS_Z, NEG_Z -> 1.00f;
        };
        set(rgb, Math.min(1f, r * shade), Math.min(1f, g * shade), Math.min(1f, b * shade));
    }

    /**
     * Side-face boot — same skirting as corridor posts so a slab sits,
     * not leftover even wood down to the floor.
     */
    public static float blockContactShade(WorldMesh.Triangle tri) {
        if (tri == null) {
            return 1f;
        }
        if (tri.face() == WorldMesh.Face.POS_Y || tri.face() == WorldMesh.Face.NEG_Y) {
            return blockLidContactShade(tri);
        }
        double midY = (tri.y1() + tri.y2() + tri.y3()) / 3.0;
        double base = tri.at() == null ? Math.floor(midY) : tri.at().y();
        return wallContactShade((midY - base) * ExploreMesh.WALL_HEIGHT);
    }

    /** Soft lid rim — dark toward the cube edge so the top meets the posts. */
    public static float blockLidContactShade(WorldMesh.Triangle tri) {
        if (tri == null || (tri.face() != WorldMesh.Face.POS_Y
                && tri.face() != WorldMesh.Face.NEG_Y)) {
            return 1f;
        }
        double cx = (tri.x1() + tri.x2() + tri.x3()) / 3.0;
        double cz = (tri.z1() + tri.z2() + tri.z3()) / 3.0;
        double bx = tri.at() == null ? Math.floor(cx) + 0.5 : tri.at().x() + 0.5;
        double bz = tri.at() == null ? Math.floor(cz) + 0.5 : tri.at().z() + 0.5;
        double edge = Math.min(1, Math.hypot(cx - bx, cz - bz) / 0.5);
        return CONTACT_CROWN_MIN + (1f - CONTACT_CROWN_MIN) * (1f - (float) edge);
    }

    /**
     * Lamp brightness only — materials already name the cube; do not hue-mix
     * leftover torch brown over wood or glass.
     */
    public static void blockTint(WorldMesh.Triangle tri, float[] rgb,
                                 double eyeX, double eyeZ, double yaw, double seconds) {
        blockTint(tri, rgb, eyeX, eyeZ, yaw, seconds, 0);
    }

    /**
     * Occupancy glass hue — door, trap, portal, NPC. Mesh type stays glass.
     */
    public static void occupancyTint(String who, float[] rgb) {
        if (who == null || who.isEmpty() || rgb == null || rgb.length < 3) {
            return;
        }
        switch (who) {
            case "door" -> {
                rgb[0] = Math.min(1f, rgb[0] * 1.18f);
                rgb[1] *= 0.82f;
                rgb[2] *= 0.72f;
            }
            case "trap" -> {
                rgb[0] = Math.min(1f, rgb[0] * 1.08f);
                rgb[1] *= 0.70f;
                rgb[2] *= 0.55f;
            }
            case "portal" -> {
                rgb[0] *= 0.78f;
                rgb[1] *= 0.88f;
                rgb[2] = Math.min(1f, rgb[2] * 1.22f);
            }
            case "npc" -> {
                rgb[0] *= 0.88f;
                rgb[1] = Math.min(1f, rgb[1] * 1.12f);
                rgb[2] *= 0.90f;
            }
            default -> {
            }
        }
    }

    public static void blockTint(WorldMesh.Triangle tri, float[] rgb,
                                 double eyeX, double eyeZ, double yaw, double seconds,
                                 double edge) {
        blockTint(tri, rgb, eyeX, eyeZ, yaw, seconds, edge, null);
    }

    public static void blockTint(WorldMesh.Triangle tri, float[] rgb,
                                 double eyeX, double eyeZ, double yaw, double seconds,
                                 double edge, World world) {
        if (tri == null) {
            blockTint(BlockType.STONE, null, rgb);
            mixHereEdge(edge, rgb);
            return;
        }
        blockTint(tri.type(), tri.face(), rgb);
        if (tri.type() == BlockType.GLASS) {
            occupancyTint(WorldOps.occupantAt(world, tri.at()), rgb);
        }
        float boot = blockContactShade(tri);
        if (rgb != null && rgb.length >= 3) {
            rgb[0] *= boot;
            rgb[1] *= boot;
            rgb[2] *= boot;
        }
        mixHereEdge(edge, rgb);
        if (Double.isNaN(eyeX) || Double.isNaN(eyeZ)) {
            return;
        }
        double cx = (tri.x1() + tri.x2() + tri.x3()) / 3.0;
        double cz = (tri.z1() + tri.z2() + tri.z3()) / 3.0;
        double dx = cx - eyeX;
        double dz = cz - eyeZ;
        double dist = Math.hypot(dx, dz);
        double facing = 1;
        if (dist > 1e-6) {
            facing = (dx * Math.sin(yaw) + dz * (-Math.cos(yaw))) / dist;
        }
        float lamp = (float) (0.40 + 0.60 * Math.max(0, facing)
                * Math.max(0, 1.0 - dist / TORCH_REACH));
        lamp *= torchBreath(seconds);
        rgb[0] = Math.min(1f, rgb[0] * lamp);
        rgb[1] = Math.min(1f, rgb[1] * lamp);
        rgb[2] = Math.min(1f, rgb[2] * lamp);
    }

    /** Start / goal floor wash — names the ends, still stone, not a neon slab. */
    public static final float FLOOR_END_WEIGHT = 0.42f;
    /** Same wash on the lid so looking up names the ends. */
    public static final float CEILING_END_WEIGHT = FLOOR_END_WEIGHT;

    private static void floor(ExploreMesh.Triangle tri, float[] rgb) {
        float check = ((tri.tr() + tri.tc()) & 1) == 0 ? 1f : 0.82f;
        float skirt = floorContactShade(tri);
        float[] ink = endStone(0.34f, 0.24f, 0.14f, tri.tile(), FLOOR_END_WEIGHT);
        set(rgb, ink[0] * check * skirt, ink[1] * check * skirt, ink[2] * check * skirt);
    }

    private static void ceiling(ExploreMesh.Triangle tri, float[] rgb) {
        float crown = ceilingContactShade(tri);
        float[] ink = endStone(CEILING_R, CEILING_G, CEILING_B, tri.tile(), CEILING_END_WEIGHT);
        set(rgb, ink[0] * crown, ink[1] * crown, ink[2] * crown);
    }

    private static float[] endStone(float r, float g, float b, TileType tile, float weight) {
        if (tile == TileType.START) {
            return new float[] {
                    r + (MAP_START_R - r) * weight,
                    g + (MAP_START_G - g) * weight,
                    b + (MAP_START_B - b) * weight
            };
        }
        if (tile == TileType.GOAL) {
            return new float[] {
                    r + (MAP_GOAL_R - r) * weight,
                    g + (MAP_GOAL_G - g) * weight,
                    b + (MAP_GOAL_B - b) * weight
            };
        }
        return new float[] {r, g, b};
    }

    private static void wall(ExploreMesh.Triangle tri, float[] rgb) {
        double nx = (tri.y2() - tri.y1()) * (tri.z3() - tri.z1())
                - (tri.z2() - tri.z1()) * (tri.y3() - tri.y1());
        double nz = (tri.x2() - tri.x1()) * (tri.y3() - tri.y1())
                - (tri.y2() - tri.y1()) * (tri.x3() - tri.x1());
        boolean eastWest = Math.abs(nx) > Math.abs(nz);
        double midY = (tri.y1() + tri.y2() + tri.y3()) / 3.0;
        float boot = wallContactShade(midY);
        float stripe = stripe(tri, eastWest);
        float shade = boot * stripe;
        if (eastWest) {
            set(rgb, 0.48f * shade, 0.28f * shade, 0.16f * shade);
        } else {
            set(rgb, 0.64f * shade, 0.40f * shade, 0.22f * shade);
        }
    }

    /**
     * Soft skirting on the wall — dark at the floor and the crown, full in the
     * mid-band so the tunnel has a boot and a lid.
     */
    public static float wallContactShade(double midY) {
        double yFrac = Math.max(0, Math.min(1, midY / ExploreMesh.WALL_HEIGHT));
        if (yFrac < CONTACT_BOOT_FRAC) {
            float t = (float) (yFrac / CONTACT_BOOT_FRAC);
            return CONTACT_BOOT_MIN + (1f - CONTACT_BOOT_MIN) * t;
        }
        if (yFrac > 1.0 - CONTACT_CROWN_FRAC) {
            float t = (float) ((1.0 - yFrac) / CONTACT_CROWN_FRAC);
            return CONTACT_CROWN_MIN + (1f - CONTACT_CROWN_MIN) * t;
        }
        return 1f;
    }

    /** Soft skirting on the floor — dark toward the tile rim where walls meet. */
    public static float floorContactShade(ExploreMesh.Triangle tri) {
        if (tri == null || tri.face() != ExploreMesh.Face.FLOOR) {
            return 1f;
        }
        double cx = (tri.x1() + tri.x2() + tri.x3()) / 3.0;
        double cz = (tri.z1() + tri.z2() + tri.z3()) / 3.0;
        double tcx = ExploreMesh.tileCenterX(tri.tc());
        double tcz = ExploreMesh.tileCenterZ(tri.tr());
        double half = ExploreMesh.TILE / 2.0;
        double lx = Math.abs(cx - tcx) / half;
        double lz = Math.abs(cz - tcz) / half;
        double rim = Math.max(0, Math.min(1, Math.max(lx, lz)));
        if (rim <= FLOOR_CONTACT_START) {
            return 1f;
        }
        float t = (float) ((rim - FLOOR_CONTACT_START) / (1.0 - FLOOR_CONTACT_START));
        return 1f - FLOOR_CONTACT_DIM * t;
    }

    /** Soft crown on the ceiling — dark toward the tile rim where walls meet. */
    public static float ceilingContactShade(ExploreMesh.Triangle tri) {
        if (tri == null || tri.face() != ExploreMesh.Face.CEILING) {
            return 1f;
        }
        double cx = (tri.x1() + tri.x2() + tri.x3()) / 3.0;
        double cz = (tri.z1() + tri.z2() + tri.z3()) / 3.0;
        double tcx = ExploreMesh.tileCenterX(tri.tc());
        double tcz = ExploreMesh.tileCenterZ(tri.tr());
        double half = ExploreMesh.TILE / 2.0;
        double lx = Math.abs(cx - tcx) / half;
        double lz = Math.abs(cz - tcz) / half;
        double rim = Math.max(0, Math.min(1, Math.max(lx, lz)));
        if (rim <= CEILING_CONTACT_START) {
            return 1f;
        }
        float t = (float) ((rim - CEILING_CONTACT_START) / (1.0 - CEILING_CONTACT_START));
        return 1f - CEILING_CONTACT_DIM * t;
    }

    private static float stripe(ExploreMesh.Triangle tri, boolean eastWest) {
        double u = eastWest
                ? (tri.z1() + tri.z2() + tri.z3()) / 3.0
                : (tri.x1() + tri.x2() + tri.x3()) / 3.0;
        int band = (int) Math.floor(u / ExploreMesh.TILE);
        return (band & 1) == 0 ? 1f : 0.84f;
    }

    private static void torch(ExploreMesh.Triangle tri, double eyeX, double eyeZ,
                             double yaw, float[] rgb, double seconds) {
        double cx = (tri.x1() + tri.x2() + tri.x3()) / 3.0;
        double cz = (tri.z1() + tri.z2() + tri.z3()) / 3.0;
        double dx = cx - eyeX;
        double dz = cz - eyeZ;
        double dist = Math.hypot(dx, dz);
        double facing = 1;
        if (dist > 1e-6) {
            facing = (dx * Math.sin(yaw) + dz * (-Math.cos(yaw))) / dist;
        }
        float lamp = (float) (0.40 + 0.60 * Math.max(0, facing)
                * Math.max(0, 1.0 - dist / TORCH_REACH));
        lamp *= torchBreath(seconds);
        boolean wall = tri.face() == ExploreMesh.Face.WALL;
        boolean lid = tri.face() == ExploreMesh.Face.CEILING;
        float weight = wall ? TORCH_WALL_WARM_WEIGHT
                : lid ? TORCH_CEILING_WARM_WEIGHT : TORCH_FLOOR_WARM_WEIGHT;
        float warmR = wall ? TORCH_WALL_WARM_R : TORCH_FLOOR_WARM_R;
        float warmG = wall ? TORCH_WALL_WARM_G : TORCH_FLOOR_WARM_G;
        float warmB = wall ? TORCH_WALL_WARM_B : TORCH_FLOOR_WARM_B;
        boolean endStone = !wall && (tri.tile() == TileType.START || tri.tile() == TileType.GOAL);
        if (!endStone) {
            float mix = Math.max(0f, Math.min(1f, lamp * weight));
            rgb[0] = rgb[0] + (warmR - rgb[0]) * mix;
            rgb[1] = rgb[1] + (warmG - rgb[1]) * mix;
            rgb[2] = rgb[2] + (warmB - rgb[2]) * mix;
        }
        rgb[0] = Math.min(1f, rgb[0] * lamp);
        rgb[1] = Math.min(1f, rgb[1] * lamp);
        rgb[2] = Math.min(1f, rgb[2] * lamp);
    }

    public static double mapEdge(int tr, int tc, int minR, int maxR, int minC, int maxC) {
        double cx = (minC + maxC) / 2.0;
        double cy = (minR + maxR) / 2.0;
        double dx = (tc - cx) / Math.max(1, (maxC - minC + 1) / 2.0);
        double dy = (tr - cy) / Math.max(1, (maxR - minR + 1) / 2.0);
        return Math.min(1, Math.hypot(dx, dy));
    }

    private static int project(int value, int min, int max) {
        int span = Math.max(1, max - min);
        return (int) Math.round((value - min) * (MAP - 1) / (double) span);
    }

    private static void set(float[] rgb, float r, float g, float b) {
        rgb[0] = r;
        rgb[1] = g;
        rgb[2] = b;
    }

    private static void tri(List<HandTri> out, float x1, float y1, float x2, float y2,
                            float x3, float y3, HandPart part) {
        out.add(new HandTri(x1, y1, x2, y2, x3, y3, part));
    }

    @FunctionalInterface
    private interface Texel {
        int[] at(int x, int y);
    }

    private static byte[] raster(Texel texel) {
        byte[] out = new byte[TEX * TEX * 4];
        for (int y = 0; y < TEX; y++) {
            for (int x = 0; x < TEX; x++) {
                int[] rgb = texel.at(x, y);
                int i = (y * TEX + x) * 4;
                out[i] = (byte) rgb[0];
                out[i + 1] = (byte) rgb[1];
                out[i + 2] = (byte) rgb[2];
                out[i + 3] = (byte) 255;
            }
        }
        return out;
    }

    private static int[] rgbBytes(int r, int g, int b) {
        return new int[] {clampByte(r), clampByte(g), clampByte(b)};
    }

    private static int clampByte(int v) {
        return Math.max(0, Math.min(255, v));
    }

    private static int hash(int x, int y) {
        return (x * 374761393 + y * 668265263) >>> 8;
    }
}
