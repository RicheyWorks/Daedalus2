// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.GeneratedFrame;
import com.daedalus.api.dto.MoveFrame;
import com.daedalus.api.dto.PluginFailedFrame;
import com.daedalus.api.dto.SolvedFrame;
import com.daedalus.plugin.events.MazeGeneratedEvent;
import com.daedalus.plugin.events.MazeSolvedEvent;
import com.daedalus.plugin.events.PlayerMovedEvent;
import com.daedalus.plugin.events.PluginFailedEvent;
import org.springframework.context.event.EventListener;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Controller;

/**
 * WebSocket bridge. Subscribes to internal Spring events and re-publishes them on STOMP topics
 * so the front end (or any external dashboard) receives live updates.
 */
@Controller
public class MazeWebSocketController {

    private final SimpMessagingTemplate stomp;

    public MazeWebSocketController(SimpMessagingTemplate stomp) {
        this.stomp = stomp;
    }

    @EventListener
    public void onGenerated(MazeGeneratedEvent e) {
        var m = e.metadata();
        stomp.convertAndSend("/topic/maze/" + m.id() + "/state",
                new GeneratedFrame(m.id(), m.rows(), m.cols(), m.generatorId()));
    }

    @EventListener
    public void onSolved(MazeSolvedEvent e) {
        stomp.convertAndSend("/topic/maze/" + e.mazeId() + "/solver",
                new SolvedFrame(e.mazeId(), e.solverId(), e.path().size(), e.stats().success()));
    }

    @EventListener
    public void onMove(PlayerMovedEvent e) {
        stomp.convertAndSend("/topic/session/" + e.sessionId() + "/player",
                new MoveFrame(e.sessionId(), e.from(), e.to()));
    }

    /**
     * Forward plugin failures to a single STOMP topic so the UI can surface them as toast
     * notifications, banner alerts, or whatever the front-end prefers. Operators no longer
     * have to grep server logs to discover that a plugin crashed during boot.
     */
    @EventListener
    public void onPluginFailed(PluginFailedEvent e) {
        stomp.convertAndSend("/topic/plugins/failures",
                new PluginFailedFrame(
                        e.pluginId(),
                        e.pluginVersion(),
                        e.phase().name(),
                        e.errorClass(),
                        e.errorMessage(),
                        e.getTimestamp()));
    }
}
