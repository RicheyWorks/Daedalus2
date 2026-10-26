// SPDX-License-Identifier: MIT
package com.daedalus.server.service.simulation;

import com.daedalus.server.DaedalusApp;
import com.daedalus.server.security.JwtTokenService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
import org.springframework.context.ConfigurableApplicationContext;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Path;
import java.time.Duration;
import static org.assertj.core.api.Assertions.assertThat;

/** Full application lifecycle and real HTTP/JWT boundary, without any renderer or client mocks. */
class LivingWorldHttpRestartTest {
    @TempDir Path temp;
    private final ObjectMapper json = new ObjectMapper();
    private static final String ACTION = "{\"requestId\":\"00000000-0000-0000-0000-000000000001\",\"water\":3}";

    @Test void authenticatedHttpActionSurvivesCompleteApplicationStopAndRestart() throws Exception {
        JsonNode originalReceipt;
        String committedHash;
        try (HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).build()) {
            try (var app = start()) {
                URI state = endpoint(app);
                String alice = app.getBean(JwtTokenService.class).issue("alice").token();
                String bob = app.getBean(JwtTokenService.class).issue("bob").token();
                assertThat(send(client, state, null, null).statusCode()).isEqualTo(401);
                var before = json.readTree(send(client, state, alice, null).body());
                assertThat(before.path("cisternWater").asInt()).isEqualTo(3);
                assertThat(send(client, URI.create(state + "/actions/supply"), bob, ACTION).statusCode()).isEqualTo(403);
                var accepted = send(client, URI.create(state + "/actions/supply"), alice, ACTION);
                assertThat(accepted.statusCode()).isEqualTo(200);
                var result = json.readTree(accepted.body());
                assertThat(result.path("duplicate").asBoolean()).isFalse();
                assertThat(result.path("state").path("questCompleted").asBoolean()).isTrue();
                originalReceipt = result.path("receipt");
                committedHash = result.path("state").path("stateHash").asText();
            }
            try (var app = start()) {
                URI state = endpoint(app);
                String alice = app.getBean(JwtTokenService.class).issue("alice").token();
                var recovered = send(client, state, alice, null);
                assertThat(recovered.statusCode()).isEqualTo(200);
                var view = json.readTree(recovered.body());
                assertThat(view.path("stateHash").asText()).isEqualTo(committedHash);
                assertThat(view.path("rememberedActor").asText()).isEqualTo("alice");
                assertThat(view.path("cisternWater").asInt()).isZero();
                assertThat(view.path("keeperWater").asInt()).isEqualTo(3);
                var retry = send(client, URI.create(state + "/actions/supply"), alice, ACTION);
                assertThat(retry.statusCode()).isEqualTo(200);
                var result = json.readTree(retry.body());
                assertThat(result.path("duplicate").asBoolean()).isTrue();
                assertThat(result.path("receipt")).isEqualTo(originalReceipt);
                assertThat(result.path("state").path("stateHash").asText()).isEqualTo(committedHash);
            }
        }
    }

    private ConfigurableApplicationContext start() {
        return new SpringApplicationBuilder(DaedalusApp.class).profiles("prod", "test").run(
                "--server.port=0", "--server.address=127.0.0.1", "--daedalus.redis.enabled=false",
                // Local fixture credentials, independent of any developer production environment.
                "--daedalus.security.jwt.secret=simulation-http-restart-test-only-secret!!",
                "--daedalus.security.admin.password-bcrypt=$2a$10$7EqJtq98hPqEX7fNZaFWoOhi5B0h6C1JcqIcnLmVjKobXAB9Zwmqu",
                "--daedalus.plugins.directory=" + temp.resolve("plugins"),
                "--daedalus.plugins.scan-on-startup=false", "--daedalus.world.file=" + temp.resolve("world.daew"),
                "--daedalus.simulation.enabled=true", "--daedalus.simulation.file=" + temp.resolve("settlement.simulation"),
                "--daedalus.simulation.steward=alice", "--daedalus.simulation.tick-ms=3600000", "--daedalus.simulation.poll-ms=3600000");
    }
    private URI endpoint(ConfigurableApplicationContext app) {
        int port = ((WebServerApplicationContext) app).getWebServer().getPort();
        return URI.create("http://127.0.0.1:" + port + "/api/v1/world/world-zero/simulation/v1");
    }
    private HttpResponse<String> send(HttpClient client, URI uri, String token, String body) throws Exception {
        var request = HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(10)).header("User-Agent", "DaedalusLink-contract-test");
        if (token != null) request.header("Authorization", "Bearer " + token);
        if (body != null) request.header("Content-Type", "application/json").POST(HttpRequest.BodyPublishers.ofString(body));
        return client.send(request.build(), HttpResponse.BodyHandlers.ofString());
    }
}
