// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.WorldEventFrame;
import com.daedalus.plugin.events.WorldBlockEvent;
import org.springframework.context.event.EventListener;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Controller;

/**
 * World events on their own topic. Maze {@code /state} frames stay maze-shaped.
 */
@Controller
public class WorldWebSocketController {

    private final SimpMessagingTemplate stomp;

    public WorldWebSocketController(SimpMessagingTemplate stomp) {
        this.stomp = stomp;
    }

    @EventListener
    public void onWorldBlock(WorldBlockEvent e) {
        stomp.convertAndSend("/topic/world/" + e.worldId() + "/events",
                new WorldEventFrame(e.worldId(), e.kind().name(),
                        e.x(), e.y(), e.z(), e.type(), e.previous(), e.revision()));
    }
}
