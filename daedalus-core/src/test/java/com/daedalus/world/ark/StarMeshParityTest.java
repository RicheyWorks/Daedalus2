// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;
import java.util.stream.IntStream;

import org.junit.jupiter.api.Test;

/**
 * Java = C++ for the star mesh core (G588 port of G441). engines/unreal/core-test/ark_star_mesh_parity.txt is
 * written from this class (run with -Dark.parity.write=true) and replayed line for line by ark_star_mesh_core_test.cpp
 * against DaedalusArkStarMeshCore.h. Inputs come from SplittableRandom(seed), which the C++ side draws bit for bit
 * through StableRng.
 */
class StarMeshParityTest {

    private static final Path FILE = Path.of("..", "engines", "unreal", "core-test", "ark_star_mesh_parity.txt");
    static final int SEEDS = 60;

    /** Seeds 1..40 draw 3 to 16 stars in [-100, 100]; seeds 41..60 draw them across the full +-10^6 sky. */
    static long[][] stars(SplittableRandom rng, int n, int span) {
        long[][] pts = new long[n][];
        for (int i = 0; i < n; i++) {
            long[] p;
            boolean bad;
            do {
                p = new long[] {rng.nextInt(2 * span + 1) - span, rng.nextInt(2 * span + 1) - span};
                bad = false;
                for (int j = 0; j < i && !bad; j++) {
                    bad = pts[j][0] == p[0] && pts[j][1] == p[1];
                    for (int k = j + 1; k < i && !bad; k++) {
                        bad = (pts[k][0] - pts[j][0]) * (p[1] - pts[j][1])
                                == (pts[k][1] - pts[j][1]) * (p[0] - pts[j][0]);
                    }
                }
            } while (bad);
            pts[i] = p;
        }
        return pts;
    }

