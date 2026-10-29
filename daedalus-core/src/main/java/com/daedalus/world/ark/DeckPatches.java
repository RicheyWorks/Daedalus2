// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/**
 * G347 The Deck Patches: the carpenter cuts deck patches made of n unit squares joined edge to
 * edge (polyominoes). Patches are grown one cell at a time from every smaller patch and kept in a
 * canonical form, so the same patch is counted once whether it is slid (fixed count) or also turned
 * and flipped (free count).
 */
public final class DeckPatches {

    public static final String QUEST_ID = "q_deck_patches";

    private static final int MAX = 10;

    private DeckPatches() { }

    private static long[] normalize(long[] cells) {
        long minX = Long.MAX_VALUE;
        long minY = Long.MAX_VALUE;
        for (long c : cells) {
            minX = Math.min(minX, c >> 16);
            minY = Math.min(minY, c & 0xFFFF);
        }
        long[] out = new long[cells.length];
        for (int i = 0; i < cells.length; i++) {
            out[i] = (((cells[i] >> 16) - minX) << 16) | ((cells[i] & 0xFFFF) - minY);
        }
        Arrays.sort(out);
        return out;
    }

    private static long pack(int x, int y) {
        return ((long) (x + 100) << 16) | (y + 100);
    }

    private static long[] transform(long[] cells, int t) {
        long[] out = new long[cells.length];
        for (int i = 0; i < cells.length; i++) {
            int x = (int) (cells[i] >> 16);
            int y = (int) (cells[i] & 0xFFFF);
            int nx;
            int ny;
            switch (t & 3) {
                case 0:
                    nx = x;
                    ny = y;
                    break;
                case 1:
                    nx = -y;
                    ny = x;
                    break;
                case 2:
                    nx = -x;
                    ny = -y;
                    break;
                default:
                    nx = y;
                    ny = -x;
                    break;
            }
            if (t >= 4) {
                nx = -nx;
            }
            out[i] = pack(nx, ny);
        }
        return normalize(out);
    }

    private static String key(long[] cells) {
        return Arrays.toString(cells);
    }

    private static String freeKey(long[] cells) {
        String best = null;
        for (int t = 0; t < 8; t++) {
            String k = key(transform(cells, t));
            if (best == null || k.compareTo(best) < 0) {
                best = k;
            }
        }
        return best;
    }

    private static Set<String> fixedShapes(int n) {
        Set<String> cur = new HashSet<>();
        cur.add(key(new long[] {0L}));
        for (int size = 1; size < n; size++) {
            Set<String> next = new HashSet<>();
            for (String s : cur) {
                long[] cells = parse(s);
                Set<Long> have = new HashSet<>();
                for (long c : cells) {
                    have.add(c);
                }
                for (long c : cells) {
                    int x = (int) (c >> 16);
                    int y = (int) (c & 0xFFFF);
                    int[][] nb = {{x + 1, y}, {x - 1, y}, {x, y + 1}, {x, y - 1}};
                    for (int[] p : nb) {
                        if (p[0] >= 0 && p[1] >= 0 && have.contains(((long) p[0] << 16) | p[1])) {
                            continue;
                        }
                        long[] grown = new long[cells.length + 1];
                        for (int i = 0; i < cells.length; i++) {
                            grown[i] = pack((int) (cells[i] >> 16), (int) (cells[i] & 0xFFFF));
                        }
                        grown[cells.length] = pack(p[0], p[1]);
                        next.add(key(normalize(grown)));
                    }
                }
            }
            cur = next;
        }
        return cur;
    }

    private static long[] parse(String s) {
        String body = s.substring(1, s.length() - 1);
        String[] parts = body.split(", ");
        long[] out = new long[parts.length];
        for (int i = 0; i < parts.length; i++) {
            out[i] = Long.parseLong(parts[i]);
        }
        return out;
    }

    private static void checkN(int n) {
        if (n < 1 || n > MAX) {
            throw new IllegalArgumentException("patch size 1.." + MAX + ": " + n);
        }
    }

    /** Patches of n cells counted up to sliding only. */
    public static long fixedCount(int n) {
        checkN(n);
        return fixedShapes(n).size();
    }

    /** Patches of n cells counted up to sliding, turning and flipping. */
    public static long freeCount(int n) {
        checkN(n);
        Set<String> free = new HashSet<>();
        for (String s : fixedShapes(n)) {
            free.add(freeKey(parse(s)));
        }
        return free.size();
    }

    /** True when the cells (x, y pairs, 0..999) are distinct and edge-connected. */
    public static boolean isPatch(int[][] cells) {
        if (cells.length == 0) {
            return false;
        }
        Set<Long> all = new HashSet<>();
        for (int[] c : cells) {
            if (c.length != 2 || c[0] < 0 || c[1] < 0 || c[0] > 999 || c[1] > 999 || !all.add(pack(c[0], c[1]))) {
                return false;
            }
        }
        Set<Long> seen = new HashSet<>();
        ArrayDeque<int[]> q = new ArrayDeque<>();
        q.add(cells[0]);
        seen.add(pack(cells[0][0], cells[0][1]));
        while (!q.isEmpty()) {
            int[] c = q.poll();
            int[][] nb = {{c[0] + 1, c[1]}, {c[0] - 1, c[1]}, {c[0], c[1] + 1}, {c[0], c[1] - 1}};
            for (int[] p : nb) {
                long k = pack(p[0], p[1]);
                if (all.contains(k) && seen.add(k)) {
                    q.add(p);
                }
            }
        }
        return seen.size() == cells.length;
    }

    /** Quest q_deck_patches: say how many free patches have n cells. */
    public static boolean quest(int n, long answer) {
        return freeCount(n) == answer;
    }
}