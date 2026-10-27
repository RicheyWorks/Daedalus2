// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ArkDrydock.Ark;
import com.daedalus.world.forge.ArkDrydock.Life;
import com.daedalus.world.forge.ArkDrydock.Voyage;
import com.daedalus.world.forge.ShardLandfall.Hold;
import com.daedalus.world.forge.ShardLandfall.Pasture;
import com.daedalus.world.forge.ShardLandfall.Plan;
import com.daedalus.world.forge.VoidCrossing.Crossing;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * C++ = Java, line for line (G170 native core): engines/unreal/core-test/shard_landfall_parity.txt is written by
 * shard_landfall_core_test.cpp --write from DaedalusShardLandfallCore.h.
 */
class ShardLandfallParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "shard_landfall_parity.txt");

    /** Land every whole pair and every hive the hold has (often overgrazes). */
    static Plan all(Hold h) {
        Map<Life, Integer> pairs = new EnumMap<>(Life.class);
        for (Life k : ShardLandfall.PAIRED) {
            pairs.put(k, h.heads(k) / 2);
        }
        return new Plan(pairs, h.heads(Life.VENT_BEES));
    }

    static List<String> expected() {
        List<String> out = new ArrayList<>();
        for (int seed = 0; seed < 50; seed++) {
            Voyage v = ArkDrydock.voyage(seed);
            Ark g = VoidCrossingParityTest.generated(seed, v);
            for (int t = 0; t < 2; t++) {
                for (int sp = 0; sp <= 6; sp += 6) {
                    for (int hand = 0; hand < 3; hand++) {
                        Crossing x = VoidCrossingParityTest.play(g, v, t == 1, sp, seed, hand);
                        Hold h = Hold.of(x);
                        Pasture p = ShardLandfall.pasture(h.shard(), seed);
                        String head = "seed=" + seed + " tonic=" + t + " spares=" + sp + " hand=" + hand + " plan=";
                        out.add(head + "best " + ShardLandfall.land(h, p, ShardLandfall.best(h, p)).encode());
                        out.add(head + "none " + ShardLandfall.land(h, p, Plan.none()).encode());
                        out.add(head + "all " + ShardLandfall.land(h, p, all(h)).encode());
                    }
                }
            }
        }
        return out;
    }

    @Test
    void javaMatchesTheCppParityFileLineForLine() throws IOException {
        List<String> lines = Files.readAllLines(PARITY);
        assertThat(lines.get(0)).startsWith("# shard_landfall_core_test.cpp --write");
        assertThat(lines.subList(1, lines.size())).hasSize(1800).containsExactlyElementsOf(expected());
    }
}
