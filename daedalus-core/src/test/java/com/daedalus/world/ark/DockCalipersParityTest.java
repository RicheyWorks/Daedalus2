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
 * Java = C++ for the dock calipers core (G592 port of G461). engines/unreal/core-test/ark_dock_calipers_parity.txt is
 * written from this class (run with -Dark.parity.write=true) and replayed line for line by
 * ark_dock_calipers_core_test.cpp against DaedalusArkDockCalipersCore.h. Inputs come from SplittableRandom(seed),
 * which the C++ side draws bit for bit through StableRng. The width is written as its IEEE bits in hex.
 */
class DockCalipersParityTest {

    private static final Path FILE = Path.of("..", "engines", "unreal", "core-test", "ark_dock_calipers_parity.txt");
    static final int SEEDS = 60;

    /** Seeds 1..30 crowd 1 to 40 buoys into [-5, 5] (repeats, collinear runs), 31..50 into [-1000, 1000], 51..60 the full +-10^6. */
    static int span(int seed) {
        return seed <= 30 ? 5 : seed <= 50 ? 1000 : (int) DockCalipers.MAX_COORD;
    }

    static List<String> dockCalipers() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            SplittableRandom rng = new SplittableRandom(s);
            int n = 1 + rng.nextInt(40);
            int span = span(s);
            long[][] pts = new long[n][];
            for (int i = 0; i < n; i++) {
                pts[i] = new long[] {rng.nextInt(2 * span + 1) - span, rng.nextInt(2 * span + 1) - span};
            }
            StringBuilder line = new StringBuilder("seed=" + s + " n=" + n + " buoys=");
            for (int i = 0; i < n; i++) {
                line.append(i == 0 ? "" : ",").append(pts[i][0]).append(':').append(pts[i][1]);
            }
            long[][] hull = DockCalipers.hull(pts);
            line.append(" hull=");
            for (int i = 0; i < hull.length; i++) {
                line.append(i == 0 ? "" : ",").append(hull[i][0]).append(':').append(hull[i][1]);
            }
            line.append(" diam2=").append(DockCalipers.diameterSquared(pts)).append(" width=")
                    .append(Long.toHexString(Double.doubleToRawLongBits(DockCalipers.width(pts))));
            out.add(line.toString());
        }
        return out;
    }

    @Test
    void dockCalipersMatchesCpp() throws IOException {
        List<String> actual = dockCalipers();
        if (Boolean.getBoolean("ark.parity.write")) {
            List<String> body = new ArrayList<>();
            body.add("# G461 DockCalipers parity (G592): written by DockCalipersParityTest.java, replayed by"
                    + " ark_dock_calipers_core_test.cpp. Seeds 1.." + SEEDS + "; width as IEEE bits in hex.");
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
