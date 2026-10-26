// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.ParcelAccess;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.ParcelId;
import com.daedalus.world.ParcelVerb;
import com.daedalus.world.World;
import com.daedalus.world.WorldStore;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Island claims (ADR-026): a claim box holds the whole island and never touches a neighbour's;
 * claiming turns open ground into an owner's; abandoning opens it again; claims survive the store.
 */
class IslandClaimTest {

    @TempDir
    Path tmp;

    @Test
    void claimBoxesHoldTheBiggestIslandAndNeverTouchANeighbour() {
        for (int k = 0; k < 4; k++) {
            assertThat(IslandOps.claimBounds(k).overlaps(IslandOps.claimBounds(k + 1))).isFalse();
        }
        ParcelBounds box = IslandOps.claimBounds(3);
        BlockCoordinate origin = IslandOps.slot(3);
        for (long seed : new long[] {1, 11, 42, 777}) {
            IslandPlan plan = IslandGenerator.generate(seed, IslandGenerator.MAX_RADIUS);
            for (BlockCoordinate rel : plan.blocks().keySet()) {
                BlockCoordinate at = new BlockCoordinate(origin.x() + rel.x(), origin.y() + rel.y(),
                        origin.z() + rel.z());
                assertThat(box.contains(at)).as("seed %d cube %s", seed, rel).isTrue();
            }
        }
    }

    @Test
    void aClaimMakesTheGroundTheOwnersAndAbandoningOpensItAgain() {
        World world = new World(com.daedalus.world.WorldId.ZERO);
        BlockCoordinate at = IslandOps.slot(0);
        assertThat(world.may("bob", ParcelVerb.BLOCK_PLACE, at)).isEqualTo(ParcelAccess.ALLOWED);
        long before = world.revision().value();

        ParcelId id = world.claimParcel(IslandOps.claimBounds(0), "alice", "Isle 0");
        assertThat(id).isNotNull();
        assertThat(world.revision().value()).isEqualTo(before + 1);
        assertThat(world.may("alice", ParcelVerb.BLOCK_PLACE, at)).isEqualTo(ParcelAccess.ALLOWED);
        assertThat(world.may("bob", ParcelVerb.BLOCK_PLACE, at)).isEqualTo(ParcelAccess.DENIED);
        assertThat(world.may("system", ParcelVerb.BLOCK_PLACE, at)).isEqualTo(ParcelAccess.DENIED);
        world.grant(id, "bob", ParcelVerb.BLOCK_PLACE);
        assertThat(world.may("bob", ParcelVerb.BLOCK_PLACE, at)).isEqualTo(ParcelAccess.ALLOWED);
        assertThat(world.claimParcel(IslandOps.claimBounds(0), "carol", "Isle 0")).isNull();
        assertThat(world.may("bob", ParcelVerb.BLOCK_PLACE, IslandOps.slot(1))).isEqualTo(ParcelAccess.ALLOWED);

        assertThat(world.dropParcel(id)).isTrue();
        assertThat(world.dropParcel(id)).isFalse();
        assertThat(world.may("carol", ParcelVerb.BLOCK_PLACE, at)).isEqualTo(ParcelAccess.ALLOWED);
        ParcelId again = world.claimParcel(IslandOps.claimBounds(0), "carol", "Isle 0");
        assertThat(world.acl(again).grants()).as("an old grant does not carry to a new owner").isEmpty();
    }

    @Test
    void aClaimSurvivesTheStore() throws Exception {
        World world = new World(com.daedalus.world.WorldId.ZERO);
        world.place(IslandOps.slot(0), BlockType.GRASS);
        ParcelId id = world.claimParcel(IslandOps.claimBounds(0), "alice", "Isle 0");
        world.grant(id, "bob", ParcelVerb.BLOCK_PLACE);
        Path file = tmp.resolve("w.daew");
        WorldStore.save(world, file);

        World back = WorldStore.load(file);
        assertThat(back.parcelAt(IslandOps.slot(0)).ownerId()).isEqualTo("alice");
        assertThat(back.parcelAt(IslandOps.slot(0)).placeName()).isEqualTo("Isle 0");
        assertThat(back.may("bob", ParcelVerb.BLOCK_PLACE, IslandOps.slot(0))).isEqualTo(ParcelAccess.ALLOWED);
        assertThat(back.may("eve", ParcelVerb.BLOCK_PLACE, IslandOps.slot(0))).isEqualTo(ParcelAccess.DENIED);
    }
}
