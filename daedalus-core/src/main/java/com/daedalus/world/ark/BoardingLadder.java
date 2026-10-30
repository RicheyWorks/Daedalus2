// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

/**
 * G423 The Boarding Ladder: boarders stand on the deck at rows y &lt;= 0 of an unbounded grid
 * (Conway's Soldiers). A jump takes a boarder over an orthogonal neighbour into the empty cell
 * beyond, and the jumped boarder leaves. Gives the fewest boarders that can put one boarder on
 * (0, k) for k = 0 to {@link #MAX_ROW}, found by searching jumps backwards from the target, one
 * such starting layout with its jumps, a jump checker and the golden-ratio pagoda weight, which no
 * jump can raise.
 */
public final class BoardingLadder {

    public static final String QUEST_ID = "q_boarding_ladder";
    public static final int MAX_ROW = 3;
    private static final int[][] DIRS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
    private static final double SIGMA = (Math.sqrt(5) - 1) / 2;

    private BoardingLadder() { }

    private static long pack(int x, int y) {
        return ((long) (x + 1000) << 20) | (y + 1000);
    }

    private static int px(long p) {
        return (int) (p >> 20) - 1000;
    }

    private static int py(long p) {
        return (int) (p & 0xFFFFF) - 1000;
    }

    private static void row(int k) {
        if (k < 0 || k > MAX_ROW) {
            throw new IllegalArgumentException("row must be 0 to " + MAX_ROW);
        }
    }

    /** Reverse jumps found by the search, newest last, as {x, y, dx, dy} of the forward jump. */
    private static List<int[]> search(int k) {
        row(k);
        for (int moves = 0;; moves++) {
            TreeSet<Long> pegs = new TreeSet<>();
            pegs.add(pack(0, k));
            List<int[]> path = new ArrayList<>();
            if (dfs(pegs, moves, path, new HashSet<>())) {
                return path;
            }
        }
    }

    private static boolean dfs(TreeSet<Long> pegs, int left, List<int[]> path, Set<String> dead) {
        int above = 0;
        for (long p : pegs) {
            above += py(p) > 0 ? 1 : 0;
        }
        if (above == 0) {
            return true;
        }
        if (above > left) {
            return false;
        }
        String key = left + pegs.toString();
        if (dead.contains(key)) {
            return false;
        }
        for (long p : new ArrayList<>(pegs)) {
            int x = px(p);
            int y = py(p);
            for (int[] d : DIRS) {
                long b = pack(x - d[0], y - d[1]);
                long a = pack(x - 2 * d[0], y - 2 * d[1]);
                if (pegs.contains(a) || pegs.contains(b)) {
                    continue;
                }
                pegs.remove(p);
                pegs.add(a);
                pegs.add(b);
                path.add(new int[] {x - 2 * d[0], y - 2 * d[1], d[0], d[1]});
                if (dfs(pegs, left - 1, path, dead)) {
                    return true;
                }
                path.remove(path.size() - 1);
                pegs.remove(a);
                pegs.remove(b);
                pegs.add(p);
            }
        }
        dead.add(key);
        return false;
    }

    /** Fewest boarders on or below the line that can reach (0, k). */
    public static int fewest(int k) {
        return search(k).size() + 1;
    }

    /** Forward jumps {x, y, dx, dy} for the layout from {@link #layout(int)}. */
    public static int[][] jumps(int k) {
        List<int[]> rev = search(k);
        int[][] out = new int[rev.size()][];
        for (int i = 0; i < out.length; i++) {
            out[i] = rev.get(rev.size() - 1 - i).clone();
        }
        return out;
    }

    /** A starting layout {x, y} of {@link #fewest(int)} boarders, all with y &lt;= 0. */
    public static int[][] layout(int k) {
        TreeSet<Long> pegs = new TreeSet<>();
        pegs.add(pack(0, k));
        for (int[] j : search(k)) {
            pegs.add(pack(j[0], j[1]));
            pegs.add(pack(j[0] + j[2], j[1] + j[3]));
            pegs.remove(pack(j[0] + 2 * j[2], j[1] + 2 * j[3]));
        }
        int[][] out = new int[pegs.size()][];
        int i = 0;
        for (long p : pegs) {
            out[i++] = new int[] {px(p), py(p)};
        }
        return out;
    }

    /** Plays the jumps from the layout; returns the cells left, or an empty array if one is illegal. */
    public static int[][] play(int[][] start, int[][] moves) {
        Set<Long> pegs = new HashSet<>();
        for (int[] s : start) {
            pegs.add(pack(s[0], s[1]));
        }
        for (int[] j : moves) {
            if (j == null || j.length != 4 || Math.abs(j[2]) + Math.abs(j[3]) != 1) {
                return new int[0][];
            }
            long a = pack(j[0], j[1]);
            long b = pack(j[0] + j[2], j[1] + j[3]);
            long c = pack(j[0] + 2 * j[2], j[1] + 2 * j[3]);
            if (!pegs.contains(a) || !pegs.contains(b) || pegs.contains(c)) {
                return new int[0][];
            }
            pegs.remove(a);
            pegs.remove(b);
            pegs.add(c);
        }
        int[][] out = new int[pegs.size()][];
        int i = 0;
        for (long p : new TreeSet<>(pegs)) {
            out[i++] = new int[] {px(p), py(p)};
        }
        return out;
    }

    /** Pagoda weight toward (0, k): the sum of sigma^(|x| + |k - y|), sigma = (sqrt 5 - 1) / 2. */
    public static double pagoda(int[][] pegs, int k) {
        double s = 0;
        for (int[] p : pegs) {
            s += Math.pow(SIGMA, Math.abs(p[0]) + Math.abs(k - p[1]));
        }
        return s;
    }

    /** Quest q_boarding_ladder: the bosun names the fewest boarders needed to reach row k. */
    public static boolean quest(int k, int answer) {
        return fewest(k) == answer;
    }
}