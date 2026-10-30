// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class StarMeshTest {

    private static long orient(long[] a, long[] b, long[] c) {
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    }

    /** Random points with no three collinear and no four cocircular. */
    private static long[][] general(SplittableRandom rnd, int n, int span) {
        while (true) {
            List<long[]> pts = new ArrayList<>();
            while (pts.size() < n) {
                long[] p = {rnd.nextInt(2 * span + 1) - span, rnd.nextInt(2 * span + 1) - span};
                boolean ok = true;
                for (int i = 0; i < pts.size() && ok; i++) {
                    ok = pts.get(i)[0] != p[0] || pts.get(i)[1] != p[1];
                    for (int j = i + 1; j < pts.size() && ok; j++) {
                        ok = orient(pts.get(i), pts.get(j), p) != 0;
                    }
                }
                if (ok) {
                    pts.add(p);
                }
            }
            long[][] a = pts.toArray(new long[0][]);
            if (n > 25 || noFourCocircular(a)) {
                return a;
            }
        }
    }

    private static boolean noFourCocircular(long[][] a) {
        for (int i = 0; i < a.length; i++) {
            for (int j = i + 1; j < a.length; j++) {
                for (int k = j + 1; k < a.length; k++) {
                    for (int l = k + 1; l < a.length; l++) {
                        if (StarMesh.inCircle(a[i], a[j], a[k], a[l]) == 0) {
                            return false;
                        }
                    }
                }
            }
        }
        return true;
    }

    private static Set<List<Integer>> canon(int[][] tris) {
        Set<List<Integer>> s = new HashSet<>();
        for (int[] t : tris) {
            int[] c = t.clone();
            Arrays.sort(c);
            s.add(List.of(c[0], c[1], c[2]));
        }
        return s;
    }

    /** Brute force: every triple whose circumcircle holds no other point. */
    private static int[][] brute(long[][] p) {
        List<int[]> out = new ArrayList<>();
        for (int i = 0; i < p.length; i++) {
            for (int j = i + 1; j < p.length; j++) {
                for (int k = j + 1; k < p.length; k++) {
                    int[] t = orient(p[i], p[j], p[k]) > 0 ? new int[] {i, j, k} : new int[] {i, k, j};
                    if (StarMesh.emptyCircles(p, new int[][] {t})) {
                        out.add(t);
                    }
                }
            }
        }
        return out.toArray(new int[0][]);
    }

    private static int hullSize(long[][] p) {
        int h = 0;
        for (int i = 0; i < p.length; i++) {
            for (int j = 0; j < p.length; j++) {
                if (i == j) {
                    continue;
                }
                boolean edge = true;
                for (int k = 0; k < p.length && edge; k++) {
                    edge = k == i || k == j || orient(p[i], p[j], p[k]) > 0;
                }
                h += edge ? 1 : 0;
            }
        }
        return h;
    }

    @Test
    void matchesBruteForce() {
        SplittableRandom rnd = new SplittableRandom(441);
        for (int t = 0; t < 40; t++) {
            long[][] p = general(rnd, 3 + rnd.nextInt(20), 50);
            assertThat(canon(StarMesh.triangulate(p))).isEqualTo(canon(brute(p)));
        }
    }

    @Test
    void countsAndOrientation() {
        SplittableRandom rnd = new SplittableRandom(4410);
        for (int t = 0; t < 10; t++) {
            long[][] p = general(rnd, 40 + rnd.nextInt(60), 1_000_000);
            int[][] tris = StarMesh.triangulate(p);
            assertThat(tris.length).isEqualTo(2 * p.length - 2 - hullSize(p));
            for (int[] tr : tris) {
                assertThat(orient(p[tr[0]], p[tr[1]], p[tr[2]])).isPositive();
            }
            assertThat(StarMesh.emptyCircles(p, tris)).isTrue();
        }
    }

    @Test
    void squareCornersAndCentre() {
        long[][] p = {{0, 0}, {10, 1}, {9, 11}, {-1, 10}, {4, 5}};
        int[][] tris = StarMesh.triangulate(p);
        assertThat(tris.length).isEqualTo(4);
        for (int[] tr : tris) {
            assertThat(tr).contains(4);
        }
    }

    @Test
    void questAndBounds() {
        long[][] p = {{0, 0}, {10, 1}, {9, 11}, {-1, 10}, {4, 5}};
        assertThat(StarMesh.quest(p, 4)).isTrue();
        assertThat(StarMesh.quest(p, 3)).isFalse();
        assertThat(StarMesh.QUEST_ID).isEqualTo("q_star_mesh");
        assertThatThrownBy(() -> StarMesh.triangulate(new long[][] {{0, 0}, {1, 1}, {2, 2}}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> StarMesh.triangulate(new long[][] {{0, 0}, {1, 0}}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> StarMesh.triangulate(new long[][] {{0, 0}, {1, 0}, {0, 2_000_000}}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void hullNeighboursAndLocateMatchBruteForce() {
        SplittableRandom rnd = new SplittableRandom(4411);
        for (int t = 0; t < 30; t++) {
            long[][] p = general(rnd, 3 + rnd.nextInt(25), 1_000);
            StarMesh.Mesh mesh = StarMesh.build(p);
            // Hull: every consecutive pair is a hull edge with all other stars on its left, and it has every hull star.
            int[] hull = mesh.hull();
            assertThat(hull.length).isEqualTo(hullSize(p));
            for (int i = 0; i < hull.length; i++) {
                for (int k = 0; k < p.length; k++) {
                    if (k != hull[i] && k != hull[(i + 1) % hull.length]) {
                        assertThat(orient(p[hull[i]], p[hull[(i + 1) % hull.length]], p[k])).isPositive();
                    }
                }
            }
            // Neighbours: symmetric, and 2 * edges = 2 * (3n - 3 - h).
            int[][] nb = StarMesh.neighbours(p.length, mesh.triangles());
            int degrees = 0;
            for (int i = 0; i < p.length; i++) {
                degrees += nb[i].length;
                for (int j : nb[i]) {
                    assertThat(nb[j]).contains(i);
                }
            }
            assertThat(degrees).isEqualTo(2 * (3 * p.length - 3 - hull.length));
            // Locate: inside the hull exactly when some triangle holds the point, and that triangle does.
            for (int q = 0; q < 50; q++) {
                long[] at = {rnd.nextInt(2_401) - 1_200, rnd.nextInt(2_401) - 1_200};
                int found = StarMesh.locate(p, mesh.triangles(), at);
                boolean inside = true;
                for (int i = 0; i < hull.length; i++) {
                    inside &= orient(p[hull[i]], p[hull[(i + 1) % hull.length]], at) >= 0;
                }
                assertThat(found >= 0).isEqualTo(inside);
                if (found >= 0) {
                    int[] tr = mesh.triangles()[found];
                    assertThat(orient(p[tr[0]], p[tr[1]], at)).isNotNegative();
                    assertThat(orient(p[tr[1]], p[tr[2]], at)).isNotNegative();
                    assertThat(orient(p[tr[2]], p[tr[0]], at)).isNotNegative();
                }
            }
        }
    }

    @Test
    void flipsAndRefusalReasons() {
        // A convex quadrilateral inserted badly needs exactly one flip.
        StarMesh.Mesh quad = StarMesh.build(new long[][] {{0, 0}, {1, 5}, {2, -5}, {3, 0}});
        assertThat(quad.flips()).isEqualTo(1);
        assertThat(quad.hull()).containsExactly(0, 2, 3, 1);
        assertThat(StarMesh.problem(new long[][] {{0, 0}, {1, 1}})).isEqualTo("few");
        assertThat(StarMesh.problem(new long[][] {{0, 0}, {0, 0}, {2, 3}})).isEqualTo("duplicate");
        assertThat(StarMesh.problem(new long[][] {{0, 0}, {1, 1}, {2, 2}})).isEqualTo("collinear");
        assertThat(StarMesh.problem(new long[][] {{0, 0}, {1, 0}, {0, 1_000_001}})).isEqualTo("range");
        assertThat(StarMesh.problem(new long[][] {{0, 0}, {4, 0}, {0, 4}})).isNull();
        assertThatThrownBy(() -> StarMesh.build(new long[][] {{0, 0}, {1, 1}, {2, 2}}))
                .hasMessageContaining("collinear");
    }

    /** Prim on the complete graph: the sorted squared lengths of a minimum spanning tree (the same for every MST). */
    private static long[] primLengths(long[][] p) {
        int n = p.length;
        long[] best = new long[n];
        boolean[] in = new boolean[n];
        Arrays.fill(best, Long.MAX_VALUE);
        best[0] = 0;
        long[] out = new long[n - 1];
        for (int step = 0; step < n; step++) {
            int u = -1;
            for (int i = 0; i < n; i++) {
                if (!in[i] && (u < 0 || best[i] < best[u])) {
                    u = i;
                }
            }
            in[u] = true;
            if (step > 0) {
                out[step - 1] = best[u];
            }
            for (int i = 0; i < n; i++) {
                long dx = p[u][0] - p[i][0];
                long dy = p[u][1] - p[i][1];
                best[i] = Math.min(best[i], dx * dx + dy * dy);
            }
        }
        Arrays.sort(out);
        return out;
    }

    @Test
    void edgesAndChartLinesMatchBruteForce() {
        SplittableRandom rnd = new SplittableRandom(4412);
        for (int t = 0; t < 40; t++) {
            long[][] p = general(rnd, 3 + rnd.nextInt(30), t % 2 == 0 ? 40 : 1_000_000);
            int[][] tris = StarMesh.triangulate(p);
            assertThat(StarMesh.edges(p.length, tris)).hasNumberOfRows(3 * p.length - 3 - hullSize(p));
            int[][] chart = StarMesh.chartLines(p, tris);
            assertThat(chart).hasNumberOfRows(p.length - 1);
            long[] lengths = new long[chart.length];
            for (int i = 0; i < chart.length; i++) {
                long dx = p[chart[i][0]][0] - p[chart[i][1]][0];
                long dy = p[chart[i][0]][1] - p[chart[i][1]][1];
                lengths[i] = dx * dx + dy * dy;
            }
            Arrays.sort(lengths);
            assertThat(lengths).containsExactly(primLengths(p));
        }
    }

    @Test
    void edgeSkies() {
        // Four cocircular corners: two triangles either way, and every circumcircle is still empty.
        long[][] square = {{0, 0}, {2, 0}, {2, 2}, {0, 2}};
        assertThat(StarMesh.triangulate(square)).hasNumberOfRows(2);
        assertThat(StarMesh.emptyCircles(square, StarMesh.triangulate(square))).isTrue();
        // Six stars on one circle: a fan of four triangles with empty circles.
        long[][] ring = {{5, 0}, {3, 4}, {-3, 4}, {-5, 0}, {0, -5}, {4, -3}};
        assertThat(StarMesh.triangulate(ring)).hasNumberOfRows(4);
        assertThat(StarMesh.emptyCircles(ring, StarMesh.triangulate(ring))).isTrue();
        // The whole sky's corners around a centre star, given in any order.
        long m = StarMesh.MAX_COORD;
        long[][] corners = {{-m, -m}, {m, -m}, {m, m}, {-m, m}, {0, 1}};
        assertThat(StarMesh.triangulate(corners)).hasNumberOfRows(4);
        assertThat(StarMesh.build(corners).hull()).containsExactly(0, 1, 2, 3);
        // Three stars given clockwise still come back counter-clockwise.
        long[][] cw = {{0, 0}, {0, 1}, {1, 0}};
        int[] one = StarMesh.triangulate(cw)[0];
        assertThat(orient(cw[one[0]], cw[one[1]], cw[one[2]])).isPositive();
    }
}
