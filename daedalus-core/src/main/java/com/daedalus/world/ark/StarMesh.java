// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;

/**
 * G441 The Star Mesh: the navigator joins fixed stars (integer points) into the Delaunay mesh,
 * the triangulation where no star lies inside any triangle's circumcircle. Points are inserted in
 * x order, each joined to the hull edges it sees, then edges are flipped (Lawson) until every
 * edge is locally Delaunay. Orientation uses long arithmetic and the in-circle test exact 128-bit
 * sums, so results are exact. Requires no three points collinear; with four cocircular stars either diagonal is
 * Delaunay and the insertion order picks one.
 *
 * <p>API, mirrored one for one by DaedalusArkStarMeshCore.h:
 * <ul>
 *   <li>{@link #problem}: why a sky is refused (few, many, range, duplicate, collinear), or null;</li>
 *   <li>{@link #build}: triangles, counter-clockwise hull and Lawson flip count; {@link #triangulate}: triangles;</li>
 *   <li>{@link #neighbours}, {@link #edges}: adjacency, and each edge once (3n - 3 - hull of them);</li>
 *   <li>{@link #chartLines}: the Euclidean minimum spanning tree over the mesh edges;</li>
 *   <li>{@link #locate}, {@link #nearest}: the triangle under a point, the nearest star by a greedy walk;</li>
 *   <li>{@link #inCircle}, {@link #emptyCircles}: the exact predicate and the Delaunay check.</li>
 * </ul>
 */
public final class StarMesh {

    public static final String QUEST_ID = "q_star_mesh";
    public static final int MAX_POINTS = 400;
    public static final long MAX_COORD = 1_000_000;

    private StarMesh() { }

    private static long orient(long[] a, long[] b, long[] c) {
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    }

    /**
     * Positive when d lies inside the circumcircle of counter-clockwise a, b, c, zero on it, negative outside. Exact
     * for coordinates within 10^6: the determinant is six products (dx_i * dy_j) * sq_k, each under 2^107, summed in
     * 128 bits (Math.multiplyHigh), the same expansion as StarInCircle in DaedalusArkStarMeshCore.h. No BigInteger.
     */
    public static int inCircle(long[] a, long[] b, long[] c, long[] d) {
        long[][] p = {a, b, c};
        long[] dx = new long[3];
        long[] dy = new long[3];
        long[] sq = new long[3];
        for (int i = 0; i < 3; i++) {
            dx[i] = p[i][0] - d[0];
            dy[i] = p[i][1] - d[1];
            sq[i] = dx[i] * dx[i] + dy[i] * dy[i];
        }
        long[] sum = new long[2];
        add(sum, dx[0] * dy[1], sq[2], 1);
        add(sum, dx[0] * dy[2], sq[1], -1);
        add(sum, dx[1] * dy[0], sq[2], -1);
        add(sum, dx[1] * dy[2], sq[0], 1);
        add(sum, dx[2] * dy[0], sq[1], 1);
        add(sum, dx[2] * dy[1], sq[0], -1);
        return sum[1] < 0 ? -1 : (sum[0] | sum[1]) != 0 ? 1 : 0;
    }

    /** sum (hi:lo, two's complement) += sign * x * y, with x * y taken exactly in 128 bits. */
    private static void add(long[] sum, long x, long y, int sign) {
        long lo = x * y;
        long hi = Math.multiplyHigh(x, y);
        if (sign < 0) {
            lo = -lo;
            hi = ~hi + (lo == 0 ? 1 : 0);
        }
        long nlo = sum[0] + lo;
        sum[1] += hi + (Long.compareUnsigned(nlo, sum[0]) < 0 ? 1 : 0);
        sum[0] = nlo;
    }

