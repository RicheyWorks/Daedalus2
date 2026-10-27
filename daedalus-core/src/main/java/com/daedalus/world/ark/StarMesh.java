// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.math.BigInteger;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * G441 The Star Mesh: the navigator joins fixed stars (integer points) into the Delaunay mesh,
 * the triangulation where no star lies inside any triangle's circumcircle. Points are inserted in
 * x order, each joined to the hull edges it sees, then edges are flipped (Lawson) until every
 * edge is locally Delaunay. Orientation uses long arithmetic and the in-circle test BigInteger,
 * so results are exact. Requires no three points collinear and no four cocircular.
 */
public final class StarMesh {

    public static final String QUEST_ID = "q_star_mesh";
    public static final int MAX_POINTS = 400;
    public static final long MAX_COORD = 1_000_000;

    private StarMesh() { }

    private static long orient(long[] a, long[] b, long[] c) {
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    }

    /** Positive when d lies inside the circumcircle of counter-clockwise a, b, c. */
    public static int inCircle(long[] a, long[] b, long[] c, long[] d) {
        BigInteger[] r = new BigInteger[9];
        long[][] p = {a, b, c};
        for (int i = 0; i < 3; i++) {
            BigInteger dx = BigInteger.valueOf(p[i][0] - d[0]);
            BigInteger dy = BigInteger.valueOf(p[i][1] - d[1]);
            r[3 * i] = dx;
            r[3 * i + 1] = dy;
            r[3 * i + 2] = dx.multiply(dx).add(dy.multiply(dy));
        }
        BigInteger det = r[0].multiply(r[4].multiply(r[8]).subtract(r[5].multiply(r[7])))
                .subtract(r[1].multiply(r[3].multiply(r[8]).subtract(r[5].multiply(r[6]))))
                .add(r[2].multiply(r[3].multiply(r[7]).subtract(r[4].multiply(r[6]))));
        return det.signum();
    }

    private static void check(long[][] pts) {
        if (pts == null || pts.length < 3 || pts.length > MAX_POINTS) {
            throw new IllegalArgumentException("need 3 to " + MAX_POINTS + " points");
        }
        for (long[] p : pts) {
            if (p == null || p.length != 2 || Math.abs(p[0]) > MAX_COORD || Math.abs(p[1]) > MAX_COORD) {
                throw new IllegalArgumentException("points are {x, y} within 10^6");
            }
        }
        for (int i = 0; i < pts.length; i++) {
            for (int j = i + 1; j < pts.length; j++) {
                if (pts[i][0] == pts[j][0] && pts[i][1] == pts[j][1]) {
                    throw new IllegalArgumentException("duplicate point");
                }
                for (int k = j + 1; k < pts.length; k++) {
                    if (orient(pts[i], pts[j], pts[k]) == 0) {
                        throw new IllegalArgumentException("three points collinear");
                    }
                }
            }
        }
    }

    private static long key(int a, int b) {
        return (long) a << 32 | b;
    }

    /** Delaunay triangles as counter-clockwise index triples into the input array. */
    public static int[][] triangulate(long[][] pts) {
        check(pts);
        int n = pts.length;
        Integer[] order = new Integer[n];
        for (int i = 0; i < n; i++) {
            order[i] = i;
        }
        Arrays.sort(order, Comparator.<Integer>comparingLong(i -> pts[i][0]).thenComparingLong(i -> pts[i][1]));
        List<int[]> tris = new ArrayList<>();
        Map<Long, Integer> edge = new HashMap<>();
        int a = order[0];
        int b = order[1];
        int c = order[2];
        if (orient(pts[a], pts[b], pts[c]) < 0) {
            int t = b;
            b = c;
            c = t;
        }
        add(tris, edge, a, b, c);
        List<Integer> hull = new ArrayList<>(List.of(a, b, c));
        ArrayDeque<long[]> stack = new ArrayDeque<>();
        for (int s = 3; s < n; s++) {
            int p = order[s];
            int h = hull.size();
            boolean[] vis = new boolean[h];
            for (int i = 0; i < h; i++) {
                vis[i] = orient(pts[hull.get(i)], pts[hull.get((i + 1) % h)], pts[p]) < 0;
            }
            int start = 0;
            while (!(vis[start] && !vis[(start + h - 1) % h])) {
                start++;
            }
            List<Integer> nh = new ArrayList<>();
            int i = start;
            nh.add(hull.get(i));
            while (vis[i]) {
                int u = hull.get(i);
                int v = hull.get((i + 1) % h);
                add(tris, edge, v, u, p);
                stack.push(new long[] {u, v});
                i = (i + 1) % h;
            }
            nh.add(p);
            for (int j = i; j != start; j = (j + 1) % h) {
                nh.add(hull.get(j));
            }
            hull = nh;
            while (!stack.isEmpty()) {
                long[] e = stack.pop();
                legalize(pts, tris, edge, (int) e[0], (int) e[1], stack);
            }
        }
        List<int[]> out = new ArrayList<>();
        for (int[] t : tris) {
            if (t[0] >= 0) {
                out.add(t.clone());
            }
        }
        return out.toArray(new int[0][]);
    }

    private static void add(List<int[]> tris, Map<Long, Integer> edge, int a, int b, int c) {
        int id = tris.size();
        tris.add(new int[] {a, b, c});
        edge.put(key(a, b), id);
        edge.put(key(b, c), id);
        edge.put(key(c, a), id);
    }

    private static int third(int[] t, int u, int v) {
        for (int x : t) {
            if (x != u && x != v) {
                return x;
            }
        }
        throw new IllegalStateException("degenerate triangle");
    }

    private static void legalize(long[][] pts, List<int[]> tris, Map<Long, Integer> edge, int u, int v,
            ArrayDeque<long[]> stack) {
        Integer t1 = edge.get(key(u, v));
        Integer t2 = edge.get(key(v, u));
        if (t1 == null || t2 == null) {
            return;
        }
        int c = third(tris.get(t1), u, v);
        int d = third(tris.get(t2), u, v);
        if (inCircle(pts[u], pts[v], pts[c], pts[d]) <= 0) {
            return;
        }
        for (int id : new int[] {t1, t2}) {
            int[] t = tris.get(id);
            for (int k = 0; k < 3; k++) {
                edge.remove(key(t[k], t[(k + 1) % 3]));
            }
            t[0] = -1;
        }
        add(tris, edge, u, d, c);
        add(tris, edge, d, v, c);
        stack.push(new long[] {u, d});
        stack.push(new long[] {d, v});
        stack.push(new long[] {v, c});
        stack.push(new long[] {c, u});
    }

    /** True when no point lies strictly inside any triangle's circumcircle. */
    public static boolean emptyCircles(long[][] pts, int[][] tris) {
        for (int[] t : tris) {
            for (int i = 0; i < pts.length; i++) {
                if (i != t[0] && i != t[1] && i != t[2] && inCircle(pts[t[0]], pts[t[1]], pts[t[2]], pts[i]) > 0) {
                    return false;
                }
            }
        }
        return true;
    }

    /** Quest q_star_mesh: the navigator names how many triangles the star mesh has. */
    public static boolean quest(long[][] pts, int answer) {
        return triangulate(pts).length == answer;
    }
}