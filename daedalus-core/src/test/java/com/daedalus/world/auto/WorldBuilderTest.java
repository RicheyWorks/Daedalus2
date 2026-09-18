// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.ChunkCoordinate;
import com.daedalus.world.Door;
import com.daedalus.world.Npc;
import com.daedalus.world.Parcel;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.ParcelDenyResult;
import com.daedalus.world.ParcelForgiveResult;
import com.daedalus.world.ParcelGrantResult;
import com.daedalus.world.ParcelLeaseResult;
import com.daedalus.world.ParcelReleaseResult;
import com.daedalus.world.ParcelRevokeResult;
import com.daedalus.world.ParcelVerb;
import com.daedalus.world.PlaceNames;
import com.daedalus.world.TrapResult;
import com.daedalus.world.TrapState;
import com.daedalus.world.World;
import com.daedalus.world.stamp.StampOps;
import com.daedalus.world.stamp.StampResult;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Builder recipes drive {@link WorldOps} only. No agent.* verbs.
 */
class WorldBuilderTest {

    @Test
    void aRecipePlacesAndArmsThroughWorldOps() {
        World world = World.zero();
        WorldBuilder builder = new WorldBuilder(world);
        BlockCoordinate at = new BlockCoordinate(3, 0, 1);
        long before = world.revision().value();
        List<DriveTrace.Step> trace = builder.run(List.of(
                new WorldBuilder.Step(at, "block.place", BlockType.STONE),
                new WorldBuilder.Step(at, "block.inspect", null),
                new WorldBuilder.Step(at, "trap.arm", null)));
        assertThat(world.get(at)).isEqualTo(BlockType.STONE);
        assertThat(world.revision().value()).isGreaterThan(before);
        assertThat(world.trap().state()).isEqualTo(TrapState.ARMED);
        assertThat(trace)
                .extracting(DriveTrace.Step::capability)
                .containsExactly("block.place", "block.inspect", "trap.arm");
        assertThat(trace.get(2).result()).isEqualTo(TrapResult.ARMED.toString());
        AccountingReport report = AccountingHarness.account(
                WorldZeroCapabilities.registry(), WorldZeroDrive.DRIVEN);
        AccountingHarness.requireAccounted(report);
        assertThat(report.unaccountedCount()).isZero();
    }