    /**
     * Why a sky cannot be meshed, or null when it can: "few" (under 3 stars), "many" (over MAX_POINTS),
     * "range" (a star that is not {x, y} within 10^6), "duplicate" or "collinear" (three stars on one line).
     * Checked in that order; the same names as StarMeshProblemName in DaedalusArkStarMeshCore.h.
     */
    public static String problem(long[][] pts) {
        if (pts == null || pts.length < 3) {
            return "few";
        }
        if (pts.length > MAX_POINTS) {
            return "many";
        }
        for (long[] p : pts) {
            if (p == null || p.length != 2 || Math.abs(p[0]) > MAX_COORD || Math.abs(p[1]) > MAX_COORD) {
                return "range";
            }
        }
        for (int i = 0; i < pts.length; i++) {
            for (int j = i + 1; j < pts.length; j++) {
                if (pts[i][0] == pts[j][0] && pts[i][1] == pts[j][1]) {
                    return "duplicate";
                }
            }
        }
        for (int i = 0; i < pts.length; i++) {
            for (int j = i + 1; j < pts.length; j++) {
                for (int k = j + 1; k < pts.length; k++) {
                    if (orient(pts[i], pts[j], pts[k]) == 0) {
                        return "collinear";
                    }
                }
            }
        }
        return null;
    }

    private static void check(long[][] pts) {
        String why = problem(pts);
        if (why != null) {
            throw new IllegalArgumentException("star mesh refused: " + why);
        }
    }

    /**
     * A built mesh: counter-clockwise triangles (the order of {@link #triangulate}), the hull counter-clockwise
     * from the lowest-x (then lowest-y) star, and the number of Lawson flips the build made.
     */
    public record Mesh(int[][] triangles, int[] hull, int flips) {

        /** Copies in, so a mesh never shares arrays with its builder. */
        public Mesh {
            triangles = copy(triangles);
            hull = hull.clone();
        }

        /** A copy of the triangles; changing it does not change the mesh. */
        @Override
        public int[][] triangles() {
            return copy(triangles);
        }

        /** A copy of the hull; changing it does not change the mesh. */
        @Override
        public int[] hull() {
            return hull.clone();
        }

        private static int[][] copy(int[][] rows) {
            int[][] out = new int[rows.length][];
            for (int i = 0; i < rows.length; i++) {
                out[i] = rows[i].clone();
            }
            return out;
        }
    }

    private static long key(int a, int b) {
        return (long) a << 32 | b;
    }

    /** Delaunay triangles as counter-clockwise index triples into the input array. */
    public static int[][] triangulate(long[][] pts) {
        return build(pts).triangles();
    }

