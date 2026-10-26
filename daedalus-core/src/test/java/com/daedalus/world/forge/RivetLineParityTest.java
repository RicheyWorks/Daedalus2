// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ArkDrydock.ArkClass;
import com.daedalus.world.forge.RivetLine.Set;
import com.daedalus.world.forge.RivetLine.Tray;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * C++ = Java, line for line (G112): engines/unreal/core-test/rivet_line_parity.txt is written by
 * rivet_line_core_test.cpp --write from DaedalusRivetLineCore.h.
 */
class RivetLineParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "rivet_line_parity.txt");

    /** The same hands the C++ test plays: 0 master, 1 eager, 2 sloppy. */
    static List<Set> hand(Tray t, int seed, int h) {
        if (h == 0) {
            return RivetLine.master(t);
        }
        SplittableRandom rng = new SplittableRandom(seed * 17L + t.arkClass().ordinal() * 3 + h);
        List<Set> out = new ArrayList<>();
        int n = h == 1 ? t.holes() : t.holes() - rng.nextInt(5);
        for (int i = 0; i < n; i++) {
            int at = h == 1 ? t.readyMs().get(i) - 300 + rng.nextInt(700) : t.readyMs().get(i) + rng.nextInt(1200);
            int strikes = h == 1 ? 1 + rng.nextInt(4) : rng.nextInt(5);
            out.add(new Set(at, strikes));
        }
        return out;
    }

    static List<String> expected() {
        List<String> out = new ArrayList<>();
        for (ArkClass c : ArkClass.values()) {
            for (int seed = 0; seed < 40; seed++) {
                Tray t = RivetLine.tray(c, seed);
                for (int h = 0; h < 3; h++) {
                    out.add("c=" + c.ordinal() + " seed=" + seed + " hand=" + h + " " + RivetLine.encode(c, RivetLine.judge(t, hand(t, seed, h))));
                }
            }
        }
        return out;
    }

    @Test
    void javaMatchesTheCppParityFileLineForLine() throws IOException {
        List<String> lines = Files.readAllLines(PARITY);
        assertThat(lines.get(0)).startsWith("# rivet_line_core_test.cpp --write");
        assertThat(lines.subList(1, lines.size())).hasSize(360).containsExactlyElementsOf(expected());
    }
}
