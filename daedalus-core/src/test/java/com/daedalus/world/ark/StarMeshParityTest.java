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
            int[][] tris = StarMesh.triangulate(pts);
            line.append(" tris=").append(tris.length).append(' ');
            for (int i = 0; i < tris.length; i++) {
                line.append(i == 0 ? "" : ",").append(tris[i][0]).append('.').append(tris[i][1]).append('.')
                        .append(tris[i][2]);
            }
            out.add(line.toString());
        }
        return out;
    }

    @Test
    void starMeshMatchesCpp() throws IOException {
        List<String> actual = starMesh();
        if (Boolean.getBoolean("ark.parity.write")) {
            List<String> body = new ArrayList<>();
            body.add("# G441 StarMesh parity (G588): written by StarMeshParityTest.java, replayed by"
                    + " ark_star_mesh_core_test.cpp. Seeds 1.." + SEEDS + ".");
            body.addAll(actual);
            Files.write(FILE, body, StandardCharsets.UTF_8);
        }
        List<String> expected = Files.readAllLines(FILE, StandardCharsets.UTF_8).stream()
                .filter(l -> !l.startsWith("#") && !l.isBlank()).toList();
        assertThat(expected).hasSize(SEEDS);
        IntStream.range(0, SEEDS)
                .forEach(i -> assertThat(actual.get(i)).as("line %d", i).isEqualTo(expected.get(i)));
    }
}
