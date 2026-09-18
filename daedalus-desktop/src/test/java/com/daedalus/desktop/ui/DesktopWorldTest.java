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
import com.daedalus.world.Parcel;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.PlaceNames;
import com.daedalus.world.World;
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
                .isEqualTo("world-zero r=0 · listening · door · trap · portal · npc");
        assertThat(DesktopWorld.chunkOccupants(World.zero(), null))
                .isEqualTo("door · trap · portal · npc");
        assertThat(DesktopWorld.chunkOccupants(null, null)).isEmpty();
        WorldEventFrame far = new WorldEventFrame(
                DesktopWorld.ID, "BLOCK_PLACED", 64, 0, 0, "STONE", "AIR", 1);
        assertThat(DesktopWorld.chunkOccupants(World.zero(), far)).isEmpty();
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
        assertThat(DesktopWorld.inspectLine(named, null))
                .isEqualTo("world-zero r=" + named.revision().value()
                        + " · Willow Walk · listening · door · trap · portal · npc");
        assertThat(DesktopWorld.inspectLine(named.revision().value(), "Willow Walk", placed))
                .isEqualTo("world-zero r=" + named.revision().value()
                        + " · Willow Walk · BLOCK_PLACED 1,2,3 STONE");
        assertThat(DesktopWorld.ID).isEqualTo("world-zero");
        assertThat(DesktopWorld.PLACE_INK).isEqualTo("#94612e");
        assertThat(DesktopWorld.PLACE_CLASS).isEqualTo("world-place");
        assertThat(DesktopWorld.firstPlace(World.zero())).isEmpty();
        named.leaseParcel(named.parcels().get(0).id(), Parcel.SYSTEM_TENANT);
        assertThat(DesktopWorld.firstLease(named)).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(DesktopWorld.inspectLine(named, null))
                .isEqualTo("world-zero r=" + named.revision().value()
                        + " · Willow Walk · " + Parcel.SYSTEM_TENANT
                        + " · listening · door · trap · portal · npc");
        assertThat(DesktopWorld.firstLease(World.zero())).isEmpty();
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
        assertThat(DesktopWorld.firstPlace(two)).isIn(PlaceNames.STREETS);
        assertThat(DesktopWorld.lastPlace(two)).isIn(PlaceNames.STREETS);
        assertThat(DesktopWorld.lastPlace(two)).isNotEqualTo(DesktopWorld.firstPlace(two));
        assertThat(DesktopWorld.streetLine(two))
                .isEqualTo(DesktopWorld.firstPlace(two) + " · " + DesktopWorld.lastPlace(two));
        assertThat(DesktopWorld.lastLot(two)).isEqualTo("8,0");
        assertThat(DesktopWorld.streetLots(two)).isEqualTo("0,0 · 8,0");
        assertThat(DesktopWorld.inspectLine(two, null))
                .contains("2 plots")
                .contains(cached.metadata().id().toString())
                .contains(second.metadata().id().toString())
                .contains(DesktopWorld.firstPlace(two))
                .contains(DesktopWorld.lastPlace(two))
                .contains("0,0")
                .contains("8,0");
    }
}
