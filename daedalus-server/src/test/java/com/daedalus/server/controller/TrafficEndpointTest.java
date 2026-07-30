// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.TrafficFrame;
import com.daedalus.plugin.events.TrafficPulseEvent;
import com.daedalus.engine.MazeGrid;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

/**
 * {@code POST /api/v1/maze/{id}/traffic} at the HTTP seam, plus the event→STOMP bridge for
 * traffic pulses. The congestion mechanics are proven in
 * {@link com.daedalus.server.service.TrafficServiceTest}. (Shared cached context; the
 * tracker this test enables retires itself after the quiet-tick window.)
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class TrafficEndpointTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @LocalServerPort
    private int port;

    private RestTestClient client() {
        return RestTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    }

    @Test
    void enablingTrafficIsIdempotentAndUnknownMazesAnswer404() throws Exception {
        client().post().uri("/api/v1/maze/" + UUID.randomUUID() + "/traffic")
                .exchange().expectStatus().isNotFound();

        JsonNode maze = MAPPER.readTree(client().post().uri("/api/v1/maze/generate")
                .header("Content-Type", "application/json")
                .body("{\"generatorId\":\"recursive-backtracker\",\"rows\":7,\"cols\":7,\"seed\":3}")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        String id = maze.get("id").asText();

        JsonNode first = MAPPER.readTree(client().post().uri("/api/v1/maze/" + id + "/traffic")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(first.get("active").asBoolean()).isTrue();
        assertThat(first.get("tickMillis").asLong()).isGreaterThan(0);

        JsonNode second = MAPPER.readTree(client().post().uri("/api/v1/maze/" + id + "/traffic")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(second.get("active").asBoolean()).isTrue();
    }

    @Test
    void aTrafficPulseIsForwardedAsATrafficFrameOnTheStateTopic() {
        SimpMessagingTemplate stomp = mock(SimpMessagingTemplate.class);
        MazeWebSocketController bridge = new MazeWebSocketController(stomp);
        UUID mazeId = UUID.randomUUID();

        bridge.onTrafficPulse(new TrafficPulseEvent(this, mazeId, 7, 42.5, false,
                new MazeGrid(3, 3)));

        verify(stomp).convertAndSend("/topic/maze/" + mazeId + "/state",
                new TrafficFrame(mazeId, 7, 42.5, false));
    }
}
