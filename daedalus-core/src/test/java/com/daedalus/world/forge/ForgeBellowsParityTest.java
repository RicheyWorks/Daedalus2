// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ForgeBellows.Plan;
import com.daedalus.world.forge.ForgeGrades.Material;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * C++ = Java, line for line (G69): engines/unreal/core-test/forge_bellows_parity.txt is written by
 * forge_bellows_core_test.cpp --write from DaedalusForgeBellowsCore.h.
 */
class ForgeBellowsParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "forge_bellows_parity.txt");
    private static final Material[] METALS = {Material.COPPER, Material.BRONZE, Material.IRON, Material.STEEL,
        Material.STARMETAL};

    /** The third parity input: seeded coin-flip pumps, as the C++ test builds them. */
    static List<Boolean> fitful(long seed) {
        SplittableRandom rng = new SplittableRandom(seed * 7 + 3);
        List<Boolean> v = new ArrayList<>(ForgeBellows.TICKS);
        for (int t = 0; t < ForgeBellows.TICKS; t++) {
            v.add(rng.nextInt(2) == 0);
        }
        return v;
    }

    static List<String> expected() {
        List<String> out = new ArrayList<>();
        for (int m = 0; m < METALS.length; m++) {
            for (int ox = 0; ox <= ForgeBellows.MAX_OXEN; ox++) {
                for (int s = 0; s < 20; s++) {
                    Plan p = ForgeBellows.plan(METALS[m], ox, s);
                    String key = "m=" + m + " ox=" + ox + " s=" + s;
                    out.add(key + " steady " + ForgeBellows.run(p, ForgeBellows.steadyHand(p)).encode());
                    out.add(key + " spam " + ForgeBellows.run(p, Collections.nCopies(ForgeBellows.TICKS, true)).encode());
                    out.add(key + " fitful " + ForgeBellows.run(p, fitful(s)).encode());
                }
            }
        }
        return out;
    }

    @Test
    void javaMatchesTheCppParityFileLineForLine() throws IOException {
        List<String> lines = Files.readAllLines(PARITY);
        assertThat(lines.get(0)).startsWith("# forge_bellows_core_test.cpp --write");
        assertThat(lines.subList(1, lines.size())).containsExactlyElementsOf(expected());
    }
}
