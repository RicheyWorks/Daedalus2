// SPDX-License-Identifier: MIT

package com.daedalus.world.gate;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.World;
import com.daedalus.world.WorldId;
import com.daedalus.world.WorldStyle;
import com.daedalus.world.island.IslandOps;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Sky gates (ADR-031): in the clouds on the other side of the rainbow, out of every island's reach and
 * claim, never touching each other, the same cubes every time, built all or nothing.
 */
class GateOpsTest {

    @Test
    void aGateIsARainbowACloudBankARingAndADoorway() {
        Map<BlockCoordinate, BlockType> g = GateOps.plan(0);
        Set<BlockType> kinds = new HashSet<>(g.values());
        assertThat(kinds).contains(BlockType.CLOUD, BlockType.CRYSTAL, BlockType.PORTAL, BlockType.RAINBOW_RED,
                BlockType.RAINBOW_ORANGE, BlockType.RAINBOW_YELLOW, BlockType.RAINBOW_GREEN, BlockType.RAINBOW_BLUE,
                BlockType.RAINBOW_VIOLET);
        BlockCoordinate c = GateOps.center(0);
        assertThat(g.get(c)).as("the ring's centre is the doorway").isEqualTo(BlockType.PORTAL);
        // The rainbow stands between the islands (+Z) and the gate: you fly through it to get there.
        assertThat(g.entrySet()).filteredOn(e -> e.getValue().name().startsWith("RAINBOW_"))
                .allMatch(e -> e.getKey().z() == GateOps.RAINBOW_Z && e.getKey().z() > c.z());
        // Red is the outer band, violet the inner, as in the sky.
        int top = c.y() - 14;
        assertThat(g.get(new BlockCoordinate(c.x(), top + GateOps.RAINBOW_INNER, GateOps.RAINBOW_Z)))
                .isEqualTo(BlockType.RAINBOW_VIOLET);
        assertThat(g.get(new BlockCoordinate(c.x(), top + GateOps.RAINBOW_INNER + 5, GateOps.RAINBOW_Z)))
                .isEqualTo(BlockType.RAINBOW_RED);
        // The berth is open air over a cloud shelf, on the islands' side of the ring.
        BlockCoordinate b = GateOps.berth(0);
        assertThat(g.containsKey(b)).isFalse();
        assertThat(g.get(new BlockCoordinate(b.x(), b.y() - 1, b.z()))).isEqualTo(BlockType.CLOUD);
        assertThat(b.z()).isGreaterThan(c.z());
        assertThat(GateOps.plan(0)).isEqualTo(g);
    }

    @Test
    void gatesAreOutOfEveryIslandsReachAndClaimAndApartFromEachOther() {
        Set<BlockCoordinate> seen = new HashSet<>();
        for (int k = 0; k < GateOps.MAX_GATES; k++) {
            for (BlockCoordinate at : GateOps.plan(k).keySet()) {
                assertThat(seen.add(at)).as("gate %d overlaps another gate at %s", k, at).isTrue();
                for (int slot = 0; slot < 8; slot++) {
                    assertThat(IslandOps.claimBounds(slot).contains(at)).as("gate %d inside island %d's claim", k, slot)
                            .isFalse();
                }
            }
        }
        assertThatThrownBy(() -> GateOps.center(GateOps.MAX_GATES)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> GateOps.center(-1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void arksNameAGateWithASlotNoIslandUses() {
        assertThat(GateOps.slotOfGate(0)).isEqualTo(1000);
        assertThat(GateOps.isGateSlot(1003)).isTrue();
        assertThat(GateOps.isGateSlot(63)).isFalse();
        assertThat(GateOps.isGateSlot(1000 + GateOps.MAX_GATES)).isFalse();
        assertThat(GateOps.gateOfSlot(1005)).isEqualTo(5);
        assertThat(GateOps.GATE_BASE).isGreaterThan(IslandOps.MAX_SLOTS);
        assertThatThrownBy(() -> GateOps.gateOfSlot(3)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void buildingIsAllOrNothing() {
        World w = new World(new WorldId("sky-test"));
        assertThat(GateOps.build(w, 1)).isTrue();
        for (Map.Entry<BlockCoordinate, BlockType> e : GateOps.plan(1).entrySet()) {
            assertThat(w.get(e.getKey())).isEqualTo(e.getValue());
        }
        assertThat(GateOps.build(w, 1)).as("its cubes are taken now").isFalse();
        World other = new World(new WorldId("sky-test-2"));
        BlockCoordinate blocker = GateOps.center(2);
        other.place(blocker, BlockType.STONE);
        long rev = other.revision().value();
        assertThat(GateOps.build(other, 2)).isFalse();
        assertThat(other.revision().value()).as("nothing placed").isEqualTo(rev);
    }

    @Test
    void everyWorldStyleHasAMountThatFliesOnceItsWorldShips() {
        assertThat(Mount.of(WorldStyle.SKY_ISLANDS)).isEqualTo(Mount.ARK);
        assertThat(Mount.of(WorldStyle.PARCELS)).isEqualTo(Mount.HELICOPTER);
        assertThat(Mount.of(WorldStyle.LABYRINTH)).isEqualTo(Mount.SKY_STRIDER);
        for (WorldStyle s : WorldStyle.values()) {
            assertThat(Mount.of(s).ready()).as(s.name()).isEqualTo(s.ready());
        }
        assertThat(BlockType.PORTAL.seeThrough()).isTrue();
        assertThat(BlockType.RAINBOW_RED.seeThrough()).isTrue();
        assertThat(BlockType.CRYSTAL.seeThrough()).isFalse();
    }
}
