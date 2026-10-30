// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@code POST /api/v1/maze/{id}/live} (ADR-006) at the HTTP seam: status codes, validation,
 * and the idempotence contract. The erosion mechanics themselves are proven in
 * {@link com.daedalus.server.service.LivingMazeServiceTest}; here the contract is the
 * surface — 404 for unknown mazes, 400 for out-of-range ticks, and one run per maze no
 * matter how many times the button is mashed. (Uses the shared cached context; the runs
 * this test starts are bounded to two slow ticks and self-terminate.)
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class LivingMazeEndpointTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @LocalServerPort
    private int port;

    private RestTestClient client() {
        return RestTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    }

    @Test
    void anUnknownMazeCannotBeBroughtToLife() {
        client().post().uri("/api/v1/maze/" + UUID.randomUUID() + "/live")
                .exchange().expectStatus().isNotFound();
    }

    @Test
    void tickCountIsValidatedAtTheSurface() throws Exception {
        UUID id = generate();
        client().post().uri("/api/v1/maze/" + id + "/live?ticks=0")
                .exchange().expectStatus().isBadRequest();
        client().post().uri("/api/v1/maze/" + id + "/live?ticks=100000")
                .exchange().expectStatus().isBadRequest();
    }

    @Test
    void sealFactorIsValidatedAtTheSurface() throws Exception {
        UUID id = generate();
        client().post().uri("/api/v1/maze/" + id + "/live?ticks=2&seal=-0.1")
                .exchange().expectStatus().isBadRequest();
        client().post().uri("/api/v1/maze/" + id + "/live?ticks=2&seal=1.1")
                .exchange().expectStatus().isBadRequest();
        client().post().uri("/api/v1/maze/" + id + "/live?ticks=2&seal=0.5&seed=3")
                .exchange().expectStatus().isOk();
    }

    @Test
    void bringingAMazeToLifeStartsOneBoundedIdempotentRun() throws Exception {
        UUID id = generate();

        JsonNode first = MAPPER.readTree(client()
                .post().uri("/api/v1/maze/" + id + "/live?ticks=2&seed=7")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(first.get("active").asBoolean()).isTrue();
        assertThat(first.get("ticksRequested").asInt()).isEqualTo(2);
        assertThat(first.get("tickMillis").asLong())
                .as("clients without STOMP poll at this honest interval")
                .isGreaterThan(0);

        // Mashing the button joins the existing run — never a second ticker on one grid.
        JsonNode second = MAPPER.readTree(client()
                .post().uri("/api/v1/maze/" + id + "/live?ticks=99&seed=7")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(second.get("ticksRequested").asInt()).isEqualTo(2);
    }

    private UUID generate() throws Exception {
        JsonNode maze = MAPPER.readTree(client().post().uri("/api/v1/maze/generate")
                .header("Content-Type", "application/json")
                .body("{\"generatorId\":\"recursive-backtracker\",\"rows\":9,\"cols\":9,\"seed\":4}")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        return UUID.fromString(maze.get("id").asText());
    }
}
