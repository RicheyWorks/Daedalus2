// SPDX-License-Identifier: MIT

package com.daedalus.server.actuate;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@code /actuator/algorithms} over a real context — proves the endpoint is registered with
 * actuator (a {@code @Component} that Boot ignores looks identical in a unit test) and that
 * the registries it reports are the wired ones. Doubles as the registration proof for
 * {@code ChaosGenerator}: if the new built-in is missing from {@code AlgorithmConfig}, the
 * generator list here won't contain it. Same context config as the other smoke tests, so the
 * cached context is reused.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class AlgorithmsEndpointTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    @LocalServerPort
    private int port;

    @Test
    void reportsTheLiveRegistriesIncludingTheNewestBuiltIn() throws Exception {
        RestTestClient client = RestTestClient.bindToServer()
                .baseUrl("http://localhost:" + port).build();
        byte[] body = client.get().uri("/actuator/algorithms").exchange()
                .expectStatus().isOk()
                .expectBody().returnResult().getResponseBody();
        JsonNode json = MAPPER.readTree(body);

        assertThat(json.get("generatorCount").asInt()).isEqualTo(json.get("generators").size());
        assertThat(json.get("solverCount").asInt()).isEqualTo(json.get("solvers").size());

        List<String> generatorIds = new ArrayList<>();
        json.get("generators").forEach(g -> generatorIds.add(g.get("id").asText()));
        List<String> solverIds = new ArrayList<>();
        json.get("solvers").forEach(s -> solverIds.add(s.get("id").asText()));

        // Subset assertions in the ApplicationSmokeTest style: adding algorithms must not
        // fail this test, silently losing these must.
        assertThat(generatorIds).contains("recursive-backtracker", "dungeon", "chaos");
        assertThat(solverIds).contains("bfs", "astar", "tremaux");
    }
}
