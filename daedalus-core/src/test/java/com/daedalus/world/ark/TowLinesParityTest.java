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
 * Java = C++ for the tow lines core (G584 port of G569). engines/unreal/core-test/ark_tow_lines_parity.txt is
 * written from this class (run with -Dark.parity.write=true) and replayed line for line by ark_tow_lines_core_test.cpp
 * against DaedalusArkTowLinesCore.h. Inputs come from SplittableRandom(seed), which the C++ side draws bit for bit
 * through StableRng.
 */
class TowLinesParityTest {

    private static final Path FILE = Path.of("..", "engines", "unreal", "core-test", "ark_tow_lines_parity.txt");
    static final int SEEDS = 60;

    /** Up to ten skiffs with loads in [-20, 20], then fourteen random ties, cuts, load changes and path questions. */
    static List<String> towLines() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= SEEDS; s++) {
            SplittableRandom rng = new SplittableRandom(s);
            int n = 1 + rng.nextInt(10);
            long[] loads = new long[n];
            for (int v = 0; v < n; v++) {
                loads[v] = rng.nextInt(41) - 20;
            }
            TowLines board = new TowLines(loads);
            List<int[]> tied = new ArrayList<>();
            StringBuilder ops = new StringBuilder();
            for (int k = 0; k < 14; k++) {
                int kind = rng.nextInt(4);
                if (kind == 1 && !tied.isEmpty()) {
                    int[] line = tied.remove(rng.nextInt(tied.size()));
                    boolean flipped = rng.nextBoolean();
                    int a = flipped ? line[1] : line[0];
                    int b = flipped ? line[0] : line[1];
                    ops.append(" cut=").append(a).append('-').append(b).append(':').append(board.cut(a, b) ? 1 : 0);
                } else if (kind == 2) {
                    int v = rng.nextInt(n);
                    long value = rng.nextInt(41) - 20;
                    board.setLoad(v, value);
                    ops.append(" load=").append(v).append(':').append(value);
                } else {
                    int a = rng.nextInt(n);
                    int b = rng.nextInt(n);
                    if (kind == 3) {
                        ops.append(" q=").append(a).append('-').append(b).append(':')
                                .append(board.joined(a, b) ? board.pathMax(a, b) + "/" + board.pathSum(a, b) : "-");
                    } else {
                        boolean tiedNow = board.link(a, b);
                        if (tiedNow) {
                            tied.add(new int[] {a, b});
                        }
                        ops.append(" link=").append(a).append('-').append(b).append(':').append(tiedNow ? 1 : 0);
                    }
                }
            }
            out.add("seed=" + s + " n=" + n + " loads=" + ArkTreesParityTest.join(loads) + ops);
        }
        return out;
    }

    @Test
    void towLinesMatchesCpp() throws IOException {
        List<String> actual = towLines();
        if (Boolean.getBoolean("ark.parity.write")) {
            List<String> body = new ArrayList<>();
            body.add("# G569 TowLines parity (G584): written by TowLinesParityTest.java, replayed by"
                    + " ark_tow_lines_core_test.cpp. Seeds 1.." + SEEDS + ".");
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
