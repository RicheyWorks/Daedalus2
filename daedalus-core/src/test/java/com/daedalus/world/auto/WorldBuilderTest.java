// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Door;
import com.daedalus.world.Npc;
import com.daedalus.world.Parcel;
import com.daedalus.world.ParcelLeaseResult;
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
        assertThat(builder.run(new WorldBuilder.Step(next, "parcel.lease", null)))
                .isEqualTo(ParcelLeaseResult.LEASED);
        assertThat(world.parcels().get(0).leaseId()).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(builder.run(new WorldBuilder.Step(next, "parcel.lease", null)))
                .isEqualTo(ParcelLeaseResult.LEASED);
        assertThat(world.parcels().get(1).leaseId()).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(WorldOps.lastLeaseId(world)).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(builder.run(new WorldBuilder.Step(next, "parcel.lease", null)))
                .isEqualTo(ParcelLeaseResult.ALREADY_LEASED);
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
        @SuppressWarnings("unchecked")
        Map<String, Object> trap = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "trap.inspect", null));
        assertThat(trap.get("place")).isEqualTo(place);
        assertThat(trap.get("lot")).isEqualTo("0,0");
        @SuppressWarnings("unchecked")
        Map<String, Object> portal = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "portal.inspect", null));
        assertThat(portal.get("place")).isEqualTo(place);
        assertThat(portal.get("lot")).isEqualTo("0,0");
        @SuppressWarnings("unchecked")
        Map<String, Object> npc = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "npc.inspect", null));
        assertThat(npc.get("place")).isEqualTo("");
        assertThat(npc.get("lot")).isEqualTo("");
        @SuppressWarnings("unchecked")
        Map<String, Object> onDoor = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(Door.ZERO_AT, "block.inspect", null));
        assertThat(onDoor.get("occupant")).isEqualTo("door");
        @SuppressWarnings("unchecked")
        Map<String, Object> onNpc = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(Npc.ZERO_AT, "block.inspect", null));
        assertThat(onNpc.get("occupant")).isEqualTo("npc");
        @SuppressWarnings("unchecked")
        Map<String, Object> empty = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(9, 0, 9), "block.inspect", null));
        assertThat(empty.get("occupant")).isEqualTo("");
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
        assertThat(origin.get("occupants")).isEqualTo("door · trap · portal · npc");
        @SuppressWarnings("unchecked")
        Map<String, Object> far = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(32, 0, 0), "chunk.inspect", null));
        assertThat(far.get("plots")).isEqualTo(1);
        assertThat(far.get("street")).isEqualTo(world.parcels().get(1).placeName());
        assertThat(far.get("lot")).isEqualTo("32,0");
        assertThat(far.get("occupants")).isEqualTo("");
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
        assertThat(world.parcels()).hasSize(1);
        assertThat(world.parcels().get(0).mazeRef()).isEqualTo(mazeRef);
        assertThat(world.parcels().get(0).placeName()).isIn(PlaceNames.STREETS);
        assertThat(WorldOps.lastPlaceName(world)).isEqualTo(world.parcels().get(0).placeName());
        assertThat(WorldOps.streetMazes(world)).isEqualTo(mazeRef);
        assertThat(WorldOps.streetMazes(World.zero())).isEmpty();
        @SuppressWarnings("unchecked")
        Map<String, Object> onLot = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(0, 0, 0), "block.inspect", null));
        assertThat(onLot.get("place")).isEqualTo(world.parcels().get(0).placeName());
        assertThat(onLot.get("lot")).isEqualTo("0,0");
        assertThat(onLot.get("maze")).isEqualTo(mazeRef);
        @SuppressWarnings("unchecked")
        Map<String, Object> offLot = (Map<String, Object>) builder.run(
                new WorldBuilder.Step(new BlockCoordinate(99, 0, 99), "block.inspect", null));
        assertThat(offLot.get("place")).isEqualTo("");
        assertThat(offLot.get("lot")).isEqualTo("");
        assertThat(offLot.get("maze")).isEqualTo("");
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
