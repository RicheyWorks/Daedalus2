// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.SplittableRandom;

/**
 * Grate Slide (contest gap G346): the furnace grate is a sliding-tile puzzle with one gap. Say whether it can be
 * restored and in how few slides.
 *
 * <p>The tool is plain: tiles are {@code 1..n-1} in row-major order with {@code 0} as the gap, and the goal puts the
 * gap last. {@link #solvable} is the inversion-parity test (with the blank-row rule for even widths), and
 * {@link #solve} is breadth-first search over packed states for an optimal move string on grates of at most
 * {@link #MAX_SOLVE_CELLS} cells. Moves name where the gap goes: U, D, L, R.
 */
public final class GrateSlide {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_grate_slide";

    /** Largest grate {@link #solve} will search. */
    public static final int MAX_SOLVE_CELLS = 9;

    /** How a restoration went. */
    public enum Grade { RESTORED, JAMMED }

    private GrateSlide() {
    }

    private static void check(int[] tiles, int rows, int cols) {
        if (rows < 1 || cols < 1 || tiles.length != rows * cols || tiles.length > 16) {
            throw new IllegalArgumentException("need rows*cols tiles, at most 16");
        }
        boolean[] seen = new boolean[tiles.length];
        for (int t : tiles) {
            if (t < 0 || t >= tiles.length || seen[t]) {
                throw new IllegalArgumentException("tiles must be a permutation of 0..n-1");
            }
            seen[t] = true;
        }
    }

    /** True if the grate can reach the goal. */
    public static boolean solvable(int[] tiles, int rows, int cols) {
        check(tiles, rows, cols);
        if (rows == 1 || cols == 1) {
            int prev = 0;
            for (int t : tiles) {
                if (t != 0) {
                    if (t < prev) {
                        return false;
                    }
                    prev = t;
                }
            }
            return true;
        }
        int inv = 0;
        int blankRow = 0;
        for (int i = 0; i < tiles.length; i++) {
            if (tiles[i] == 0) {
                blankRow = i / cols;
                continue;
            }
            for (int j = i + 1; j < tiles.length; j++) {
                if (tiles[j] != 0 && tiles[j] < tiles[i]) {
                    inv++;
                }
            }
        }
        if ((cols & 1) == 1) {
            return inv % 2 == 0;
        }
        int fromBottom = rows - blankRow;
        return ((inv + fromBottom) & 1) == 1;
    }

    private static long pack(int[] t) {
        long s = 0;
        for (int i = t.length - 1; i >= 0; i--) {
            s = (s << 4) | t[i];
        }
        return s;
    }

    private static int at(long s, int i) {
        return (int) ((s >>> (4 * i)) & 15);
    }

    private static long swap(long s, int i, int j) {
        long a = at(s, i);
        long b = at(s, j);
        long cleared = s & ~(15L << (4 * i)) & ~(15L << (4 * j));
        return cleared | (a << (4 * j)) | (b << (4 * i));
    }

    private static int gap(long s, int n) {
        for (int i = 0; i < n; i++) {
            if (at(s, i) == 0) {
                return i;
            }
        }
        throw new IllegalStateException("no gap");
    }

    /** The gap's new index after a move, or -1 if the move leaves the grate. */
    private static int step(int g, char m, int rows, int cols) {
        int r = g / cols;
        int c = g % cols;
        return switch (m) {
            case 'U' -> r > 0 ? g - cols : -1;
            case 'D' -> r < rows - 1 ? g + cols : -1;
            case 'L' -> c > 0 ? g - 1 : -1;
            case 'R' -> c < cols - 1 ? g + 1 : -1;
            default -> -1;
        };
    }

    /** The goal grate: 1..n-1 then the gap. */
    public static int[] goal(int rows, int cols) {
        int[] g = new int[rows * cols];
        for (int i = 0; i < g.length - 1; i++) {
            g[i] = i + 1;
        }
        return g;
    }

    /** An optimal move string, or empty if the grate cannot be restored. */
    public static Optional<String> solve(int[] tiles, int rows, int cols) {
        check(tiles, rows, cols);
        if (tiles.length > MAX_SOLVE_CELLS) {
            throw new IllegalArgumentException("grate too large to search: " + tiles.length);
        }
        if (!solvable(tiles, rows, cols)) {
            return Optional.empty();
        }
        int n = tiles.length;
        long start = pack(tiles);
        long target = pack(goal(rows, cols));
        Map<Long, Long> parent = new HashMap<>();
        Map<Long, Character> via = new HashMap<>();
        long[] queue = new long[16];
        int head = 0;
        int tail = 0;
        parent.put(start, start);
        queue[tail++] = start;
        String moves = "UDLR";
        while (head < tail) {
            long s = queue[head++];
            if (s == target) {
                break;
            }
            int g = gap(s, n);
            for (int k = 0; k < 4; k++) {
                int to = step(g, moves.charAt(k), rows, cols);
                if (to >= 0) {
                    long t = swap(s, g, to);
                    if (!parent.containsKey(t)) {
                        parent.put(t, s);
                        via.put(t, moves.charAt(k));
                        if (tail == queue.length) {
                            queue = Arrays.copyOf(queue, tail * 2);
                        }
                        queue[tail++] = t;
                    }
                }
            }
        }
        StringBuilder sb = new StringBuilder();
        long cur = target;
        while (cur != start) {
            sb.append(via.get(cur).charValue());
            cur = parent.get(cur);
        }
        return Optional.of(sb.reverse().toString());
    }

    /** Apply moves; empty if any move leaves the grate. */
    public static Optional<int[]> apply(int[] tiles, int rows, int cols, String moves) {
        check(tiles, rows, cols);
        long s = pack(tiles);
        int g = gap(s, tiles.length);
        for (int i = 0; i < moves.length(); i++) {
            int to = step(g, moves.charAt(i), rows, cols);
            if (to < 0) {
                return Optional.empty();
            }
            s = swap(s, g, to);
            g = to;
        }
        int[] out = new int[tiles.length];
        for (int i = 0; i < out.length; i++) {
            out[i] = at(s, i);
        }
        return Optional.of(out);
    }

    /** A seeded grate made by {@code walk} random slides from the goal (always solvable). */
    public static int[] scramble(long seed, int rows, int cols, int walk) {
        int[] t = goal(rows, cols);
        SplittableRandom r = new SplittableRandom(seed);
        StringBuilder sb = new StringBuilder();
        int g = t.length - 1;
        while (sb.length() < walk) {
            char m = "UDLR".charAt(r.nextInt(4));
            int to = step(g, m, rows, cols);
            if (to >= 0) {
                sb.append(m);
                g = to;
            }
        }
        return apply(t, rows, cols, sb.toString()).orElseThrow();
    }

    /** RESTORED only if the moves are valid, reach the goal, and are as short as possible. */
    public static Grade grade(int[] tiles, int rows, int cols, String moves) {
        Optional<int[]> end = apply(tiles, rows, cols, moves);
        Optional<String> best = solve(tiles, rows, cols);
        boolean ok = end.isPresent() && Arrays.equals(end.get(), goal(rows, cols))
                && best.isPresent() && best.get().length() == moves.length();
        return ok ? Grade.RESTORED : Grade.JAMMED;
    }

    /** The Forgemaster's line for a restoration. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case RESTORED -> "Forgemaster: the grate falls into place, not one wasted shove. The fire breathes.";
            case JAMMED -> "Forgemaster: the grate is still jammed, or you shoved it the long way round.";
        };
    }
}
