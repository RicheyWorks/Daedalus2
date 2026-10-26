// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ForgeGrades.Material;
import com.daedalus.world.forge.TemperForge.Blank;
import com.daedalus.world.forge.TemperForge.Quench;
import com.daedalus.world.forge.TemperForge.Run;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * C++ = Java, line for line (G30): engines/unreal/core-test/temper_forge_parity.txt is written by
 * temper_forge_core_test.cpp --write from DaedalusTemperForgeCore.h, including its SplittableRandom port.
 */
class TemperForgeParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "temper_forge_parity.txt");
    private static final Material[] METALS = {Material.COPPER, Material.BRONZE, Material.IRON, Material.STEEL,
        Material.STARMETAL};
    private static final int[] SHIFTS = {40, 75, 110, 150, 300};

    /** The same ten runs the C++ test builds. */
    static Run variant(Blank b, Quench q, int v) {
        Run r = TemperForge.idealRun(b, q);
        List<Integer> s = new ArrayList<>(r.strikesMs());
        int pull = r.pullMs();
        int quench = r.quenchMs();
        if (v >= 1 && v <= 5) {
            int d = SHIFTS[v - 1];
            s.replaceAll(t -> t + d);
            quench += d;
        } else if (v == 6) {
            pull -= 2000;
        } else if (v == 7) {
            quench += 900;
        } else if (v == 8) {
            s.add(s.get(s.size() - 1) + 10);
            quench += 20;
        } else if (v == 9) {
            int cold = pull + (b.metal().targetC() - b.workableC() + 40) * 1000 / TemperForge.COOL_C_PER_S;
            s.set(s.size() - 1, cold);
            quench = cold + 10;
        }
        return new Run(pull, s, quench, q);
    }

    @Test
    void javaMatchesCppForEveryMetalSeedQuenchAndVariant() throws IOException {
        List<String> expected = new ArrayList<>();
        for (String line : Files.readAllLines(PARITY)) {
            if (!line.startsWith("#") && !line.isBlank()) {
                expected.add(line);
            }
        }
        List<String> actual = new ArrayList<>();
        for (Material m : METALS) {
            for (int seed = 0; seed < 20; seed++) {
                Blank b = TemperForge.blank(m, seed);
                for (Quench q : Quench.values()) {
                    for (int v = 0; v < 10; v++) {
                        actual.add(m.name() + " seed=" + seed + " v=" + v + " n=" + b.strikes() + " beat=" + b.beatMs()
                                + " | " + TemperForge.judge(b, variant(b, q, v)).encode());
                    }
                }
            }
        }
        assertThat(expected).hasSize(5 * 20 * 3 * 10);
        for (int i = 0; i < actual.size(); i++) {
            assertThat(actual.get(i)).as("line %d", i).isEqualTo(expected.get(i));
        }
    }
}
