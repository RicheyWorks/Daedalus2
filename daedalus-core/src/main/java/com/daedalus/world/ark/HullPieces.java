// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * G376 The Hull Pieces: the twelve pentomino hull pieces (F I L N P T U V W X Y Z), each made of
 * five squares. Every piece is turned and flipped into its distinct orientations, and a rectangle
 * of hull is tiled with a chosen set of pieces, each used once, by handing the placements to the
 * G371 exact-cover solver (one column per piece and one per hull cell).
 */
public final class HullPieces {

    public static final String QUEST_ID = "q_hull_pieces";

    public static final String NAMES = "FILNPTUVWXYZ";

    private static final String[][] SHAPES = {
        {".##", "##.", ".#."}, {"#####"}, {"####", "#..."}, {"###.", "..##"}, {"###", "##."},
        {"###", ".#.", ".#."}, {"#.#", "###"}, {"#..", "#..", "###"}, {"#..", "##.", ".##"},
        {".#.", "###", ".#."}, {"####", ".#.."}, {"##.", ".#.", ".##"}};

    private HullPieces() { }

    private static int[][] cellsOf(int piece) {
        List<int[]> out = new ArrayList<>();
        String[] rows = SHAPES[piece];
        for (int r = 0; r < rows.length; r++) {
            for (int c = 0; c < rows[r].length(); c++) {
                if (rows[r].charAt(c) == '#') {
                    out.add(new int[] {r, c});
                }
            }
        }
        return out.toArray(new int[0][]);
    }

    private static int[][] normalized(int[][] cells) {
        int minR = Integer.MAX_VALUE;
        int minC = Integer.MAX_VALUE;
        for (int[] p : cells) {
            minR = Math.min(minR, p[0]);
            minC = Math.min(minC, p[1]);
        }
        int[][] out = new int[cells.length][];
        for (int i = 0; i < cells.length; i++) {
            out[i] = new int[] {cells[i][0] - minR, cells[i][1] - minC};
        }
        Arrays.sort(out, (a, b) -> a[0] != b[0] ? Integer.compare(a[0], b[0]) : Integer.compare(a[1], b[1]));
        return out;
    }

    /** Distinct orientations (turns and flips) of a piece, each as sorted {row, col} cells. */
    public static int[][][] orientations(int piece) {
        if (piece < 0 || piece >= 12) {
            throw new IllegalArgumentException("piece 0..11");
        }
        int[][] base = cellsOf(piece);
        Set<String> seen = new HashSet<>();
        List<int[][]> out = new ArrayList<>();
        for (int t = 0; t < 8; t++) {
            int[][] cur = new int[5][];
            for (int i = 0; i < 5; i++) {
                int r = base[i][0];
                int c = base[i][1];
                for (int k = 0; k < (t & 3); k++) {
                    int tmp = r;
                    r = c;
                    c = -tmp;
                }
                if (t >= 4) {
                    c = -c;
                }
                cur[i] = new int[] {r, c};
            }
            int[][] norm = normalized(cur);
            if (seen.add(Arrays.deepToString(norm))) {
                out.add(norm);
            }
        }
        return out.toArray(new int[0][][]);
    }

    private static int[][] lots(int h, int w, int[] pieces) {
        List<int[]> lots = new ArrayList<>();
        for (int k = 0; k < pieces.length; k++) {
            for (int[][] o : orientations(pieces[k])) {
                for (int r = 0; r < h; r++) {
                    for (int c = 0; c < w; c++) {
                        int[] lot = new int[6];
                        lot[0] = k;
                        boolean fits = true;
                        for (int i = 0; i < 5 && fits; i++) {
                            int rr = r + o[i][0];
                            int cc = c + o[i][1];
                            fits = rr < h && cc < w;
                            lot[i + 1] = pieces.length + rr * w + cc;
                        }
                        if (fits) {
                            lots.add(lot);
                        }
                    }
                }
            }
        }
        return lots.toArray(new int[0][]);
    }

    private static void checkBoard(int h, int w, int[] pieces) {
        if (h < 1 || w < 1 || h * w != 5 * pieces.length || h * w > 60) {
            throw new IllegalArgumentException("board area must be 5 per piece, at most 60");
        }
        boolean[] used = new boolean[12];
        for (int p : pieces) {
            if (p < 0 || p >= 12 || used[p]) {
                throw new IllegalArgumentException("pieces are distinct 0..11");
            }
            used[p] = true;
        }
    }

    /** Number of tilings of an h x w hull by the given pieces, each used once (up to limit). */
    public static long count(int h, int w, int[] pieces, long limit) {
        checkBoard(h, w, pieces);
        return CoverLots.count(pieces.length + h * w, lots(h, w, pieces), limit);
    }

    /** One tiling as a grid of piece indices (into NAMES), or an empty array. */
    public static int[][] tile(int h, int w, int[] pieces) {
        checkBoard(h, w, pieces);
        int[][] lots = lots(h, w, pieces);
        int[] pick = CoverLots.solve(pieces.length + h * w, lots);
        if (pick.length == 0) {
            return new int[0][];
        }
        int[][] grid = new int[h][w];
        for (int p : pick) {
            for (int i = 1; i < 6; i++) {
                int cell = lots[p][i] - pieces.length;
                grid[cell / w][cell % w] = pieces[lots[p][0]];
            }
        }
        return grid;
    }

    /** Quest q_hull_pieces: how many ways the full set of 12 tiles the given hull. */
    public static boolean quest(int h, int w, long answer) {
        int[] all = new int[12];
        for (int i = 0; i < 12; i++) {
            all[i] = i;
        }
        return count(h, w, all, Long.MAX_VALUE) == answer;
    }
}