// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.MutationFrame;
import com.daedalus.engine.MazeGrid;
import com.daedalus.plugin.events.MazeMutatedEvent;
import org.junit.jupiter.api.Test;
import org.springframework.messaging.simp.SimpMessagingTemplate;

import java.util.UUID;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

/**
 * The event→STOMP bridge for living mazes (ADR-006): a {@link MazeMutatedEvent} must reach
 * {@code /topic/maze/{id}/state} as a {@link MutationFrame} carrying deltas only (clients
 * re-fetch the grid). Without the listener the whole feature mutates silently — the UI
 * would keep drawing a maze that no longer exists.
 */
class MazeWebSocketMutationBridgeTest {

    @Test
    void aMutationEventIsForwardedAsAMutationFrameOnTheStateTopic() {
        SimpMessagingTemplate stomp = mock(SimpMessagingTemplate.class);
        MazeWebSocketController bridge = new MazeWebSocketController(stomp);
        UUID mazeId = UUID.randomUUID();

        bridge.onMutated(new MazeMutatedEvent(this, mazeId, 4, 3, 12, false,
                new MazeGrid(5, 5)));

        verify(stomp).convertAndSend("/topic/maze/" + mazeId + "/state",
                new MutationFrame(mazeId, 4, 3, 0, 12, false));
    }
}
