// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;
import java.util.TreeSet;

/**
 * Rune Trace (contest gap G356): a grid of runes is cut into the anvil face. The apprentice traces a word by stepping
 * to any of the eight neighbours without reusing a cell. Find every listed word that can be traced.
 *
 * <p>The tool is plain: {@link #findWords} builds a trie over the words (lowercase a-z) and runs a DFS from every cell
 * that follows only trie edges, marking visited cells and removing found words so they are not searched again. Any
 * project can use it for Boggle-style word grids.
 */
public final class RuneTrace {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_rune_trace";

    /** Runes used for seeded grids and words. */
    public static final String RUNES = "fuxae";

    /** How a tracing went. */
    public enum Grade { TRACED, SMUDGED }

    private RuneTrace() {
    }

    /** A seeded rows x cols grid. */
    public static char[][] grid(long seed, int rows, int cols) {
        if (rows < 1 || cols < 1) {
            throw new IllegalArgumentException("need rows, cols >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        char[][] g = new char[rows][cols];
        for (char[] row : g) {
            for (int j = 0; j < cols; j++) {
                row[j] = RUNES.charAt(r.nextInt(RUNES.length()));
            }
        }
        return g;
    }

    /** {@code n} seeded words of length 1..maxLen. */
    public static List<String> words(long seed, int n, int maxLen) {
        if (n < 0 || maxLen < 1) {
            throw new IllegalArgumentException("need n >= 0 and maxLen >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        List<String> out = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            int len = 1 + r.nextInt(maxLen);
            StringBuilder sb = new StringBuilder(len);
            for (int k = 0; k < len; k++) {
                sb.append(RUNES.charAt(r.nextInt(RUNES.length())));
            }
            out.add(sb.toString());
        }
        return out;
    }

    /** Every listed word that can be traced, sorted and without duplicates. */
    public static List<String> findWords(char[][] grid, List<String> words) {
        int[][] next = new int[1][26];
        String[] end = new String[1];
        int nodes = 1;
        for (String w : words) {
            if (w.isEmpty()) {
                throw new IllegalArgumentException("words must be non-empty");
            }
            int v = 0;
            for (int i = 0; i < w.length(); i++) {
                int c = w.charAt(i) - 'a';
                if (c < 0 || c >= 26) {
                    throw new IllegalArgumentException("words must be lowercase a-z: " + w);
                }
                if (next[v][c] == 0) {
                    if (nodes == next.length) {
                        next = Arrays.copyOf(next, nodes * 2);
                        end = Arrays.copyOf(end, nodes * 2);
                    }
                    next[nodes] = new int[26];
                    next[v][c] = nodes++;
                }
                v = next[v][c];
            }
            end[v] = w;
        }
        TreeSet<String> found = new TreeSet<>();
        int rows = grid.length;
        boolean[][] seen = new boolean[rows][];
        for (int i = 0; i < rows; i++) {
            seen[i] = new boolean[grid[i].length];
        }
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < grid[i].length; j++) {
                dfs(grid, seen, next, end, 0, i, j, found);
            }
        }
        return new ArrayList<>(found);
    }

    private static void dfs(char[][] g, boolean[][] seen, int[][] next, String[] end, int v, int i, int j,
            TreeSet<String> found) {
        int c = g[i][j] - 'a';
        if (c < 0 || c >= 26 || seen[i][j] || next[v][c] == 0) {
            return;
        }
        int u = next[v][c];
        if (end[u] != null) {
            found.add(end[u]);
            end[u] = null;
        }
        seen[i][j] = true;
        for (int di = -1; di <= 1; di++) {
            for (int dj = -1; dj <= 1; dj++) {
                int a = i + di;
                int b = j + dj;
                if ((di != 0 || dj != 0) && a >= 0 && a < g.length && b >= 0 && b < g[a].length) {
                    dfs(g, seen, next, end, u, a, b, found);
                }
            }
        }
        seen[i][j] = false;
    }

    /** TRACED only if the claimed set (any order, duplicates ignored) is exactly right. */
    public static Grade grade(char[][] grid, List<String> words, List<String> claimed) {
        return new TreeSet<>(claimed).equals(new TreeSet<>(findWords(grid, words))) ? Grade.TRACED : Grade.SMUDGED;
    }

    /** The Forgemaster's line for a tracing. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TRACED -> "Forgemaster: every word on that anvil, found and none invented. Sharp eyes.";
            case SMUDGED -> "Forgemaster: you missed a word or dreamed one up. Trace the runes again.";
        };
    }
}
