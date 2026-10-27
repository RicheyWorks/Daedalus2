// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G406 The Sail Cloths: the sailmaker cuts a canvas up to 6x6 into rectangles (Tatamibari). Each
 * piece holds exactly one clue: {@link #SQUARE} pieces are square, {@link #WIDE} pieces are wider
 * than tall, {@link #TALL} pieces are taller than wide. No four pieces may meet at one point.
 * Clue cells are numbered 0..k-1 in row order; an answer labels every cell with its piece's clue
 * number.
 */
public final class SailCloths {

    public static final String QUEST_ID = "q_sail_cloths";
    public static final int NONE = 0;
    public static final int SQUARE = 1;
    public static final int WIDE = 2;
    public static final int TALL = 3;

    private SailCloths() { }

    /** Clue positions in row order as r * w + c; validates the grid. */
    private static int[] cluePositions(int[][] clues) {
        int h = clues.length;
        if (h < 1 || h > 6) {
            throw new IllegalArgumentException("rows 1..6");
        }
        int w = clues[0].length;
        if (w < 1 || w > 6) {
            throw new IllegalArgumentException("cols 1..6");
        }
        int k = 0;
        for (int[] row : clues) {
            if (row.length != w) {
                throw new IllegalArgumentException("rectangular");
            }
            for (int v : row) {
                if (v < NONE || v > TALL) {
                    throw new IllegalArgumentException("clue NONE..TALL");
                }
                if (v != NONE) {
                    k++;
                }
            }
        }
        int[] pos = new int[k];
        int i = 0;
        for (int x = 0; x < h * w; x++) {
            if (clues[x / w][x % w] != NONE) {
                pos[i++] = x;
            }
        }
        return pos;
    }

    private static boolean shapeOk(int kind, int rows, int cols) {
        return kind == SQUARE ? rows == cols : kind == WIDE ? cols > rows : rows > cols;
    }

    /** True when the labelling cuts the canvas into valid pieces. */
    public static boolean isValid(int[][] clues, int[][] labels) {
        int[] pos = cluePositions(clues);
        int h = clues.length;
        int w = clues[0].length;
        int k = pos.length;
        if (labels.length != h || k == 0) {
            return false;
        }
        int[] top = new int[k];
        int[] left = new int[k];
        int[] bottom = new int[k];
        int[] right = new int[k];
        int[] cells = new int[k];
        Arrays.fill(top, h);
        Arrays.fill(left, w);
        Arrays.fill(bottom, -1);
        Arrays.fill(right, -1);
        for (int r = 0; r < h; r++) {
            if (labels[r].length != w) {
                return false;
            }
            for (int c = 0; c < w; c++) {
                int p = labels[r][c];
                if (p < 0 || p >= k) {
                    return false;
                }
                top[p] = Math.min(top[p], r);
                left[p] = Math.min(left[p], c);
                bottom[p] = Math.max(bottom[p], r);
                right[p] = Math.max(right[p], c);
                cells[p]++;
            }
        }
        for (int p = 0; p < k; p++) {
            int rows = bottom[p] - top[p] + 1;
            int cols = right[p] - left[p] + 1;
            int cr = pos[p] / w;
            int cc = pos[p] % w;
            if (cells[p] != rows * cols || labels[cr][cc] != p
                || !shapeOk(clues[cr][cc], rows, cols)) {
                return false;
            }
        }
        for (int r = 1; r < h; r++) {
            for (int c = 1; c < w; c++) {
                int a = labels[r - 1][c - 1];
                int b = labels[r - 1][c];
                int d = labels[r][c - 1];
                int e = labels[r][c];
                if (a != b && a != d && a != e && b != d && b != e && d != e) {
                    return false;
                }
            }
        }
        return true;
    }

    private static final class Search {
        final int[][] clues;
        final int[] pos;
        final int h;
        final int w;
        final int[][] lab;
        final long limit;
        long count;
        int[][] first = new int[0][];

        Search(int[][] clues, int[] pos, long limit) {
            this.clues = clues;
            this.pos = pos;
            this.h = clues.length;
            this.w = clues[0].length;
            this.lab = new int[h][w];
            for (int[] row : lab) {
                Arrays.fill(row, -1);
            }
            this.limit = limit;
        }

        void run() {
            if (count >= limit) {
                return;
            }
            int x = 0;
            while (x < h * w && lab[x / w][x % w] >= 0) {
                x++;
            }
            if (x == h * w) {
                if (isValid(clues, lab)) {
                    if (count == 0) {
                        first = new int[h][];
                        for (int r = 0; r < h; r++) {
                            first[r] = lab[r].clone();
                        }
                    }
                    count++;
                }
                return;
            }
            int r0 = x / w;
            int c0 = x % w;
            int maxC = w;
            for (int r1 = r0; r1 < h; r1++) {
                for (int c1 = c0; c1 < maxC; c1++) {
                    if (lab[r1][c1] >= 0) {
                        maxC = c1;
                        break;
                    }
                    int found = -1;
                    int many = 0;
                    for (int p = 0; p < pos.length; p++) {
                        int pr = pos[p] / w;
                        int pc = pos[p] % w;
                        if (pr >= r0 && pr <= r1 && pc >= c0 && pc <= c1) {
                            found = p;
                            many++;
                        }
                    }
                    if (many > 1) {
                        maxC = c1;
                        break;
                    }
                    if (many == 1 && shapeOk(clues[pos[found] / w][pos[found] % w],
                        r1 - r0 + 1, c1 - c0 + 1)) {
                        fill(r0, c0, r1, c1, found);
                        run();
                        fill(r0, c0, r1, c1, -1);
                    }
                }
            }
        }

        void fill(int r0, int c0, int r1, int c1, int v) {
            for (int r = r0; r <= r1; r++) {
                for (int c = c0; c <= c1; c++) {
                    lab[r][c] = v;
                }
            }
        }
    }

    /** Number of valid cuttings, stopping at limit. */
    public static long count(int[][] clues, long limit) {
        Search s = new Search(clues, cluePositions(clues), limit);
        s.run();
        return s.count;
    }

    /** First valid cutting, or an empty array when none exists. */
    public static int[][] solve(int[][] clues) {
        Search s = new Search(clues, cluePositions(clues), 1);
        s.run();
        return s.first;
    }

    /** Quest hook: the player's labelling must meet every rule. */
    public static boolean quest(int[][] clues, int[][] answer) {
        return isValid(clues, answer);
    }
}