    @Test
    void aRecipeStampsThenLeasesThroughWorldOps() {
        World world = World.zero();
        WorldBuilder builder = new WorldBuilder(world);
        assertThat(WorldOps.asStampResult(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "stamp.apply", null))).outcome())
                .isEqualTo("APPLIED");
        assertThat(world.parcels()).hasSize(1);
        assertThat(world.parcels().get(0).placeName()).isIn(PlaceNames.STREETS);
        assertThat(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.lease", null)))
                .isEqualTo(ParcelLeaseResult.LEASED);
        assertThat(world.parcels().get(0).leaseId()).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.lease", null)))
                .isEqualTo(ParcelLeaseResult.ALREADY_LEASED);
        assertThat(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.release", null)))
                .isEqualTo(ParcelReleaseResult.RELEASED);
        assertThat(world.parcels().get(0).leaseId()).isEmpty();
        assertThat(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.release", null)))
                .isEqualTo(ParcelReleaseResult.NOT_LEASED);
        assertThat(new WorldBuilder(World.zero()).run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.release", null)))
                .isEqualTo(ParcelReleaseResult.NO_PARCEL);
        assertThat(WorldOps.releaseParcel(null)).isEqualTo(ParcelReleaseResult.NO_PARCEL);
    }

    @Test
    void aRecipePassesActorAndVerb() {
        World world = World.zero();
        WorldBuilder builder = new WorldBuilder(world);
        BlockCoordinate origin = new BlockCoordinate(0, 0, 0);
        assertThat(WorldOps.asStampResult(builder.run(new WorldBuilder.Step(
                origin, "stamp.apply", null))).outcome())
                .isEqualTo("APPLIED");
        assertThat(builder.run(new WorldBuilder.Step(
                origin, "parcel.grant", null, null, "bob", "door.open")))
                .isEqualTo(ParcelGrantResult.GRANTED);
        assertThat(WorldOps.aclLine(world)).isEqualTo("bob door.open");
        assertThat(WorldOps.asStampResult(builder.run(new WorldBuilder.Step(
                origin, "stamp.apply", null, null, "", "carol"))).outcome())
                .isEqualTo("DENIED");
        assertThat(WorldOps.actorLine(world)).isEqualTo("carol");
        List<DriveTrace.Step> driven = builder.session().trace();
        assertThat(driven.get(driven.size() - 1).actor()).isEqualTo("carol");
        assertThat(driven.get(driven.size() - 1).at()).isEqualTo("0,0,0");
        assertThat(world.parcels()).hasSize(1);
    }

    @Test
    void aSecondPlotLeasesWhenTheFirstIsTaken() {
        World world = World.zero();
        WorldBuilder builder = new WorldBuilder(world);
        builder.run(new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "stamp.apply", null));
        BlockCoordinate next = StampOps.nextOrigin(
                world, new MazeGrid(1, 1), new BlockCoordinate(0, 0, 0), 1);
        builder.run(new WorldBuilder.Step(next, "stamp.apply", null));
        assertThat(world.parcels()).hasSize(2);
        assertThat(world.parcels().get(0).placeName()).isIn(PlaceNames.STREETS);
        assertThat(world.parcels().get(1).placeName()).isIn(PlaceNames.STREETS);
        assertThat(world.parcels().get(1).placeName())
                .isNotEqualTo(world.parcels().get(0).placeName());
        assertThat(WorldOps.lastPlaceName(world)).isEqualTo(world.parcels().get(1).placeName());
        assertThat(WorldOps.streetLine(world))
                .isEqualTo(world.parcels().get(0).placeName() + " · "
                        + world.parcels().get(1).placeName());
        assertThat(WorldOps.lastLot(world)).isEqualTo(next.x() + "," + next.z());
        assertThat(WorldOps.streetLots(world))
                .isEqualTo("0,0 · " + next.x() + "," + next.z());
        assertThat(WorldOps.lastLot(World.zero())).isEmpty();
        assertThat(WorldOps.streetLots(World.zero())).isEmpty();
        @SuppressWarnings("unchecked")
        Map<String, Object> snap = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(next, "world.inspect", null));
        assertThat(snap.get("plots")).isEqualTo(2);
        assertThat(snap.get("street")).isEqualTo(WorldOps.streetLine(world));
        assertThat(snap.get("lot")).isEqualTo(WorldOps.streetLots(world));
        assertThat(snap.get("maze")).isEqualTo(WorldOps.streetMazes(world));
        assertThat(snap.get("occupants")).isEqualTo("door · trap · portal · npc");
        assertThat(snap.get("stands"))
                .isEqualTo("door 0,1,0 · trap 1,1,0 · portal 2,1,0 · npc 3,1,0");
        assertThat(WorldOps.occupantsLine(World.zero())).isEqualTo("door · trap · portal · npc");
        assertThat(WorldOps.occupantsLine(null)).isEmpty();
        assertThat(WorldOps.standsLine(World.zero()))
                .isEqualTo("door 0,1,0 · trap 1,1,0 · portal 2,1,0 · npc 3,1,0");
        assertThat(WorldOps.standsLine(null)).isEmpty();
        assertThat(snap.get("acl")).isEqualTo("");
        assertThat(WorldOps.aclLine(world)).isEmpty();
        assertThat(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.grant", null, null, "bob")))
                .isEqualTo(ParcelGrantResult.GRANTED);
        assertThat(WorldOps.aclLine(world)).isEqualTo("bob block.place");
        assertThat(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.grant", null, null, "bob")))
                .isEqualTo(ParcelGrantResult.ALREADY_GRANTED);
        assertThat(new WorldBuilder(World.zero()).run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.grant", null, null, "bob")))
                .isEqualTo(ParcelGrantResult.NO_PARCEL);
        assertThat(WorldOps.grantParcel(null, null, "bob"))
                .isEqualTo(ParcelGrantResult.NO_PARCEL);
        assertThat(WorldOps.grantParcel(world, new BlockCoordinate(0, 0, 0), "bob", "door.open"))
                .isEqualTo(ParcelGrantResult.GRANTED);
        assertThat(WorldOps.aclLine(world)).isEqualTo("bob block.place · bob door.open");
        assertThat(WorldOps.grantParcel(world, new BlockCoordinate(0, 0, 0), "bob", "door.open"))
                .isEqualTo(ParcelGrantResult.ALREADY_GRANTED);
        assertThat(WorldOps.grantParcel(world, new BlockCoordinate(0, 0, 0), "bob", "shop.open"))
                .isEqualTo(ParcelGrantResult.UNKNOWN_VERB);
        assertThat(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.deny", null, null, "bob")))
                .isEqualTo(ParcelDenyResult.DENIED);
        assertThat(WorldOps.aclLine(world))
                .isEqualTo("bob block.place · bob door.open · !bob block.place");
        assertThat(WorldOps.denyParcel(world, new BlockCoordinate(0, 0, 0), "bob", "door.open"))
                .isEqualTo(ParcelDenyResult.DENIED);
        assertThat(WorldOps.aclLine(world))
                .isEqualTo("bob block.place · bob door.open · !bob block.place · !bob door.open");
        assertThat(WorldOps.denyParcel(world, new BlockCoordinate(0, 0, 0), "bob", "shop.open"))
                .isEqualTo(ParcelDenyResult.UNKNOWN_VERB);
        assertThat(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.deny", null, null, "bob")))
                .isEqualTo(ParcelDenyResult.ALREADY_DENIED);
        assertThat(new WorldBuilder(World.zero()).run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.deny", null, null, "bob")))
                .isEqualTo(ParcelDenyResult.NO_PARCEL);
        assertThat(WorldOps.denyParcel(null, null, "bob"))
                .isEqualTo(ParcelDenyResult.NO_PARCEL);
        assertThat(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.revoke", null, null, "bob")))
                .isEqualTo(ParcelRevokeResult.REVOKED);
        assertThat(WorldOps.aclLine(world))
                .isEqualTo("bob door.open · !bob block.place · !bob door.open");
        assertThat(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.revoke", null, null, "bob")))
                .isEqualTo(ParcelRevokeResult.NOT_GRANTED);
        assertThat(new WorldBuilder(World.zero()).run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.revoke", null, null, "bob")))
                .isEqualTo(ParcelRevokeResult.NO_PARCEL);
        assertThat(WorldOps.revokeParcel(null, null, "bob"))
                .isEqualTo(ParcelRevokeResult.NO_PARCEL);
        assertThat(WorldOps.revokeParcel(world, new BlockCoordinate(0, 0, 0), "bob", "shop.open"))
                .isEqualTo(ParcelRevokeResult.UNKNOWN_VERB);
        assertThat(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.forgive", null, null, "bob")))
                .isEqualTo(ParcelForgiveResult.FORGIVEN);
        assertThat(WorldOps.aclLine(world))
                .isEqualTo("bob door.open · !bob door.open");
        assertThat(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.forgive", null, null, "bob")))
                .isEqualTo(ParcelForgiveResult.NOT_DENIED);
        assertThat(new WorldBuilder(World.zero()).run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.forgive", null, null, "bob")))
                .isEqualTo(ParcelForgiveResult.NO_PARCEL);
        assertThat(WorldOps.forgiveParcel(null, null, "bob"))
                .isEqualTo(ParcelForgiveResult.NO_PARCEL);
        assertThat(WorldOps.forgiveParcel(world, new BlockCoordinate(0, 0, 0), "bob",
                "shop.open"))
                .isEqualTo(ParcelForgiveResult.UNKNOWN_VERB);
        assertThat(builder.run(new WorldBuilder.Step(next, "parcel.lease", null)))
                .isEqualTo(ParcelLeaseResult.LEASED);
        assertThat(world.parcels().get(0).leaseId()).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(builder.run(new WorldBuilder.Step(next, "parcel.lease", null)))
                .isEqualTo(ParcelLeaseResult.LEASED);
        assertThat(world.parcels().get(1).leaseId()).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(WorldOps.lastLeaseId(world)).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(builder.run(new WorldBuilder.Step(next, "parcel.lease", null)))
                .isEqualTo(ParcelLeaseResult.ALREADY_LEASED);
        assertThat(builder.run(new WorldBuilder.Step(next, "parcel.release", null)))
                .isEqualTo(ParcelReleaseResult.RELEASED);
        assertThat(world.parcels().get(0).leaseId()).isEmpty();
        assertThat(WorldOps.lastLeaseId(world)).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(builder.run(new WorldBuilder.Step(next, "parcel.release", null)))
                .isEqualTo(ParcelReleaseResult.RELEASED);
        assertThat(WorldOps.lastLeaseId(world)).isEmpty();
        assertThat(builder.run(new WorldBuilder.Step(next, "parcel.release", null)))
                .isEqualTo(ParcelReleaseResult.NOT_LEASED);
    }

    @Test
    void occupancyInspectNamesTheSlab() {
        World world = World.zero();
        WorldBuilder builder = new WorldBuilder(world);
        builder.run(new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "stamp.apply", null));
        String place = world.parcels().get(0).placeName();
        @SuppressWarnings("unchecked")
        Map<String, Object> door = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "door.inspect", null));
        assertThat(door.get("place")).isEqualTo(place);
        assertThat(door.get("lot")).isEqualTo("0,0");
        assertThat(door.get("box")).isEqualTo("0,0,0-2,1,2");
        assertThat(door.get("maze")).isEqualTo("");
        assertThat(door.get("lease")).isEqualTo("");
        assertThat(door.get("acl")).isEqualTo("");
        assertThat(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.lease", null)))
                .isEqualTo(ParcelLeaseResult.LEASED);
        @SuppressWarnings("unchecked")
        Map<String, Object> leased = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "door.inspect", null));
        assertThat(leased.get("lease")).isEqualTo(Parcel.SYSTEM_TENANT);
        @SuppressWarnings("unchecked")
        Map<String, Object> trap = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "trap.inspect", null));
        assertThat(trap.get("place")).isEqualTo(place);
        assertThat(trap.get("lot")).isEqualTo("0,0");
        assertThat(trap.get("box")).isEqualTo("0,0,0-2,1,2");
        assertThat(trap.get("maze")).isEqualTo("");
        assertThat(trap.get("lease")).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(trap.get("acl")).isEqualTo("");
        @SuppressWarnings("unchecked")
        Map<String, Object> portal = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "portal.inspect", null));
        assertThat(portal.get("place")).isEqualTo(place);
        assertThat(portal.get("lot")).isEqualTo("0,0");
        assertThat(portal.get("box")).isEqualTo("0,0,0-2,1,2");
        assertThat(portal.get("maze")).isEqualTo("");
        assertThat(portal.get("lease")).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(portal.get("acl")).isEqualTo("");
        @SuppressWarnings("unchecked")
        Map<String, Object> npc = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "npc.inspect", null));
        assertThat(npc.get("place")).isEqualTo("");
        assertThat(npc.get("lot")).isEqualTo("");
        assertThat(npc.get("box")).isEqualTo("");
        assertThat(npc.get("maze")).isEqualTo("");
        assertThat(npc.get("lease")).isEqualTo("");
        assertThat(npc.get("acl")).isEqualTo("");
        @SuppressWarnings("unchecked")
        Map<String, Object> onDoor = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(Door.ZERO_AT, "block.inspect", null));
        assertThat(onDoor.get("occupant")).isEqualTo("door");
        assertThat(onDoor.get("acl")).isEqualTo("");
        @SuppressWarnings("unchecked")
        Map<String, Object> onNpc = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(Npc.ZERO_AT, "block.inspect", null));
        assertThat(onNpc.get("occupant")).isEqualTo("npc");
        @SuppressWarnings("unchecked")
        Map<String, Object> empty = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(9, 0, 9), "block.inspect", null));
        assertThat(empty.get("occupant")).isEqualTo("");
        assertThat(empty.get("acl")).isEqualTo("");
        world.grant(world.parcels().get(0).id(), "bob", ParcelVerb.BLOCK_PLACE);
        @SuppressWarnings("unchecked")
        Map<String, Object> granted = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(Door.ZERO_AT, "block.inspect", null));
        assertThat(granted.get("acl")).isEqualTo("bob block.place");
        @SuppressWarnings("unchecked")
        Map<String, Object> off = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(9, 0, 9), "block.inspect", null));
        assertThat(off.get("acl")).isEqualTo("");
        @SuppressWarnings("unchecked")
        Map<String, Object> doorGranted = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(Door.ZERO_AT, "door.inspect", null));
        assertThat(doorGranted.get("acl")).isEqualTo("bob block.place");
        @SuppressWarnings("unchecked")
        Map<String, Object> trapGranted = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(Door.ZERO_AT, "trap.inspect", null));
        assertThat(trapGranted.get("acl")).isEqualTo("bob block.place");
        @SuppressWarnings("unchecked")
        Map<String, Object> portalGranted = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(Door.ZERO_AT, "portal.inspect", null));
        assertThat(portalGranted.get("acl")).isEqualTo("bob block.place");
        @SuppressWarnings("unchecked")
        Map<String, Object> npcOff = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(Npc.ZERO_AT, "npc.inspect", null));
        assertThat(npcOff.get("acl")).isEqualTo("");
        World wide = World.zero();
        wide.applyStamp(new ParcelBounds(0, 0, 0, 4, 1, 2), Parcel.SYSTEM_OWNER,
                List.of(new BlockCoordinate(0, 0, 0)), List.of(BlockType.STONE));
        wide.grant(wide.parcels().get(0).id(), "bob", ParcelVerb.BLOCK_PLACE);
        @SuppressWarnings("unchecked")
        Map<String, Object> npcOn = (Map<String, Object>) new WorldBuilder(wide).run(
                new WorldBuilder.Step(Npc.ZERO_AT, "npc.inspect", null));
        assertThat(npcOn.get("acl")).isEqualTo("bob block.place");
    }

    @Test
    void chunkInspectNamesOverlappingPlots() {
        World world = World.zero();
        WorldBuilder builder = new WorldBuilder(world);
        builder.run(new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "stamp.apply", null));
        builder.run(new WorldBuilder.Step(new BlockCoordinate(32, 0, 0), "stamp.apply", null));
        @SuppressWarnings("unchecked")
        Map<String, Object> origin = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "chunk.inspect", null));
        assertThat(origin.get("plots")).isEqualTo(1);
        assertThat(origin.get("street")).isEqualTo(world.parcels().get(0).placeName());
        assertThat(origin.get("lot")).isEqualTo("0,0");
        assertThat(origin.get("maze")).isEqualTo("");
        assertThat(origin.get("lease")).isEqualTo("");
        assertThat(origin.get("acl")).isEqualTo("");
        assertThat(WorldOps.aclInChunk(null, null)).isEmpty();
        world.grant(world.parcels().get(0).id(), "bob", ParcelVerb.BLOCK_PLACE);
        @SuppressWarnings("unchecked")
        Map<String, Object> granted = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "chunk.inspect", null));
        assertThat(granted.get("acl")).isEqualTo("bob block.place");
        assertThat(WorldOps.aclInChunk(world, new ChunkCoordinate(0, 0, 0)))
                .isEqualTo("bob block.place");
        assertThat(WorldOps.aclInChunk(world, new ChunkCoordinate(2, 0, 0))).isEmpty();
        assertThat(origin.get("occupants")).isEqualTo("door · trap · portal · npc");
        assertThat(origin.get("stands"))
                .isEqualTo("door 0,1,0 · trap 1,1,0 · portal 2,1,0 · npc 3,1,0");
        assertThat(WorldOps.standsInChunk(World.zero(), new ChunkCoordinate(0, 0, 0)))
                .isEqualTo("door 0,1,0 · trap 1,1,0 · portal 2,1,0 · npc 3,1,0");
        assertThat(WorldOps.standsInChunk(null, null)).isEmpty();
        @SuppressWarnings("unchecked")
        Map<String, Object> far = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(32, 0, 0), "chunk.inspect", null));
        assertThat(far.get("plots")).isEqualTo(1);
        assertThat(far.get("street")).isEqualTo(world.parcels().get(1).placeName());
        assertThat(far.get("lot")).isEqualTo("32,0");
        assertThat(far.get("maze")).isEqualTo("");
        assertThat(far.get("acl")).isEqualTo("");
        assertThat(far.get("occupants")).isEqualTo("");
        assertThat(far.get("stands")).isEqualTo("");
        World near = World.zero();
        WorldBuilder two = new WorldBuilder(near);
        two.run(new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "stamp.apply", null));
        BlockCoordinate next = StampOps.nextOrigin(
                near, new MazeGrid(1, 1), new BlockCoordinate(0, 0, 0), 1);
        two.run(new WorldBuilder.Step(next, "stamp.apply", null));
        @SuppressWarnings("unchecked")
        Map<String, Object> both = (Map<String, Object>) two.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "chunk.inspect", null));
        assertThat(both.get("plots")).isEqualTo(2);
        assertThat(both.get("street")).isEqualTo(WorldOps.streetLine(near));
        assertThat(both.get("lot")).isEqualTo(WorldOps.streetLots(near));
    }

    @Test
    void aRecipeStampsALabMazeThroughWorldOps() {
        World world = World.zero();
        WorldBuilder builder = new WorldBuilder(world);
        MazeGrid maze = new MazeGrid(3, 3);
        maze.carve(maze.cell(0, 0), Direction.EAST);
        String mazeRef = "00000000-0000-4000-8000-000000000007";
        StampResult stamped = WorldOps.asStampResult(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "stamp.apply", null, maze, mazeRef)));
        assertThat(stamped.ok()).isTrue();
        assertThat(stamped.outcome()).isEqualTo("APPLIED");
        assertThat(stamped.bounds().maxX()).isEqualTo(6);
        assertThat(stamped.bounds().maxZ()).isEqualTo(6);
        assertThat(WorldOps.boxLine(stamped.bounds())).isEqualTo("0,0,0-6,1,6");
        assertThat(WorldOps.boxAt(world, new BlockCoordinate(0, 0, 0))).isEqualTo("0,0,0-6,1,6");
        assertThat(WorldOps.boxAt(world, new BlockCoordinate(99, 0, 99))).isEmpty();
        assertThat(WorldOps.boxLine(null)).isEmpty();
        assertThat(world.parcels()).hasSize(1);
        assertThat(world.parcels().get(0).mazeRef()).isEqualTo(mazeRef);
        assertThat(world.parcels().get(0).placeName()).isIn(PlaceNames.STREETS);
        assertThat(WorldOps.lastPlaceName(world)).isEqualTo(world.parcels().get(0).placeName());
        assertThat(WorldOps.streetMazes(world)).isEqualTo(mazeRef);
        assertThat(WorldOps.streetMazes(World.zero())).isEmpty();
        assertThat(WorldOps.mazesInChunk(world, new ChunkCoordinate(0, 0, 0))).isEqualTo(mazeRef);
        assertThat(WorldOps.mazesInChunk(world, new ChunkCoordinate(4, 0, 0))).isEmpty();
        assertThat(WorldOps.mazesInChunk(null, null)).isEmpty();
        @SuppressWarnings("unchecked")
        Map<String, Object> chunkOn = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "chunk.inspect", null));
        assertThat(chunkOn.get("maze")).isEqualTo(mazeRef);
        assertThat(chunkOn.get("lease")).isEqualTo("");
        assertThat(WorldOps.leasesInChunk(world, new ChunkCoordinate(0, 0, 0))).isEmpty();
        assertThat(WorldOps.leasesInChunk(null, null)).isEmpty();
        @SuppressWarnings("unchecked")
        Map<String, Object> onLot = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "block.inspect", null));
        assertThat(onLot.get("place")).isEqualTo(world.parcels().get(0).placeName());
        assertThat(onLot.get("lot")).isEqualTo("0,0");
        assertThat(onLot.get("box")).isEqualTo("0,0,0-6,1,6");
        assertThat(onLot.get("maze")).isEqualTo(mazeRef);
        @SuppressWarnings("unchecked")
        Map<String, Object> npcOnLot = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "npc.inspect", null));
        assertThat(npcOnLot.get("box")).isEqualTo("0,0,0-6,1,6");
        assertThat(npcOnLot.get("maze")).isEqualTo(mazeRef);
        assertThat(npcOnLot.get("lease")).isEqualTo("");
        assertThat(builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "parcel.lease", null)))
                .isEqualTo(ParcelLeaseResult.LEASED);
        @SuppressWarnings("unchecked")
        Map<String, Object> npcLeased = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "npc.inspect", null));
        assertThat(npcLeased.get("lease")).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(WorldOps.lastLeaseMaze(world)).isEqualTo(mazeRef);
        assertThat(WorldOps.lastLeaseMaze(World.zero())).isEmpty();
        assertThat(WorldOps.lastLeaseMaze(null)).isEmpty();
        @SuppressWarnings("unchecked")
        Map<String, Object> chunkLeased = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "chunk.inspect", null));
        assertThat(chunkLeased.get("lease")).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(WorldOps.leasesInChunk(world, new ChunkCoordinate(0, 0, 0)))
                .isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(WorldOps.leasesInChunk(world, new ChunkCoordinate(4, 0, 0))).isEmpty();
        @SuppressWarnings("unchecked")
        Map<String, Object> doorOnLot = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "door.inspect", null));
        assertThat(doorOnLot.get("maze")).isEqualTo(mazeRef);
        @SuppressWarnings("unchecked")
        Map<String, Object> trapOnLot = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "trap.inspect", null));
        assertThat(trapOnLot.get("maze")).isEqualTo(mazeRef);
        @SuppressWarnings("unchecked")
        Map<String, Object> portalOnLot = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "portal.inspect", null));
        assertThat(portalOnLot.get("maze")).isEqualTo(mazeRef);
        @SuppressWarnings("unchecked")
        Map<String, Object> offLot = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(99, 0, 99), "block.inspect", null));
        assertThat(offLot.get("place")).isEqualTo("");
        assertThat(offLot.get("lot")).isEqualTo("");
        assertThat(offLot.get("box")).isEqualTo("");
        assertThat(offLot.get("maze")).isEqualTo("");
        Observation onObserve = Observation.take(world,
                new WorldAddress(world.id(), new BlockCoordinate(0, 0, 0)));
        assertThat(onObserve.maze()).isEqualTo(mazeRef);
        Observation offObserve = Observation.take(world,
                new WorldAddress(world.id(), new BlockCoordinate(99, 0, 99)));
        assertThat(offObserve.maze()).isEmpty();
        MazeGrid other = new MazeGrid(3, 3);
        other.carve(other.cell(0, 0), Direction.EAST);
        String mazeTwo = "00000000-0000-4000-8000-000000000008";
        BlockCoordinate nextLot = StampOps.nextOrigin(world, other, new BlockCoordinate(0, 0, 0), 1);
        assertThat(WorldOps.asStampResult(builder.run(new WorldBuilder.Step(
                nextLot, "stamp.apply", null, other, mazeTwo))).ok()).isTrue();
        assertThat(builder.run(new WorldBuilder.Step(nextLot, "parcel.lease", null)))
                .isEqualTo(ParcelLeaseResult.LEASED);
        assertThat(WorldOps.lastLeaseMaze(world)).isEqualTo(mazeTwo);
        assertThat(builder.run(new WorldBuilder.Step(nextLot, "parcel.release", null)))
                .isEqualTo(ParcelReleaseResult.RELEASED);
        assertThat(WorldOps.lastLeaseMaze(world)).isEqualTo(mazeTwo);
        assertThat(builder.run(new WorldBuilder.Step(nextLot, "parcel.release", null)))
                .isEqualTo(ParcelReleaseResult.RELEASED);
        assertThat(WorldOps.lastLeaseMaze(world)).isEmpty();
    }

    @Test
    void anInventedAgentVerbIsRejected() {
        WorldBuilder builder = new WorldBuilder(World.zero());
        assertThatThrownBy(() -> builder.run(new WorldBuilder.Step(
                new BlockCoordinate(0, 0, 0), "agent.build", BlockType.WOOD)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Unknown capability");
        assertThatThrownBy(() -> builder.run((WorldBuilder.Step) null))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Step");
        assertThatThrownBy(() -> builder.run((List<WorldBuilder.Step>) null))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Recipe");
    }
}
