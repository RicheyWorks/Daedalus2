package com.daedalus.server.service;

import com.daedalus.server.DaedalusApp;
import com.daedalus.server.security.JwtTokenService;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
import org.springframework.context.ConfigurableApplicationContext;
import static org.assertj.core.api.Assertions.assertThat;

/** Real JWT/binary HTTP and application restart, using only disposable loopback storage. */
class RealmRecordHttpRestartTest {
    @TempDir Path tmp;
    private final ObjectMapper json = new ObjectMapper();

    @Test void hostPayloadIsAuthorizedRateLimitedAndSurvivesRestart() throws Exception {
        byte[] payload = Files.readAllBytes(Path.of("..", "docs", "contracts", "shardstead-v1", "ledger-save.bin"));
        try (var client = HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NEVER).build()) {
            try (var app = start()) {
                URI uri = endpoint(app);
                String host = app.getBean(JwtTokenService.class).issue("world-host").token();
                String player = app.getBean(JwtTokenService.class).issue("player").token();
                assertThat(send(client, uri, null, null, 0).statusCode()).isEqualTo(401);
                assertThat(send(client, uri, player, payload, 0).statusCode()).isEqualTo(403);
                assertThat(send(client, uri, host, null, 0).statusCode()).isEqualTo(404);
                var updated = send(client, uri, host, payload, 0);
                assertThat(updated.statusCode()).isEqualTo(200);
                assertThat(json.readTree(updated.body()).path("result").asText()).isEqualTo("UPDATED");
                assertThat(updated.headers().firstValue("X-Record-Revision")).contains("1");
                var replay = send(client, uri, host, payload, 0);
                assertThat(replay.statusCode()).isEqualTo(200);
                assertThat(json.readTree(replay.body()).path("result").asText()).isEqualTo("REPLAY");
                var conflict = send(client, uri, host, new byte[] {1}, 0);
                assertThat(conflict.statusCode()).isEqualTo(409);
                assertThat(conflict.headers().firstValue("X-Record-Revision")).contains("1");
                assertPayload(send(client, uri, host, null, 0), payload);
                assertThat(send(client, uri, host, null, 0).statusCode()).isEqualTo(429);
            }
            try (var app = start()) {
                String host = app.getBean(JwtTokenService.class).issue("world-host").token();
                assertPayload(send(client, endpoint(app), host, null, 0), payload);
            }
        }
    }

    private void assertPayload(HttpResponse<byte[]> reply, byte[] payload) throws Exception {
        assertThat(reply.statusCode()).isEqualTo(200);
        assertThat(reply.body()).isEqualTo(payload);
        assertThat(reply.headers().firstValue("X-Record-Revision")).contains("1");
        String hash = java.util.HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(payload));
        assertThat(reply.headers().firstValue("X-Payload-SHA256")).contains(hash);
    }

    private ConfigurableApplicationContext start() {
        return new SpringApplicationBuilder(DaedalusApp.class).profiles("prod", "test").run(
                "--server.port=0", "--server.address=127.0.0.1", "--daedalus.redis.enabled=false",
                "--daedalus.security.jwt.secret=realm-record-http-test-only-secret-123456!",
                "--daedalus.security.admin.password-bcrypt=$2a$10$7EqJtq98hPqEX7fNZaFWoOhi5B0h6C1JcqIcnLmVjKobXAB9Zwmqu",
                "--daedalus.plugins.directory=" + tmp.resolve("plugins"), "--daedalus.plugins.scan-on-startup=false",
                "--daedalus.world.file=" + tmp.resolve("world.daew"), "--daedalus.realm-record.enabled=true",
                "--daedalus.realm-record.directory=" + tmp.resolve("records"), "--daedalus.realm-record.host-subjects=world-host",
                "--resilience4j.ratelimiter.instances.realmRecords.limit-for-period=5",
                "--resilience4j.ratelimiter.instances.realmRecords.limit-refresh-period=1h");
    }

    private URI endpoint(ConfigurableApplicationContext app) {
        int port = ((WebServerApplicationContext) app).getWebServer().getPort();
        return URI.create("http://127.0.0.1:" + port + "/api/v1/host/realm-records/WORLD-ZERO/ledger");
    }

    private HttpResponse<byte[]> send(HttpClient client, URI uri, String token, byte[] payload, long revision) throws Exception {
        var request = HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(10));
        if (token != null) request.header("Authorization", "Bearer " + token);
        if (payload != null) request.header("Content-Type", "application/octet-stream")
                .header("X-Expected-Revision", Long.toString(revision)).PUT(HttpRequest.BodyPublishers.ofByteArray(payload));
        return client.send(request.build(), HttpResponse.BodyHandlers.ofByteArray());
    }
}
