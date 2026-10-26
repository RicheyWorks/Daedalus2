// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ArkDrydock.Ark;
import com.daedalus.world.forge.ArkDrydock.ArkClass;
import com.daedalus.world.forge.ArkDrydock.Life;
import com.daedalus.world.forge.ArkDrydock.Plate;
import com.daedalus.world.forge.ArkDrydock.Voyage;
import com.daedalus.world.forge.TemperForge.Quench;
import com.daedalus.world.forge.VoidCrossing.Crossing;
import com.daedalus.world.forge.VoidCrossing.Outcome;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * C++ = Java, line for line (G165): engines/unreal/core-test/void_crossing_parity.txt is written by
 * void_crossing_core_test.cpp --write from DaedalusVoidCrossingCore.h.
 */
class VoidCrossingParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "void_crossing_parity.txt");

    /** The same parity arks the C++ test builds. */
    static Ark generated(int seed, Voyage v) {
        SplittableRandom rng = new SplittableRandom(seed * 29L + 3);
        ArkClass c = ArkClass.values()[seed % ArkClass.values().length];
        List<Plate> plates = new ArrayList<>();
        List<Integer> rivets = new ArrayList<>();
        for (int k = 0; k < c.plates(); k++) {
            int t = 60 + rng.nextInt(41);
            Quench q = k == 0 ? Quench.DUAL : Quench.values()[rng.nextInt(3)];
            plates.add(new Plate(t, q, true));
            rivets.add(rng.nextInt(8) == 0 ? ArkDrydock.RIVETS_PER_SEAM - 1 : ArkDrydock.RIVETS_PER_SEAM);
        }
        Map<Life, Integer> m = new EnumMap<>(Life.class);
        for (Life l : Life.values()) {
            m.put(l, l.pairs() ? 2 * rng.nextInt(2) : rng.nextInt(3));
        }
        Ark dry = new Ark(c, plates, rivets, m, 0);
        int extra = rng.nextInt(300);
        int water = ArkDrydock.waterNeedDl(dry, v) + extra - (rng.nextInt(10) == 0 ? 400 : 0);
        return new Ark(c, plates, rivets, m, Math.max(0, water));
    }

    static Crossing play(Ark a, Voyage v, boolean tonic, int spares, int seed, int h) {
        if (h == 0) {
            return VoidCrossing.bosun(a, v, tonic, spares, seed);
        }
        Crossing x = VoidCrossing.depart(a, v, tonic, spares, seed);
        SplittableRandom rng = new SplittableRandom(seed * 7L + (tonic ? 2 : 0) + spares);
        int n = a.plates().size();
        while (x.outcome() == Outcome.SAILING) {
            x.sail(h == 1 ? -1 : rng.nextInt(n + 1) - 1);
        }
        return x;
    }

    static List<String> expected() {
        List<String> out = new ArrayList<>();
        for (int seed = 0; seed < 100; seed++) {
            Voyage v = ArkDrydock.voyage(seed);
            Ark g = generated(seed, v);
            for (int t = 0; t < 2; t++) {
                for (int sp = 0; sp <= 6; sp += 6) {
                    for (int h = 0; h < 3; h++) {
                        out.add("seed=" + seed + " tonic=" + t + " spares=" + sp + " hand=" + h + " " + play(g, v, t == 1, sp, seed, h).encode());
                    }
                }
            }
        }
        return out;
    }

    @Test
    void javaMatchesTheCppParityFileLineForLine() throws IOException {
        List<String> lines = Files.readAllLines(PARITY);
        assertThat(lines.get(0)).startsWith("# void_crossing_core_test.cpp --write");
        assertThat(lines.subList(1, lines.size())).hasSize(1200).containsExactlyElementsOf(expected());
    }
}
