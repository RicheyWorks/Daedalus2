package com.daedalus.controller;

import com.daedalus.model.Point;
import com.daedalus.plugin.events.MazeGeneratedEvent;
import com.daedalus.plugin.events.MazeSolvedEvent;
import com.daedalus.plugin.events.PlayerMovedEvent;
import org.springframework.context.event.EventListener;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Controller;

import java.util.UUID;

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

    public record GeneratedFrame(UUID mazeId, int rows, int cols, String generatorId) {}
    public record SolvedFrame(UUID mazeId, String solverId, int pathLength, boolean success) {}
    public record MoveFrame(UUID sessionId, Point from, Point to) {}

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
}