    static List<String> starMesh() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            SplittableRandom rng = new SplittableRandom(s);
            int n = 3 + rng.nextInt(14);
            long[][] pts = stars(rng, n, s <= 40 ? 100 : (int) StarMesh.MAX_COORD);
            StringBuilder line = new StringBuilder("seed=" + s + " n=" + n + " stars=");
            for (int i = 0; i < n; i++) {
                line.append(i == 0 ? "" : ",").append(pts[i][0]).append(':').append(pts[i][1]);
            }
            StarMesh.Mesh mesh = StarMesh.build(pts);
            int[][] tris = mesh.triangles();
            describe(line, pts, mesh);
            line.append(" nbrs=");
            int[][] nbrs = StarMesh.neighbours(n, tris);
            for (int i = 0; i < n; i++) {
                line.append(i == 0 ? "" : "|").append(join(nbrs[i], "."));
            }
            // Four random sightings in the same sky, then star 0 itself (a corner of its triangles).
            int span = s <= 40 ? 100 : (int) StarMesh.MAX_COORD;
            line.append(" locate=");
            for (int q = 0; q < 5; q++) {
                long[] at = q < 4 ? new long[] {rng.nextInt(2 * span + 1) - span, rng.nextInt(2 * span + 1) - span}
                        : pts[0];
                line.append(q == 0 ? "" : ",").append(at[0]).append(':').append(at[1]).append('>')
                        .append(StarMesh.locate(pts, tris, at));
            }
            out.add(line.toString());
        }
        for (int i = 0; i < EDGE_SKIES.length; i++) {
            long[][] pts = EDGE_SKIES[i];
            StringBuilder line = new StringBuilder("sky=" + i + " n=" + pts.length);
            describe(line, pts, StarMesh.build(pts));
            out.add(line.toString());
        }
        for (int i = 0; i < REFUSED.length; i++) {
            String why = StarMesh.problem(REFUSED[i]);
            out.add("refused=" + i + " why=" + (why == null ? "ok" : why));
        }
        return out;
    }

    /** Triangles, hull, flip count, edge count and chart lines (minimum spanning tree) of one mesh. */
    static void describe(StringBuilder line, long[][] pts, StarMesh.Mesh mesh) {
        int[][] tris = mesh.triangles();
        line.append(" tris=").append(tris.length).append(' ');
        for (int i = 0; i < tris.length; i++) {
            line.append(i == 0 ? "" : ",").append(tris[i][0]).append('.').append(tris[i][1]).append('.')
                    .append(tris[i][2]);
        }
        line.append(" hull=").append(join(mesh.hull(), ",")).append(" flips=").append(mesh.flips());
        line.append(" edges=").append(StarMesh.edges(pts.length, tris).length).append(" chart=");
        int[][] chart = StarMesh.chartLines(pts, tris);
        for (int i = 0; i < chart.length; i++) {
            line.append(i == 0 ? "" : ",").append(chart[i][0]).append('-').append(chart[i][1]);
        }
    }

    /**
     * Hand skies at the edges of the rules: four and six cocircular stars (either diagonal is Delaunay, the insertion
     * order picks one), the four corners of the sky around a centre, the same square given clockwise, and a thin
     * sliver: stars a unit or two off the long east-west line across the sky.
     */
    static final long[][][] EDGE_SKIES = {
        {{0, 0}, {2, 0}, {2, 2}, {0, 2}},
        {{5, 0}, {3, 4}, {-3, 4}, {-5, 0}, {0, -5}, {4, -3}},
        {{-StarMesh.MAX_COORD, -StarMesh.MAX_COORD}, {StarMesh.MAX_COORD, -StarMesh.MAX_COORD},
            {StarMesh.MAX_COORD, StarMesh.MAX_COORD}, {-StarMesh.MAX_COORD, StarMesh.MAX_COORD}, {0, 1}},
        {{0, 2}, {2, 2}, {2, 0}, {0, 0}},
        {{-StarMesh.MAX_COORD, 0}, {-1, 1}, {1, 2}, {StarMesh.MAX_COORD, 1}, {0, -StarMesh.MAX_COORD}},
        {{0, 0}, {1, 0}, {0, 1}},
    };

    /** Bad skies, one per refusal reason (C++ builds the same list). */
    static final long[][][] REFUSED = {
        {{0, 0}, {1, 1}},
        new long[StarMesh.MAX_POINTS + 1][],
        {{0, 0}, {1, 0}, {0, StarMesh.MAX_COORD + 1}},
        {{0, 0}, {0, 0}, {2, 3}},
        {{0, 0}, {1, 1}, {2, 2}},
        {{0, 0}, {5, 1}, {2, 3}, {7, 4}, {9, 9}, {-3, -3}},
        {{0, 0}, {4, 0}, {0, 4}},
    };

    static {
        for (int i = 0; i < REFUSED[1].length; i++) {
            REFUSED[1][i] = new long[] {i, (long) i * i};
        }
    }

    static String join(int[] v, String sep) {
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < v.length; i++) {
            b.append(i == 0 ? "" : sep).append(v[i]);
        }
        return b.length() == 0 ? "-" : b.toString();
    }

    @Test
    void starMeshMatchesCpp() throws IOException {
        List<String> actual = starMesh();
        if (Boolean.getBoolean("ark.parity.write")) {
            List<String> body = new ArrayList<>();
            body.add("# G441 StarMesh parity (G588): written by StarMeshParityTest.java, replayed by"
                    + " ark_star_mesh_core_test.cpp. Seeds 1.." + SEEDS + " (triangles, hull, flips, edges, chart"
                    + " lines, neighbours, locate), then hand edge skies, then one refused sky per reason.");
            body.addAll(actual);
            Files.write(FILE, body, StandardCharsets.UTF_8);
        }
        List<String> expected = Files.readAllLines(FILE, StandardCharsets.UTF_8).stream()
                .filter(l -> !l.startsWith("#") && !l.isBlank()).toList();
        assertThat(expected).hasSize(actual.size());
        IntStream.range(0, actual.size())
                .forEach(i -> assertThat(actual.get(i)).as("line %d", i).isEqualTo(expected.get(i)));
    }
}
