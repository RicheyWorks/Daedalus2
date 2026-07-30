// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@code GET /api/v1/maze/daily} at the HTTP seam (ADR-006 idea #4). The determinism story
 * is proven in {@link com.daedalus.server.service.DailyMazeServiceTest}; here the contract
 * is the surface: the literal path must not be swallowed by {@code GET /maze/{id}}'s UUID
 * template, the response carries today's UTC date, repeat calls share one maze id, and the
 * daily maze is an ordinary maze — fetchable by id like any other. (Shared cached context.)
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class DailyMazeEndpointTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @LocalServerPort
    private int port;

    private RestTestClient client() {
        return RestTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    }

    @Test
    void theDailyIsStableWithinTheDayAndIsAnOrdinaryMaze() throws Exception {
        JsonNode first = MAPPER.readTree(client().get().uri("/api/v1/maze/daily")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());

        // "daily" must route to the literal mapping, never parse as a UUID.
        assertThat(first.get("date").asText())
                .isEqualTo(LocalDate.now(ZoneOffset.UTC).toString());
        UUID id = UUID.fromString(first.get("maze").get("id").asText());
        assertThat(first.get("maze").get("tiles").isArray()).isTrue();

        JsonNode second = MAPPER.readTree(client().get().uri("/api/v1/maze/daily")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(second.get("maze").get("id").asText())
                .as("one maze per day — shared runs and permalinks depend on it")
                .isEqualTo(id.toString());

        // And it is a first-class maze: fetchable by id like any generated one.
        client().get().uri("/api/v1/maze/" + id).exchange().expectStatus().isOk();
    }
}
