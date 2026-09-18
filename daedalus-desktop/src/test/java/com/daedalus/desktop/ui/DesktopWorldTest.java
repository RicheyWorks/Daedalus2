// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.api.dto.WorldEventFrame;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeMetadata;
import com.daedalus.model.MazeStats;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.WorldService;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Door;
import com.daedalus.world.Parcel;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.ParcelVerb;
import com.daedalus.world.PlaceNames;
import com.daedalus.world.Trap;
import com.daedalus.world.TrapResult;
import com.daedalus.world.World;
import com.daedalus.world.auto.DriveTrace;
import com.daedalus.world.auto.WorldOps;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class DesktopWorldTest {

    @Test
    void inspectLineNamesRevisionAndLastEvent() {
        assertThat(DesktopWorld.inspectLine(null, null)).isEqualTo("world-zero · unavailable");
        assertThat(DesktopWorld.inspectLine(World.zero(), null))
                .isEqualTo("world-zero r=0 · listening · door · trap · portal · npc"
                        + " · door 0,1,0 · trap 1,1,0 · portal 2,1,0 · npc 3,1,0");
        assertThat(DesktopWorld.chunkOccupants(World.zero(), null))
                .isEqualTo("door · trap · portal · npc");
        assertThat(DesktopWorld.chunkStands(World.zero(), null))
                .isEqualTo("door 0,1,0 · trap 1,1,0 · portal 2,1,0 · npc 3,1,0");
        assertThat(DesktopWorld.chunkOccupants(null, null)).isEmpty();
        assertThat(DesktopWorld.chunkStands(null, null)).isEmpty();
        WorldEventFrame far = new WorldEventFrame(
                DesktopWorld.ID, "BLOCK_PLACED", 64, 0, 0, "STONE", "AIR", 1);
        assertThat(DesktopWorld.chunkOccupants(World.zero(), far)).isEmpty();
        assertThat(DesktopWorld.chunkStands(World.zero(), far)).isEmpty();
        assertThat(DesktopWorld.chunkDrive(World.zero(), null)).isEmpty();
        assertThat(DesktopWorld.chunkActor(World.zero(), null)).isEmpty();
        assertThat(DesktopWorld.chunkAt(World.zero(), null)).isEmpty();
        assertThat(DesktopWorld.chunkDrive(null, null)).isEmpty();
        assertThat(DesktopWorld.chunkActor(null, null)).isEmpty();
        assertThat(DesktopWorld.chunkAt(null, null)).isEmpty();
        World gated = World.zero();
        assertThat(WorldOps.drive(gated, "trap.arm", Trap.ZERO_AT, null, null, "carol"))
                .isEqualTo(TrapResult.ARMED);
        assertThat(DesktopWorld.chunkDrive(gated, null)).isEqualTo("trap.arm ARMED");
        assertThat(DesktopWorld.chunkActor(gated, null)).isEqualTo("carol");
        assertThat(DesktopWorld.chunkAt(gated, null)).isEqualTo("1,1,0");
        assertThat(DesktopWorld.chunkDrive(gated, far)).isEmpty();
        assertThat(DesktopWorld.chunkActor(gated, far)).isEmpty();
        assertThat(DesktopWorld.chunkAt(gated, far)).isEmpty();
        assertThat(DesktopWorld.inspectLine(gated, null))
                .contains("trap.arm ARMED")
                .contains("carol")
                .contains("1,1,0");
        assertThat(DesktopWorld.inspectLine(gated, far)).doesNotContain("trap.arm ARMED");
        WorldEventFrame placed = new WorldEventFrame(
                DesktopWorld.ID, "BLOCK_PLACED", 1, 2, 3, "STONE", "AIR", 4);
        assertThat(DesktopWorld.inspectLine(4, placed))
                .isEqualTo("world-zero r=4 · BLOCK_PLACED 1,2,3 STONE");
        World named = World.zero();
        named.applyStamp(new ParcelBounds(8, 0, 8, 9, 1, 9), Parcel.SYSTEM_OWNER,
                List.of(new BlockCoordinate(8, 0, 8)),
                List.of(BlockType.WOOD));
        named.nameParcel(named.parcels().get(0).id(), "Willow Walk");
        assertThat(DesktopWorld.firstPlace(named)).isEqualTo("Willow Walk");
        assertThat(DesktopWorld.lastBox(named)).isEqualTo("8,0,8-9,1,9");
        assertThat(DesktopWorld.inspectLine(named, null))
                .isEqualTo("world-zero r=" + named.revision().value()
                        + " · Willow Walk · 8,0,8-9,1,9 · listening · door · trap · portal · npc"
                        + " · door 0,1,0 · trap 1,1,0 · portal 2,1,0 · npc 3,1,0");
        assertThat(DesktopWorld.inspectLine(named.revision().value(), "Willow Walk", placed))
                .isEqualTo("world-zero r=" + named.revision().value()
                        + " · Willow Walk · BLOCK_PLACED 1,2,3 STONE");
        assertThat(DesktopWorld.ID).isEqualTo("world-zero");
        assertThat(DesktopWorld.PLACE_INK).isEqualTo("#94612e");
        assertThat(DesktopWorld.PLACE_CLASS).isEqualTo("world-place");
        assertThat(DesktopWorld.firstPlace(World.zero())).isEmpty();
        assertThat(DesktopWorld.lastBox(World.zero())).isEmpty();
        assertThat(DesktopWorld.streetBoxes(World.zero())).isEmpty();
        named.leaseParcel(named.parcels().get(0).id(), Parcel.SYSTEM_TENANT);
        assertThat(DesktopWorld.firstLease(named)).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(DesktopWorld.inspectLine(named, null))
                .isEqualTo("world-zero r=" + named.revision().value()
                        + " · Willow Walk · " + Parcel.SYSTEM_TENANT
                        + " · 8,0,8-9,1,9 · listening · door · trap · portal · npc"
                        + " · door 0,1,0 · trap 1,1,0 · portal 2,1,0 · npc 3,1,0");
        assertThat(DesktopWorld.firstLease(World.zero())).isEmpty();
        assertThat(DesktopWorld.streetLeases(World.zero())).isEmpty();
        assertThat(DesktopWorld.streetLeases(named)).isEqualTo(Parcel.SYSTEM_TENANT);
        named.bindMaze(named.parcels().get(0).id(), "00000000-0000-4000-8000-000000000007");
        assertThat(DesktopWorld.firstMaze(named))
                .isEqualTo("00000000-0000-4000-8000-000000000007");
        assertThat(DesktopWorld.inspectLine(named, null))
                .contains("00000000-0000-4000-8000-000000000007");
        assertThat(DesktopWorld.firstMaze(World.zero())).isEmpty();
        WorldEventFrame onLot = new WorldEventFrame(
                DesktopWorld.ID, "BLOCK_PLACED", 8, 0, 8, "WOOD", "AIR",
                named.revision().value());
        assertThat(DesktopWorld.eventLot(named, onLot)).isEqualTo("Willow Walk 8,8");
        assertThat(DesktopWorld.eventLot(named, placed)).isEmpty();
        assertThat(DesktopWorld.eventLot(null, onLot)).isEmpty();
        WorldEventFrame onDoor = new WorldEventFrame(
                DesktopWorld.ID, "BLOCK_PLACED", Door.ZERO_AT.x(), Door.ZERO_AT.y(),
                Door.ZERO_AT.z(), "STONE", "AIR", 1);
        assertThat(DesktopWorld.eventLot(World.zero(), onDoor)).isEqualTo("door");
        assertThat(DesktopWorld.inspectLine(World.zero(), onDoor)).contains("door");
        assertThat(DesktopWorld.inspectLine(named, onLot))
                .contains("BLOCK_PLACED 8,0,8 WOOD")
                .contains("Willow Walk 8,8");
        assertThat(DesktopWorld.occupancyLine(World.zero())).isEmpty();
        assertThat(DesktopWorld.occupancyLine(named)).isEmpty();
        World onOrigin = World.zero();
        WorldOps.drive(onOrigin, "stamp.apply", new BlockCoordinate(0, 0, 0), null);
        assertThat(DesktopWorld.occupancyLine(onOrigin))
                .contains("door")
                .contains("trap")
                .contains("portal")
                .contains("0,0")
                .doesNotContain("npc");
        assertThat(DesktopWorld.inspectLine(onOrigin, null))
                .contains("door")
                .contains("0,0")
                .doesNotContain("npc");
        WorldEventFrame onStamp = new WorldEventFrame(
                DesktopWorld.ID, "BLOCK_PLACED", 0, 0, 0, "WOOD", "AIR",
                onOrigin.revision().value());
        assertThat(DesktopWorld.eventDrive(onOrigin, onStamp)).isEqualTo("stamp.apply APPLIED");
        assertThat(DesktopWorld.eventActor(onOrigin, onStamp)).isEqualTo("system");
        assertThat(DesktopWorld.eventAt(onOrigin, onStamp)).isEqualTo("0,0,0");
        assertThat(DesktopWorld.eventDrive(onOrigin, far)).isEmpty();
        assertThat(DesktopWorld.eventActor(null, onStamp)).isEmpty();
        assertThat(DesktopWorld.eventAt(onOrigin, null)).isEmpty();
        assertThat(DesktopWorld.inspectLine(onOrigin, onStamp))
                .contains("stamp.apply APPLIED")
                .contains("system")
                .contains("0,0,0");
        onOrigin.grant(onOrigin.parcels().get(0).id(), "bob", ParcelVerb.BLOCK_PLACE);
        assertThat(DesktopWorld.aclLine(onOrigin)).isEqualTo("bob block.place");
        assertThat(DesktopWorld.aclLine(World.zero())).isEmpty();
        assertThat(DesktopWorld.aclLine(null)).isEmpty();
        assertThat(DesktopWorld.inspectLine(onOrigin, null)).contains("bob block.place");
        DriveTrace.Step denied = new DriveTrace.Step("npc.talk", "DENIED", 1);
        assertThat(DesktopWorld.driveLine(denied)).isEqualTo("npc.talk DENIED");
        assertThat(DesktopWorld.driveLine(null)).isEmpty();
        assertThat(DesktopWorld.inspectLine(onOrigin, null, denied)).contains("npc.talk DENIED");
        assertThat(DesktopWorld.actorLine(onOrigin)).isEqualTo("system");
        assertThat(DesktopWorld.actorLine(World.zero())).isEmpty();
        assertThat(DesktopWorld.actorLine(null)).isEmpty();
        assertThat(WorldOps.drive(onOrigin, "trap.arm", Trap.ZERO_AT, null, null, "carol"))
                .isEqualTo(TrapResult.DENIED);
        assertThat(DesktopWorld.actorLine(onOrigin)).isEqualTo("carol");
        assertThat(DesktopWorld.atLine(onOrigin)).isEqualTo("1,1,0");
        assertThat(DesktopWorld.atLine(World.zero())).isEmpty();
        assertThat(DesktopWorld.atLine(null)).isEmpty();
        assertThat(DesktopWorld.inspectLine(onOrigin, null, denied))
                .contains("npc.talk DENIED")
                .contains("carol")
                .contains("1,1,0");
        assertThat(DesktopWorld.inspectLine(onOrigin, null, null))
                .startsWith(DesktopWorld.inspectLine(onOrigin, null))
                .contains("carol")
                .contains("1,1,0");
    }

    @Test
    void statusBarCarriesAWorldLineBesideMazeStatus() throws Exception {
        try (InputStream in = getClass().getResourceAsStream("/ui/main.fxml")) {
            assertThat(in).as("desktop shell").isNotNull();
            String fxml = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(fxml).contains("fx:id=\"worldLabel\"")
                    .contains("fx:id=\"statusLabel\"")
                    .contains("fx:id=\"generateButton\"")
                    .contains("fx:id=\"solveButton\"");
        }
        try (InputStream cssIn = getClass().getResourceAsStream("/ui/cosmic.css")) {
            assertThat(cssIn).as("desktop cosmic shell").isNotNull();
            String css = new String(cssIn.readAllBytes(), StandardCharsets.UTF_8);
            assertThat(css).contains(".status-bar .label.world-place")
                    .contains(DesktopWorld.PLACE_INK);
        }
    }

    @Test
    void generateProjectsTheLabMaze(@TempDir Path tmp) {
        WorldService worlds = new WorldService(tmp.resolve("world-zero.daew"));
        MazeGrid maze = new MazeGrid(3, 3);
        maze.carve(maze.cell(0, 0), Direction.EAST);
        MazeGenerationService.Cached cached = new MazeGenerationService.Cached(
                MazeMetadata.of(3, 3, 7L, "test", maze.start(), maze.goal()),
                maze, new MazeStats());
        assertThat(DesktopWorld.projectLab(null, cached)).isNull();
        assertThat(DesktopWorld.projectLab(worlds, null)).isNull();
        assertThat(DesktopWorld.projectLab(worlds, cached).ok()).isTrue();
        World live = worlds.inspect(DesktopWorld.ID);
        assertThat(DesktopWorld.firstMaze(live)).isEqualTo(cached.metadata().id().toString());
        assertThat(DesktopWorld.lastLease(live)).isEqualTo(Parcel.SYSTEM_TENANT);
        MazeGenerationService.Cached second = new MazeGenerationService.Cached(
                MazeMetadata.of(3, 3, 8L, "test", maze.start(), maze.goal()),
                maze, new MazeStats());
        assertThat(DesktopWorld.projectLab(worlds, second).ok()).isTrue();
        World two = worlds.inspect(DesktopWorld.ID);
        assertThat(two.parcels()).hasSize(2);
        assertThat(DesktopWorld.firstMaze(two)).isEqualTo(cached.metadata().id().toString());
        assertThat(DesktopWorld.lastMaze(two)).isEqualTo(second.metadata().id().toString());
        assertThat(DesktopWorld.streetMazes(two))
                .isEqualTo(cached.metadata().id() + " · " + second.metadata().id());
        assertThat(two.parcels().get(0).leaseId()).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(two.parcels().get(1).leaseId()).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(DesktopWorld.streetLeases(two))
                .isEqualTo(Parcel.SYSTEM_TENANT + " · " + Parcel.SYSTEM_TENANT);
        assertThat(DesktopWorld.firstPlace(two)).isIn(PlaceNames.STREETS);
        assertThat(DesktopWorld.lastPlace(two)).isIn(PlaceNames.STREETS);
        assertThat(DesktopWorld.lastPlace(two)).isNotEqualTo(DesktopWorld.firstPlace(two));
        assertThat(DesktopWorld.streetLine(two))
                .isEqualTo(DesktopWorld.firstPlace(two) + " · " + DesktopWorld.lastPlace(two));
        assertThat(DesktopWorld.lastLot(two)).isEqualTo("8,0");
        assertThat(DesktopWorld.streetLots(two)).isEqualTo("0,0 · 8,0");
        assertThat(DesktopWorld.lastBox(two)).isEqualTo("8,0,0-14,1,6");
        assertThat(DesktopWorld.streetBoxes(two)).isEqualTo("0,0,0-6,1,6 · 8,0,0-14,1,6");
        assertThat(DesktopWorld.inspectLine(two, null))
                .contains("2 plots")
                .contains(cached.metadata().id().toString())
                .contains(second.metadata().id().toString())
                .contains(DesktopWorld.firstPlace(two))
                .contains(DesktopWorld.lastPlace(two))
                .contains("0,0")
                .contains("8,0")
                .contains("0,0,0-6,1,6")
                .contains("8,0,0-14,1,6")
                .contains(Parcel.SYSTEM_TENANT + " · " + Parcel.SYSTEM_TENANT);
    }
}
