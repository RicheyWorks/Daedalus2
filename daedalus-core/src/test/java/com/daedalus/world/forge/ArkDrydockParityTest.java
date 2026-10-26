// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ArkDrydock.Ark;
import com.daedalus.world.forge.ArkDrydock.ArkClass;
import com.daedalus.world.forge.ArkDrydock.Life;
import com.daedalus.world.forge.ArkDrydock.Plate;
import com.daedalus.world.forge.ArkDrydock.Voyage;
import com.daedalus.world.forge.TemperForge.Quench;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * C++ = Java, line for line (G31): engines/unreal/core-test/ark_drydock_parity.txt is written by
 * ark_drydock_core_test.cpp --write from DaedalusArkDrydockCore.h.
 */
class ArkDrydockParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "ark_drydock_parity.txt");

    /** The same seeded arks the C++ test builds. */
    static Ark generated(int seed, int v, Voyage voyage) {
        ArkClass c = ArkClass.values()[seed % 3];
        SplittableRandom rng = new SplittableRandom(seed * 31L + 7);
        int n = c.plates() - (rng.nextInt(8) == 0 ? 1 : 0);
        List<Plate> plates = new ArrayList<>();
        for (int k = 0; k < n; k++) {
            int t = 40 + rng.nextInt(61);
            Quench q = Quench.values()[rng.nextInt(3)];
            boolean stamped = rng.nextInt(10) != 0;
            plates.add(new Plate(t, q, stamped));
        }
        List<Integer> rivets = new ArrayList<>();
        for (int k = 0; k < n; k++) {
            rivets.add(2 + rng.nextInt(3));
        }
        Map<Life, Integer> manifest = new EnumMap<>(Life.class);
        for (Life l : Life.values()) {
            manifest.put(l, rng.nextInt(4));
        }
        int water = rng.nextInt(c.holdDl() + 1000);
        if (v >= 1) {
            plates = new ArrayList<>(Collections.nCopies(c.plates(), new Plate(90, Quench.DUAL, true)));
            rivets = new ArrayList<>(Collections.nCopies(c.plates(), ArkDrydock.RIVETS_PER_SEAM));
        }
        if (v >= 2) {
            manifest.replaceAll((l, k) -> l.pairs() ? k - k % 2 : k);
            water = ArkDrydock.waterNeedDl(new Ark(c, plates, rivets, manifest, 0), voyage);
        }
        return new Ark(c, plates, rivets, manifest, water);
    }

    @Test
    void javaMatchesCppForEverySeededArk() throws IOException {
        List<String> expected = new ArrayList<>();
        for (String line : Files.readAllLines(PARITY)) {
            if (!line.startsWith("#") && !line.isBlank()) {
                expected.add(line);
            }
        }
        List<String> actual = new ArrayList<>();
        for (int seed = 0; seed < 60; seed++) {
            for (int v = 0; v < 3; v++) {
                Voyage voyage = ArkDrydock.voyage(seed);
                actual.add("seed=" + seed + " v=" + v + " " + ArkClass.values()[seed % 3].name() + " " + voyage.shard()
                        + " " + voyage.days() + " | " + ArkDrydock.inspect(generated(seed, v, voyage), voyage).encode());
            }
        }
        assertThat(expected).hasSize(180);
        for (int i = 0; i < actual.size(); i++) {
            assertThat(actual.get(i)).as("line %d", i).isEqualTo(expected.get(i));
        }
        assertThat(expected.stream().filter(l -> l.contains("ready=1")).count()).isBetween(20L, 100L);
    }
}
