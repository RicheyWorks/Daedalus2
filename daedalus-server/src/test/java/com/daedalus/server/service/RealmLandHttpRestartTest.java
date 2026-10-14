// SPDX-License-Identifier: MIT
package com.daedalus.server.service;

import com.daedalus.server.DaedalusApp;
import com.daedalus.server.security.JwtTokenService;
import com.daedalus.world.land.RealmLayout;
import com.daedalus.world.land.RealmLayoutStore;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
import org.springframework.context.ConfigurableApplicationContext;
import static org.assertj.core.api.Assertions.*;

class RealmLandHttpRestartTest {
    @TempDir Path temp;
    private final ObjectMapper json = new ObjectMapper();

    @Test void jwtDistrictReadSurvivesRestartAndReflectsIdentityPreservingMove() throws Exception {
        var store = new RealmLayoutStore(temp.resolve("layouts"));
        var initial = RealmLayout.empty("WORLD-ZERO", Set.of(0));
        store.save(initial, -1);
        var placed = initial.place(52, 52, 2, Long.MIN_VALUE);
        store.save(placed, 0);
        int identity = placed.estates().getFirst().landNumber();
        try (var client = HttpClient.newHttpClient()) {
            try (var app = start()) {
                URI uri = base(app).resolve("/api/v1/realms/WORLD-ZERO/lands?district=55");
                assertThat(get(client, uri, null).statusCode()).isEqualTo(401);
                assertThat(get(client, uri, "invalid").statusCode()).isEqualTo(401);
                String token = app.getBean(JwtTokenService.class).issue("land-reader").token();
                var response = get(client, uri, token);
                assertThat(response.statusCode()).isEqualTo(200);
                var dto = json.readTree(response.body());
                assertThat(dto.path("revision").asLong()).isEqualTo(1);
                assertThat(dto.path("lands").get(0).path("landNumber").asInt()).isEqualTo(identity);
                assertThat(dto.path("lands").get(0).path("seed").asText()).isEqualTo(Long.toString(Long.MIN_VALUE));
                assertThat(dto.path("reservedCells").get(0).asInt()).isZero();
                assertThat(get(client, base(app).resolve("/api/v1/realms/WORLD-ZERO/lands?district=100"), token).statusCode()).isEqualTo(400);
                assertThat(get(client, uri, token).statusCode()).isEqualTo(429);
                String second = app.getBean(JwtTokenService.class).issue("other-reader").token();
                assertThat(get(client, uri, second).statusCode()).isEqualTo(200);
            }
            store.save(placed.move(identity, 60, 60), 1);
            try (var app = start()) {
                String token = app.getBean(JwtTokenService.class).issue("after-restart").token();
                var response = get(client, base(app).resolve("/api/v1/realms/WORLD-ZERO/lands?district=66"), token);
                assertThat(response.statusCode()).isEqualTo(200);
                var dto = json.readTree(response.body());
                assertThat(dto.path("revision").asLong()).isEqualTo(2);
                assertThat(dto.path("lands").get(0).path("landNumber").asInt()).isEqualTo(identity);
                assertThat(dto.path("lands").get(0).path("cellX").asInt()).isEqualTo(60);
                String missing = app.getBean(JwtTokenService.class).issue("missing-reader").token();
                assertThat(get(client, base(app).resolve("/api/v1/realms/OCEAN/lands?district=55"), missing).statusCode()).isEqualTo(404);
                Files.writeString(temp.resolve("layouts/WORLD-ZERO.dlay"), "damaged");
                String corrupted = app.getBean(JwtTokenService.class).issue("corrupt-reader").token();
                var failure = get(client, base(app).resolve("/api/v1/realms/WORLD-ZERO/lands?district=66"), corrupted);
                assertThat(failure.statusCode()).isEqualTo(503);
                assertThat(failure.body()).doesNotContain(temp.toString());
            }
        }
    }

    private ConfigurableApplicationContext start() {
        return new SpringApplicationBuilder(DaedalusApp.class).profiles("prod", "test").run(
                "--server.port=0", "--server.address=127.0.0.1", "--daedalus.redis.enabled=false",
                "--daedalus.security.jwt.secret=land-http-restart-test-only-secret-123456!",
                "--daedalus.security.admin.password-bcrypt=$2a$10$7EqJtq98hPqEX7fNZaFWoOhi5B0h6C1JcqIcnLmVjKobXAB9Zwmqu",
                "--daedalus.plugins.directory=" + temp.resolve("plugins"), "--daedalus.plugins.scan-on-startup=false",
                "--daedalus.world.file=" + temp.resolve("world.daew"),
                "--daedalus.realm-layout.directory=" + temp.resolve("layouts"),
                "--resilience4j.ratelimiter.instances.oceanChunks.limit-for-period=2",
                "--resilience4j.ratelimiter.instances.oceanChunks.limit-refresh-period=1h");
    }
    private URI base(ConfigurableApplicationContext app) {
        return URI.create("http://127.0.0.1:" + ((WebServerApplicationContext) app).getWebServer().getPort());
    }
    private HttpResponse<String> get(HttpClient client, URI uri, String token) throws Exception {
        var request = HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(10));
        if (token != null) request.header("Authorization", "Bearer " + token);
        return client.send(request.build(), HttpResponse.BodyHandlers.ofString());
    }
}
