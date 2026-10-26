// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.WorldEventFrame;
import com.daedalus.engine.MazeGrid;
import com.daedalus.plugin.events.WorldBlockEvent;
import com.daedalus.server.service.WorldService;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.Door;
import com.daedalus.world.Parcel;
import com.daedalus.world.PlaceNames;
import com.daedalus.world.WorldId;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.ArgumentCaptor;
import org.springframework.messaging.simp.SimpMessagingTemplate;

import java.nio.file.Path;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class WorldWebSocketBridgeTest {

    @Test
    void aBlockEventIsForwardedOnTheWorldTopic() {
        SimpMessagingTemplate stomp = mock(SimpMessagingTemplate.class);
        WorldWebSocketController bridge = new WorldWebSocketController(stomp, null);
        WorldBlockEvent event = new WorldBlockEvent(this, "world-zero",
                WorldBlockEvent.Kind.BLOCK_PLACED, 1, 2, 3, "STONE", "AIR", 4);
        bridge.onWorldBlock(event);
        verify(stomp).convertAndSend("/topic/world/world-zero/events",
                new WorldEventFrame("world-zero", "BLOCK_PLACED", 1, 2, 3, "STONE", "AIR", 4));
    }

    @Test
    void aBlockOnASlabCarriesPlaceAndLot(@TempDir Path tmp) {
        SimpMessagingTemplate stomp = mock(SimpMessagingTemplate.class);
        WorldService worlds = new WorldService(tmp.resolve("ws-lot.daew"));
        worlds.stamp(WorldId.ZERO.value(), new BlockCoordinate(0, 0, 0), new MazeGrid(1, 1),
                UUID.fromString("00000000-0000-4000-8000-000000000007"));
        WorldWebSocketController bridge = new WorldWebSocketController(stomp, worlds);
        WorldBlockEvent event = new WorldBlockEvent(this, "world-zero",
                WorldBlockEvent.Kind.BLOCK_PLACED, 0, 0, 0, "STONE", "AIR", 2);
        ArgumentCaptor<WorldEventFrame> cap = ArgumentCaptor.forClass(WorldEventFrame.class);
        bridge.onWorldBlock(event);
        verify(stomp).convertAndSend(eq("/topic/world/world-zero/events"), cap.capture());
        assertThat(cap.getValue().lot()).isEqualTo("0,0");
        assertThat(cap.getValue().box()).isEqualTo("0,0,0-2,1,2");
        assertThat(cap.getValue().maze()).isEqualTo("00000000-0000-4000-8000-000000000007");
        assertThat(cap.getValue().lease()).isEmpty();
        assertThat(cap.getValue().acl()).isEmpty();
        assertThat(cap.getValue().place()).isIn(PlaceNames.STREETS);
        assertThat(cap.getValue().occupant()).isEmpty();
        assertThat(cap.getValue().drive()).isEqualTo("stamp.apply APPLIED");
        assertThat(cap.getValue().driveActor()).isEqualTo("system");
        assertThat(cap.getValue().driveAt()).isEqualTo("0,0,0");
    }

    @Test
    void aBlockOnARentedSlabCarriesLease(@TempDir Path tmp) {
        SimpMessagingTemplate stomp = mock(SimpMessagingTemplate.class);
        WorldService worlds = new WorldService(tmp.resolve("ws-lease.daew"));
        worlds.stamp(WorldId.ZERO.value(), new BlockCoordinate(0, 0, 0), new MazeGrid(1, 1),
                UUID.fromString("00000000-0000-4000-8000-000000000007"));
        worlds.leaseParcel(WorldId.ZERO.value());
        WorldWebSocketController bridge = new WorldWebSocketController(stomp, worlds);
        WorldBlockEvent event = new WorldBlockEvent(this, "world-zero",
                WorldBlockEvent.Kind.BLOCK_PLACED, 0, 0, 0, "STONE", "AIR", 3);
        ArgumentCaptor<WorldEventFrame> cap = ArgumentCaptor.forClass(WorldEventFrame.class);
        bridge.onWorldBlock(event);
        verify(stomp).convertAndSend(eq("/topic/world/world-zero/events"), cap.capture());
        assertThat(cap.getValue().lease()).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(cap.getValue().acl()).isEmpty();
    }

    @Test
    void aBlockOnAGrantedSlabCarriesAcl(@TempDir Path tmp) {
        SimpMessagingTemplate stomp = mock(SimpMessagingTemplate.class);
        WorldService worlds = new WorldService(tmp.resolve("ws-acl.daew"));
        worlds.stamp(WorldId.ZERO.value(), new BlockCoordinate(0, 0, 0), new MazeGrid(1, 1),
                UUID.fromString("00000000-0000-4000-8000-000000000007"));
        worlds.grantParcel(WorldId.ZERO.value(), new BlockCoordinate(0, 0, 0), "bob",
                "block.place");
        WorldWebSocketController bridge = new WorldWebSocketController(stomp, worlds);
        WorldBlockEvent event = new WorldBlockEvent(this, "world-zero",
                WorldBlockEvent.Kind.BLOCK_PLACED, 0, 0, 0, "STONE", "AIR", 3);
        ArgumentCaptor<WorldEventFrame> cap = ArgumentCaptor.forClass(WorldEventFrame.class);
        bridge.onWorldBlock(event);
        verify(stomp).convertAndSend(eq("/topic/world/world-zero/events"), cap.capture());
        assertThat(cap.getValue().acl()).isEqualTo("bob block.place");
    }

    @Test
    void aBlockOnTheDoorCellCarriesOccupant(@TempDir Path tmp) {
        SimpMessagingTemplate stomp = mock(SimpMessagingTemplate.class);
        WorldWebSocketController bridge = new WorldWebSocketController(stomp,
                new WorldService(tmp.resolve("ws-door.daew")));
        WorldBlockEvent event = new WorldBlockEvent(this, "world-zero",
                WorldBlockEvent.Kind.BLOCK_PLACED, Door.ZERO_AT.x(), Door.ZERO_AT.y(),
                Door.ZERO_AT.z(), "STONE", "AIR", 1);
        ArgumentCaptor<WorldEventFrame> cap = ArgumentCaptor.forClass(WorldEventFrame.class);
        bridge.onWorldBlock(event);
        verify(stomp).convertAndSend(eq("/topic/world/world-zero/events"), cap.capture());
        assertThat(cap.getValue().occupant()).isEqualTo("door");
        assertThat(cap.getValue().box()).isEmpty();
        assertThat(cap.getValue().maze()).isEmpty();
        assertThat(cap.getValue().lease()).isEmpty();
        assertThat(cap.getValue().acl()).isEmpty();
        assertThat(cap.getValue().drive()).isEmpty();
        assertThat(cap.getValue().driveActor()).isEmpty();
        assertThat(cap.getValue().driveAt()).isEmpty();
    }
}
