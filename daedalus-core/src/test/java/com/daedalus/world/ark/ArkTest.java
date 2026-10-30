// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.World;
import com.daedalus.world.island.IslandGenerator;
import com.daedalus.world.island.IslandOps;
import com.daedalus.world.island.IslandPlan;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

class ArkTest {

    @Test
    void anArkMoorsAtItsIslandsPierTip() {
        World world = World.zero();
        IslandPlan plan = IslandGenerator.generate(11);
        IslandOps.raise(world, IslandOps.slot(3), plan);
        Ark ark = ArkOps.launch(3, plan.traits());
        assertThat(ark.id()).isEqualTo("ark-3");
        assertThat(ark.homeSlot()).isEqualTo(3);
        assertThat(ark.slot()).isEqualTo(3);
        BlockCoordinate berth = ark.berth();
        // The berth is open air standing on a pier plank.
        assertThat(world.get(berth)).isEqualTo(BlockType.AIR);
        assertThat(world.get(new BlockCoordinate(berth.x(), berth.y() - 1, berth.z())))
                .isEqualTo(BlockType.WOOD);
    }

    @Test
    void namesAreAFunctionOfTheSeed() {
        assertThat(ArkNames.of(11)).isEqualTo(ArkNames.of(11));
        Set<String> names = new HashSet<>();
        for (long seed = 0; seed < 200; seed++) {
            String name = ArkNames.of(seed);
            assertThat(name).matches("[A-Z][a-z]+ [A-Z][a-z]+");
            names.add(name);
        }
        // 256 possible names; 200 seeds should land on plenty of them, not a handful.
        assertThat(names.size()).isGreaterThan(120);
    }
}
