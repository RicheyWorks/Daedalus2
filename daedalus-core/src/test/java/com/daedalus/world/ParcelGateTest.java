// SPDX-License-Identifier: MIT

package com.daedalus.world;

import com.daedalus.engine.MazeGrid;
import com.daedalus.world.auto.WorldOps;
import com.daedalus.world.stamp.StampOps;
import com.daedalus.world.stamp.StampRequest;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ParcelGateTest {

    @Test
    void ownerIsAllowedAndStrangerIsDenied() {
        Parcel parcel = systemParcel();
        assertThat(ParcelGate.check(parcel, ParcelAcl.empty(), Parcel.SYSTEM_OWNER,
                ParcelVerb.BLOCK_PLACE)).isEqualTo(ParcelAccess.ALLOWED);
        assertThat(ParcelGate.check(parcel, ParcelAcl.empty(), "alice",
                ParcelVerb.BLOCK_PLACE)).isEqualTo(ParcelAccess.DENIED);
        assertThat(ParcelGate.check(parcel, null, "", ParcelVerb.DOOR_OPEN))
                .isEqualTo(ParcelAccess.DENIED);
    }

    @Test
    void aGrantLetsAStrangerThroughAndADenyWins() {
        Parcel parcel = systemParcel();
        ParcelAcl granted = ParcelAcl.empty().grant("alice", ParcelVerb.BLOCK_PLACE);
        assertThat(ParcelGate.check(parcel, granted, "alice", ParcelVerb.BLOCK_PLACE))
                .isEqualTo(ParcelAccess.ALLOWED);
        assertThat(ParcelGate.check(parcel, granted, "alice", ParcelVerb.DOOR_OPEN))
                .isEqualTo(ParcelAccess.DENIED);
        ParcelAcl denied = granted.deny("alice", ParcelVerb.BLOCK_PLACE);
        assertThat(ParcelGate.check(parcel, denied, "alice", ParcelVerb.BLOCK_PLACE))
                .isEqualTo(ParcelAccess.DENIED);
        assertThat(ParcelGate.check(parcel, denied.deny(Parcel.SYSTEM_OWNER, ParcelVerb.STAMP_APPLY),
                Parcel.SYSTEM_OWNER, ParcelVerb.STAMP_APPLY)).isEqualTo(ParcelAccess.DENIED);
    }

    @Test
    void unparceledCubesStayOpenAndAStampedParcelUsesTheGate() {
        World world = World.zero();
        BlockCoordinate far = new BlockCoordinate(40, 0, 40);
        assertThat(world.may("anyone", ParcelVerb.BLOCK_PLACE, far))
                .isEqualTo(ParcelAccess.ALLOWED);

        StampOps.apply(world, new StampRequest(world.id(), new BlockCoordinate(0, 0, 0),
                new MazeGrid(1, 1), 0, 1));
        ParcelId id = world.parcels().get(0).id();
        BlockCoordinate inside = new BlockCoordinate(0, 0, 0);
        assertThat(world.may(Parcel.SYSTEM_OWNER, ParcelVerb.BLOCK_PLACE, inside))
                .isEqualTo(ParcelAccess.ALLOWED);
        assertThat(world.may("bob", ParcelVerb.BLOCK_PLACE, inside))
                .isEqualTo(ParcelAccess.DENIED);

        long revision = world.revision().value();
        world.grant(id, "bob", ParcelVerb.BLOCK_PLACE);
        assertThat(world.may("bob", ParcelVerb.BLOCK_PLACE, inside))
                .isEqualTo(ParcelAccess.ALLOWED);
        BlockType before = world.get(inside);
        assertThat(WorldOps.drive(world, "block.place", inside, BlockType.STONE, null, "carol"))
                .isEqualTo(BlockPlaceResult.DENIED);
        assertThat(world.get(inside)).isEqualTo(before);
        assertThat(WorldOps.drive(world, "block.place", inside, BlockType.STONE, null, "bob"))
                .isEqualTo(before);
        assertThat(world.get(inside)).isEqualTo(BlockType.STONE);
        assertThat(WorldOps.drive(world, "block.remove", inside, null, null, "carol"))
                .isEqualTo(BlockPlaceResult.DENIED);
        assertThat(world.get(inside)).isEqualTo(BlockType.STONE);
        assertThat(WorldOps.aclLine(world)).isEqualTo("bob block.place");
        assertThat(WorldOps.aclAt(world, inside)).isEqualTo("bob block.place");
        assertThat(WorldOps.aclLine(World.zero())).isEmpty();
        assertThat(WorldOps.aclLine(null)).isEmpty();
        world.deny(id, "bob", ParcelVerb.BLOCK_PLACE);
        assertThat(WorldOps.aclLine(world)).isEqualTo("bob block.place · !bob block.place");
        assertThat(world.may("bob", ParcelVerb.BLOCK_PLACE, inside))
                .isEqualTo(ParcelAccess.DENIED);
        assertThat(WorldOps.drive(world, "block.remove", inside, null, null, "bob"))
                .isEqualTo(BlockPlaceResult.DENIED);
        assertThat(world.get(inside)).isEqualTo(BlockType.STONE);
        assertThat(world.revision().value()).isEqualTo(revision + 1);
        assertThatThrownBy(() -> world.grant(new ParcelId("parcel-missing"), "bob",
                ParcelVerb.DOOR_OPEN)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void boundsContainInclusiveCubes() {
        ParcelBounds box = new ParcelBounds(0, 0, 0, 2, 1, 2);
        assertThat(box.contains(new BlockCoordinate(0, 0, 0))).isTrue();
        assertThat(box.contains(new BlockCoordinate(2, 1, 2))).isTrue();
        assertThat(box.contains(new BlockCoordinate(3, 0, 0))).isFalse();
    }

    private static Parcel systemParcel() {
        return new Parcel(new ParcelId("parcel-1"), WorldId.ZERO, Parcel.SYSTEM_OWNER,
                new ParcelBounds(0, 0, 0, 2, 1, 2), 1L);
    }
}
