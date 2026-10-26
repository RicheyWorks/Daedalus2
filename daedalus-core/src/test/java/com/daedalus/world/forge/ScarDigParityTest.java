// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ScarDig.Action;
import com.daedalus.world.forge.ScarDig.Kit;
import com.daedalus.world.forge.ScarDig.Plan;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * C++ = Java, line for line (G143): engines/unreal/core-test/scar_dig_parity.txt is written by scar_dig_core_test.cpp --write
 * from DaedalusScarDigCore.h.
 */
class ScarDigParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "scar_dig_parity.txt");
    private static final List<Kit> KITS = List.of(new Kit(false, false, 0), new Kit(false, false, 3), new Kit(true, false, 1),
            new Kit(true, true, 3));

    /** The same hands the C++ test plays: 0 prospector, 1 wild, 2 wild with swings off the west edge. */
    static List<Action> hand(Plan p, Kit k, int seed, int kitNo, int h) {
        if (h == 0) {
            return ScarDig.prospector(p, k);
        }
        SplittableRandom rng = new SplittableRandom(seed * 41L + kitNo * 5 + h);
        List<Action> out = new ArrayList<>();
        int n = 10 + rng.nextInt(50);
        for (int i = 0; i < n; i++) {
            if (rng.nextInt(8) == 0) {
                out.add(Action.drink());
            } else {
                int x = rng.nextInt(ScarDig.SIZE + 1) - (h == 2 ? 1 : 0);
                int y = rng.nextInt(ScarDig.SIZE);
                out.add(Action.swing(x, y));
            }
        }
        return out;
    }

    static List<String> expected() {
        List<String> out = new ArrayList<>();
        for (int seed = 0; seed < 50; seed++) {
            Plan p = ScarDig.plan(seed);
            for (int k = 0; k < KITS.size(); k++) {
                for (int h = 0; h < 3; h++) {
                    out.add("seed=" + seed + " kit=" + k + " hand=" + h + " "
                            + ScarDig.run(p, KITS.get(k), hand(p, KITS.get(k), seed, k, h)).encode());
                }
            }
        }
        return out;
    }

    @Test
    void javaMatchesTheCppParityFileLineForLine() throws IOException {
        List<String> lines = Files.readAllLines(PARITY);
        assertThat(lines.get(0)).startsWith("# scar_dig_core_test.cpp --write");
        assertThat(lines.subList(1, lines.size())).hasSize(600).containsExactlyElementsOf(expected());
    }
}
