// SPDX-License-Identifier: MIT

package com.daedalus.world;

import com.daedalus.engine.MazeGrid;
import com.daedalus.world.auto.WorldOps;
import com.daedalus.world.stamp.StampOps;
import com.daedalus.world.stamp.StampRequest;
import org.junit.jupiter.api.Test;

import java.util.Map;

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
    void aStampedDoorUsesTheGate() {
        World world = World.zero();
        StampOps.apply(world, new StampRequest(world.id(), new BlockCoordinate(0, 0, 0),
                new MazeGrid(1, 1), 0, 1));
        long revision = world.revision().value();
        assertThat(WorldOps.drive(world, "door.open", Door.ZERO_AT, null, null, "carol"))
                .isEqualTo(DoorResult.DENIED);
        @SuppressWarnings("unchecked")
        Map<String, Object> doorSeen = (Map<String, Object>) WorldOps.drive(
                world, "door.inspect", Door.ZERO_AT, null);
        assertThat(doorSeen.get("drive")).isEqualTo("door.open DENIED");
        assertThat(doorSeen.get("driveActor")).isEqualTo("carol");
        assertThat(world.door().state()).isEqualTo(DoorState.CLOSED);
        assertThat(world.revision().value()).isEqualTo(revision);
        assertThat(WorldOps.grantParcel(world, Door.ZERO_AT, "bob", "door.open"))
                .isEqualTo(ParcelGrantResult.GRANTED);
        assertThat(WorldOps.drive(world, "door.open", Door.ZERO_AT, null, null, "bob"))
                .isEqualTo(DoorResult.OPENED);
        assertThat(world.door().state()).isEqualTo(DoorState.OPEN);
        assertThat(WorldOps.denyParcel(world, Door.ZERO_AT, "bob", "door.open"))
                .isEqualTo(ParcelDenyResult.DENIED);
        assertThat(WorldOps.drive(world, "door.open", Door.ZERO_AT, null, null, "bob"))
                .isEqualTo(DoorResult.DENIED);
        assertThat(WorldOps.drive(world, "door.close", Door.ZERO_AT, null, null, "carol"))
                .isEqualTo(DoorResult.DENIED);
        assertThat(world.door().state()).isEqualTo(DoorState.OPEN);
        assertThat(WorldOps.drive(world, "door.open", Door.ZERO_AT, null, null, null))
                .isEqualTo(DoorResult.ALREADY_OPEN);
        assertThat(WorldOps.drive(world, "door.close", Door.ZERO_AT, null, null, null))
                .isEqualTo(DoorResult.CLOSED);
        assertThat(WorldOps.asStampResult(WorldOps.drive(
                world, "stamp.apply", new BlockCoordinate(0, 0, 0), null, null, null, "carol"))
                .outcome()).isEqualTo("DENIED");
        assertThat(WorldOps.grantParcel(world, new BlockCoordinate(0, 0, 0), "carol", "stamp.apply"))
                .isEqualTo(ParcelGrantResult.GRANTED);
        assertThat(WorldOps.asStampResult(WorldOps.drive(
                world, "stamp.apply", new BlockCoordinate(0, 0, 0), null, null, null, "carol"))
                .outcome()).isEqualTo("PARCEL_OVERLAP");
        assertThat(world.parcels()).hasSize(1);
        assertThat(WorldOps.asStampResult(WorldOps.drive(
                world, "stamp.apply", new BlockCoordinate(0, 0, 0), null))
                .outcome()).isEqualTo("PARCEL_OVERLAP");
    }

    @Test
    void aStampedTrapUsesTheGate() {
        World world = World.zero();
        StampOps.apply(world, new StampRequest(world.id(), new BlockCoordinate(0, 0, 0),
                new MazeGrid(1, 1), 0, 1));
        long revision = world.revision().value();
        assertThat(WorldOps.drive(world, "trap.arm", Trap.ZERO_AT, null, null, "carol"))
                .isEqualTo(TrapResult.DENIED);
        assertThat(WorldOps.actorLine(world)).isEqualTo("carol");
        assertThat(WorldOps.atLine(world)).isEqualTo("1,1,0");
        assertThat(WorldOps.driveOn(world, Trap.ZERO_AT)).isEqualTo("trap.arm DENIED");
        assertThat(WorldOps.actorOn(world, Trap.ZERO_AT)).isEqualTo("carol");
        assertThat(WorldOps.driveOn(world, new BlockCoordinate(0, 0, 0))).isEmpty();
        assertThat(WorldOps.actorOn(world, new BlockCoordinate(0, 0, 0))).isEmpty();
        @SuppressWarnings("unchecked")
        Map<String, Object> trapSeen = (Map<String, Object>) WorldOps.drive(
                world, "trap.inspect", Trap.ZERO_AT, null);
        assertThat(trapSeen.get("drive")).isEqualTo("trap.arm DENIED");
        assertThat(trapSeen.get("driveActor")).isEqualTo("carol");
        assertThat(world.trap().state()).isEqualTo(TrapState.DISARMED);
        assertThat(world.revision().value()).isEqualTo(revision);
        assertThat(WorldOps.grantParcel(world, Trap.ZERO_AT, "bob", "trap.arm"))
                .isEqualTo(ParcelGrantResult.GRANTED);
        assertThat(WorldOps.drive(world, "trap.arm", Trap.ZERO_AT, null, null, "bob"))
                .isEqualTo(TrapResult.ARMED);
        assertThat(world.trap().state()).isEqualTo(TrapState.ARMED);
        assertThat(WorldOps.denyParcel(world, Trap.ZERO_AT, "bob", "trap.arm"))
                .isEqualTo(ParcelDenyResult.DENIED);
        assertThat(WorldOps.drive(world, "trap.arm", Trap.ZERO_AT, null, null, "bob"))
                .isEqualTo(TrapResult.DENIED);
        assertThat(world.trap().state()).isEqualTo(TrapState.ARMED);
        assertThat(WorldOps.drive(world, "trap.arm", Trap.ZERO_AT, null, null, null))
                .isEqualTo(TrapResult.ALREADY_ARMED);
        assertThat(WorldOps.drive(world, "trap.disarm", Trap.ZERO_AT, null, null, "carol"))
                .isEqualTo(TrapResult.DENIED);
        assertThat(world.trap().state()).isEqualTo(TrapState.ARMED);
        assertThat(WorldOps.drive(world, "trap.disarm", Trap.ZERO_AT, null, null, null))
                .isEqualTo(TrapResult.DISARMED);
        assertThat(world.trap().state()).isEqualTo(TrapState.DISARMED);
        assertThat(WorldOps.driveLine(world)).isEqualTo("trap.disarm DISARMED");
        assertThat(WorldOps.actorLine(world)).isEqualTo(Parcel.SYSTEM_OWNER);
        assertThat(WorldOps.driveLine((World) null)).isEmpty();
        assertThat(WorldOps.actorLine((World) null)).isEmpty();
    }

    @Test
    void aStampedPortalUsesTheGate() {
        World world = World.zero();
        StampOps.apply(world, new StampRequest(world.id(), new BlockCoordinate(0, 0, 0),
                new MazeGrid(1, 1), 0, 1));
        long revision = world.revision().value();
        assertThat(WorldOps.drive(world, "portal.open", Portal.ZERO_AT, null, null, "carol"))
                .isEqualTo(PortalResult.DENIED);
        @SuppressWarnings("unchecked")
        Map<String, Object> portalSeen = (Map<String, Object>) WorldOps.drive(
                world, "portal.inspect", Portal.ZERO_AT, null);
        assertThat(portalSeen.get("drive")).isEqualTo("portal.open DENIED");
        assertThat(portalSeen.get("driveActor")).isEqualTo("carol");
        assertThat(world.portal().state()).isEqualTo(PortalState.SEALED);
        assertThat(world.revision().value()).isEqualTo(revision);
        assertThat(WorldOps.grantParcel(world, Portal.ZERO_AT, "bob", "portal.open"))
                .isEqualTo(ParcelGrantResult.GRANTED);
        assertThat(WorldOps.drive(world, "portal.open", Portal.ZERO_AT, null, null, "bob"))
                .isEqualTo(PortalResult.OPENED);
        assertThat(world.portal().state()).isEqualTo(PortalState.OPEN);
        assertThat(WorldOps.denyParcel(world, Portal.ZERO_AT, "bob", "portal.open"))
                .isEqualTo(ParcelDenyResult.DENIED);
        assertThat(WorldOps.drive(world, "portal.open", Portal.ZERO_AT, null, null, "bob"))
                .isEqualTo(PortalResult.DENIED);
        assertThat(world.portal().state()).isEqualTo(PortalState.OPEN);
        assertThat(WorldOps.drive(world, "portal.open", Portal.ZERO_AT, null, null, null))
                .isEqualTo(PortalResult.ALREADY_OPEN);
        assertThat(WorldOps.drive(world, "portal.seal", Portal.ZERO_AT, null, null, "carol"))
                .isEqualTo(PortalResult.DENIED);
        assertThat(world.portal().state()).isEqualTo(PortalState.OPEN);
        assertThat(WorldOps.drive(world, "portal.seal", Portal.ZERO_AT, null, null, null))
                .isEqualTo(PortalResult.SEALED);
        assertThat(world.portal().state()).isEqualTo(PortalState.SEALED);
    }

    @Test
    void aStampedNpcUsesTheGate() {
        World world = World.zero();
        StampOps.apply(world, new StampRequest(world.id(), new BlockCoordinate(0, 0, 0),
                new MazeGrid(1, 2), 0, 1));
        long revision = world.revision().value();
        assertThat(WorldOps.drive(world, "npc.talk", Npc.ZERO_AT, null, null, "carol"))
                .isEqualTo(NpcResult.DENIED);
        assertThat(world.npc().state()).isEqualTo(NpcState.IDLE);
        assertThat(world.revision().value()).isEqualTo(revision);
        assertThat(WorldOps.grantParcel(world, Npc.ZERO_AT, "bob", "npc.talk"))
                .isEqualTo(ParcelGrantResult.GRANTED);
        assertThat(WorldOps.drive(world, "npc.talk", Npc.ZERO_AT, null, null, "bob"))
                .isEqualTo(NpcResult.SPOKE);
        assertThat(world.npc().state()).isEqualTo(NpcState.SPEAKING);
        assertThat(WorldOps.denyParcel(world, Npc.ZERO_AT, "bob", "npc.talk"))
                .isEqualTo(ParcelDenyResult.DENIED);
        assertThat(WorldOps.drive(world, "npc.talk", Npc.ZERO_AT, null, null, "bob"))
                .isEqualTo(NpcResult.DENIED);
        assertThat(world.npc().state()).isEqualTo(NpcState.SPEAKING);
        assertThat(WorldOps.drive(world, "npc.talk", Npc.ZERO_AT, null, null, null))
                .isEqualTo(NpcResult.ALREADY_SPEAKING);
        assertThat(WorldOps.drive(world, "npc.hush", Npc.ZERO_AT, null, null, "carol"))
                .isEqualTo(NpcResult.DENIED);
        assertThat(world.npc().state()).isEqualTo(NpcState.SPEAKING);
        assertThat(WorldOps.drive(world, "npc.hush", Npc.ZERO_AT, null, null, null))
                .isEqualTo(NpcResult.HUSHED);
        assertThat(world.npc().state()).isEqualTo(NpcState.IDLE);
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
