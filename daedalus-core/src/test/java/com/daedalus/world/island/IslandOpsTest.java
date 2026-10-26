// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.World;
import com.daedalus.world.WorldStore;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class IslandOpsTest {

    @TempDir
    Path tmp;

    @Test
    void raisingPutsEveryCubeAtItsOffset() {
        World world = World.zero();
        IslandPlan plan = IslandGenerator.generate(11);
        BlockCoordinate origin = IslandOps.slot(0);
        assertThat(IslandOps.raise(world, origin, plan)).isEqualTo(IslandRaiseResult.RAISED);
        for (Map.Entry<BlockCoordinate, BlockType> e : plan.blocks().entrySet()) {
            BlockCoordinate rel = e.getKey();
            assertThat(world.get(new BlockCoordinate(origin.x() + rel.x(), origin.y() + rel.y(),
                    origin.z() + rel.z()))).isEqualTo(e.getValue());
        }
    }

    @Test
    void overlapPlacesNothing() {
        World world = World.zero();
        IslandPlan plan = IslandGenerator.generate(11);
        BlockCoordinate origin = IslandOps.slot(0);
        IslandOps.raise(world, origin, plan);
        long before = world.revision().value();
        int chunksBefore = world.chunkCount();
        assertThat(IslandOps.raise(world, origin, IslandGenerator.generate(12)))
                .isEqualTo(IslandRaiseResult.OVERLAP);
        assertThat(world.revision().value()).isEqualTo(before);
        assertThat(world.chunkCount()).isEqualTo(chunksBefore);
    }

    @Test
    void theLaneFillsSlotBySlot() {
        World world = World.zero();
        IslandPlan plan = IslandGenerator.generate(11);
        assertThat(IslandOps.firstFreeSlot(world, plan)).isZero();
        IslandOps.raise(world, IslandOps.slot(0), plan);
        assertThat(IslandOps.firstFreeSlot(world, plan)).isEqualTo(1);
        // A neighbour of any seed fits beside the first: slots never overlap each other.
        assertThat(IslandOps.raise(world, IslandOps.slot(1), IslandGenerator.generate(99,
                IslandGenerator.MAX_RADIUS))).isEqualTo(IslandRaiseResult.RAISED);
    }

    @Test
    void theLaneDoesNotTouchWorldZeroFixtures() {
        World world = World.zero();
        BlockCoordinate door = world.door().at();
        IslandOps.raise(world, IslandOps.slot(0), IslandGenerator.generate(11));
        assertThat(world.get(door)).isEqualTo(BlockType.AIR);
    }

    @Test
    void anIslandSurvivesSaveAndLoad() throws Exception {
        World world = World.zero();
        IslandPlan plan = IslandGenerator.generate(11);
        IslandOps.raise(world, IslandOps.slot(2), plan);
        Path file = tmp.resolve("islands.daew");
        WorldStore.save(world, file);
        World reloaded = WorldStore.load(file);
        assertThat(reloaded.revision()).isEqualTo(world.revision());
        assertThat(reloaded.chunkKeys()).isEqualTo(world.chunkKeys());
        BlockCoordinate origin = IslandOps.slot(2);
        for (Map.Entry<BlockCoordinate, BlockType> e : plan.blocks().entrySet()) {
            BlockCoordinate rel = e.getKey();
            assertThat(reloaded.get(new BlockCoordinate(origin.x() + rel.x(),
                    origin.y() + rel.y(), origin.z() + rel.z()))).isEqualTo(e.getValue());
        }
    }

    @Test
    void slotsOutsideTheLaneAreRefused() {
        assertThatThrownBy(() -> IslandOps.slot(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> IslandOps.slot(IslandOps.MAX_SLOTS))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
