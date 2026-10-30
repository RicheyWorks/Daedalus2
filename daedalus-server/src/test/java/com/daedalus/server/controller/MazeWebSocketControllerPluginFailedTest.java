// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.PluginFailedFrame;
import com.daedalus.plugin.events.PluginFailedEvent;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.messaging.simp.SimpMessagingTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

/**
 * Locks in the STOMP bridge for {@link PluginFailedEvent} — when a plugin fails to load,
 * progress through its lifecycle, or stop cleanly, the failure must be relayed to the
 * UI's {@code /topic/plugins/failures} channel as a JSON-friendly frame.
 */
class MazeWebSocketControllerPluginFailedTest {

    @Test
    void onPluginFailed_relaysToStompTopic_withFlattenedFrame() {
        SimpMessagingTemplate stomp = mock(SimpMessagingTemplate.class);
        MazeWebSocketController controller = new MazeWebSocketController(stomp);

        Throwable cause = new IllegalStateException("registry refused new generator");
        PluginFailedEvent event = new PluginFailedEvent(
                this, "biome-pack", "0.4.2",
                PluginFailedEvent.Phase.REGISTER_ALGORITHMS, cause);

        controller.onPluginFailed(event);

        ArgumentCaptor<String> topic = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<Object> payload = ArgumentCaptor.forClass(Object.class);
        verify(stomp).convertAndSend(topic.capture(), payload.capture());

        assertThat(topic.getValue()).isEqualTo("/topic/plugins/failures");
        assertThat(payload.getValue())
                .isInstanceOf(PluginFailedFrame.class);

        PluginFailedFrame frame = (PluginFailedFrame) payload.getValue();
        assertThat(frame.pluginId()).isEqualTo("biome-pack");
        assertThat(frame.pluginVersion()).isEqualTo("0.4.2");
        assertThat(frame.phase()).isEqualTo("REGISTER_ALGORITHMS");
        assertThat(frame.errorClass()).isEqualTo(IllegalStateException.class.getName());
        assertThat(frame.errorMessage()).isEqualTo("registry refused new generator");
        assertThat(frame.timestamp()).isPositive();
    }
}
