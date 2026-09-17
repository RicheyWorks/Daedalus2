// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.WorldEventFrame;
import com.daedalus.plugin.events.WorldBlockEvent;
import org.junit.jupiter.api.Test;
import org.springframework.messaging.simp.SimpMessagingTemplate;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class WorldWebSocketBridgeTest {

    @Test
    void aBlockEventIsForwardedOnTheWorldTopic() {
        SimpMessagingTemplate stomp = mock(SimpMessagingTemplate.class);
        WorldWebSocketController bridge = new WorldWebSocketController(stomp);
        WorldBlockEvent event = new WorldBlockEvent(this, "world-zero",
                WorldBlockEvent.Kind.BLOCK_PLACED, 1, 2, 3, "STONE", "AIR", 4);
        bridge.onWorldBlock(event);
        verify(stomp).convertAndSend("/topic/world/world-zero/events",
                new WorldEventFrame("world-zero", "BLOCK_PLACED", 1, 2, 3, "STONE", "AIR", 4));
    }
}