    /** Builds the Delaunay mesh; throws IllegalArgumentException naming the {@link #problem} for a bad sky. */
    public static Mesh build(long[][] pts) {
        check(pts);
        int n = pts.length;
        Integer[] order = new Integer[n];
        for (int i = 0; i < n; i++) {
            order[i] = i;
        }
        Arrays.sort(order, Comparator.<Integer>comparingLong(i -> pts[i][0]).thenComparingLong(i -> pts[i][1]));
        // Presized for a typical build (about 2n live triangles plus two per flip, 3 directed edges per live one).
        List<int[]> tris = new ArrayList<>(4 * n);
        Map<Long, Integer> edge = new HashMap<>(8 * n);
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
        int flips = 0;
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
                flips += legalize(pts, tris, edge, (int) e[0], (int) e[1], stack);
            }
        }
        List<int[]> out = new ArrayList<>();
        for (int[] t : tris) {
            if (t[0] >= 0) {
                out.add(t.clone());
            }
        }
        int[] ring = new int[hull.size()];
        int first = hull.indexOf(order[0]);
        for (int k = 0; k < ring.length; k++) {
            ring[k] = hull.get((first + k) % ring.length);
        }
        return new Mesh(out.toArray(new int[0][]), ring, flips);
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

    /** Returns 1 when the edge u-v was flipped, else 0. */
    private static int legalize(long[][] pts, List<int[]> tris, Map<Long, Integer> edge, int u, int v,
            ArrayDeque<long[]> stack) {
        Integer t1 = edge.get(key(u, v));
        Integer t2 = edge.get(key(v, u));
        if (t1 == null || t2 == null) {
            return 0;
        }
        int c = third(tris.get(t1), u, v);
        int d = third(tris.get(t2), u, v);
        if (inCircle(pts[u], pts[v], pts[c], pts[d]) <= 0) {
            return 0;
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
        return 1;
    }

    /** Each star's mesh neighbours, ascending. */
    public static int[][] neighbours(int n, int[][] tris) {
        List<TreeSet<Integer>> sets = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            sets.add(new TreeSet<>());
        }
        for (int[] t : tris) {
            for (int k = 0; k < 3; k++) {
                sets.get(t[k]).add(t[(k + 1) % 3]);
                sets.get(t[(k + 1) % 3]).add(t[k]);
            }
        }
        int[][] out = new int[n][];
        for (int i = 0; i < n; i++) {
            out[i] = sets.get(i).stream().mapToInt(Integer::intValue).toArray();
        }
        return out;
    }

    /** Every mesh edge once, as {a, b} with a < b, sorted by a then b. There are 3n - 3 - hull of them. */
    public static int[][] edges(int n, int[][] tris) {
        int[][] nb = neighbours(n, tris);
        List<int[]> out = new ArrayList<>();
        for (int a = 0; a < n; a++) {
            for (int b : nb[a]) {
                if (a < b) {
                    out.add(new int[] {a, b});
                }
            }
        }
        return out.toArray(new int[0][]);
    }

    private static long squaredLength(long[][] pts, int[] e) {
        long dx = pts[e[0]][0] - pts[e[1]][0];
        long dy = pts[e[0]][1] - pts[e[1]][1];
        return dx * dx + dy * dy;
    }

    /**
     * The navigator's chart lines: the Euclidean minimum spanning tree, taken from the mesh edges (it always lies
     * inside the Delaunay mesh). Kruskal over edges ordered by exact squared length, then a, then b; n - 1 edges.
     */
    public static int[][] chartLines(long[][] pts, int[][] tris) {
        int n = pts.length;
        int[][] all = edges(n, tris);
        Arrays.sort(all, Comparator.<int[]>comparingLong(e -> squaredLength(pts, e))
                .thenComparingInt(e -> e[0]).thenComparingInt(e -> e[1]));
        int[] parent = new int[n];
        for (int i = 0; i < n; i++) {
            parent[i] = i;
        }
        List<int[]> out = new ArrayList<>();
        for (int[] e : all) {
            int ra = root(parent, e[0]);
            int rb = root(parent, e[1]);
            if (ra != rb) {
                parent[ra] = rb;
                out.add(e);
            }
        }
        return out.toArray(new int[0][]);
    }

    private static int root(int[] parent, int x) {
        while (parent[x] != x) {
            parent[x] = parent[parent[x]];
            x = parent[x];
        }
        return x;
    }

    /**
     * The star nearest q, by a greedy walk over mesh edges from star 0: step to the neighbour closest to q (ties to
     * the lower index) while it is strictly closer. On a Delaunay mesh the walk always ends at a nearest star.
     */
    public static int nearest(long[][] pts, int[][] tris, long[] q) {
        int[][] nb = neighbours(pts.length, tris);
        int at = 0;
        while (true) {
            int best = at;
            for (int v : nb[at]) {
                if (dist2(pts[v], q) < dist2(pts[best], q)) {
                    best = v; // neighbours ascend, so ties keep the lower index
                }
            }
            if (best == at) {
                return at;
            }
            at = best;
        }
    }

    private static long dist2(long[] p, long[] q) {
        long dx = p[0] - q[0];
        long dy = p[1] - q[1];
        return dx * dx + dy * dy;
    }

    /**
     * The first triangle (in mesh order) that holds q, edges and corners included, or -1 when q is outside the hull.
     */
    public static int locate(long[][] pts, int[][] tris, long[] q) {
        for (int i = 0; i < tris.length; i++) {
            int[] t = tris[i];
            if (orient(pts[t[0]], pts[t[1]], q) >= 0 && orient(pts[t[1]], pts[t[2]], q) >= 0
                    && orient(pts[t[2]], pts[t[0]], q) >= 0) {
                return i;
            }
        }
        return -1;
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