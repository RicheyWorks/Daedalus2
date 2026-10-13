// SPDX-License-Identifier: MIT
package com.daedalus.server.config;

import com.daedalus.server.security.JwtTokenService;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import static org.assertj.core.api.Assertions.assertThat;

/** Exercise the real prod JWT chain: an otherwise valid token is not authority to drive this encounter. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "daedalus.security.jwt.secret=tactics-test-secret-at-least-32-bytes!!",
        "daedalus.security.admin.password-bcrypt=$2a$10$7EqJtq98hPqEX7fNZaFWoOhi5B0h6C1JcqIcnLmVjKobXAB9Zwmqu",
        "daedalus.redis.enabled=false", "daedalus.plugins.scan-on-startup=false",
        "daedalus.tactics.host.subject=trusted-engine", "daedalus.tactics.host.squad=auth-pack",
        "daedalus.kennel.host-subject=trusted-engine"
})
@ActiveProfiles("prod")
class TacticsHostAuthorizationTest {
    @LocalServerPort int port;
    @Autowired JwtTokenService tokens;
    private final ObjectMapper json = new ObjectMapper();

    @Test void kennelUsesRealJwtBoundaryAndPlainTextContract() throws Exception {
        try (var client = HttpClient.newHttpClient()) {
            for (String subject : java.util.List.of("anonymous", "other-user", "trusted-engine")) {
                var request = HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/api/v1/kennel/brew"))
                        .header("Content-Type", "application/json").POST(HttpRequest.BodyPublishers.ofString(
                                "{\"herbs\":[\"Barkbalm\"],\"coat\":\"None\",\"drinker\":\"cane_corso\",\"stage\":1,\"charm\":false,\"seed\":0}"));
                if (!subject.equals("anonymous")) request.header("Authorization", "Bearer " + tokens.issue(subject).token());
                var response = client.send(request.build(), HttpResponse.BodyHandlers.ofString());
                assertThat(response.statusCode()).isEqualTo(subject.equals("anonymous") ? 401 : subject.equals("other-user") ? 403 : 200);
                if (response.statusCode() == 200) assertThat(response.body())
                        .isEqualTo("TONIC 1\nbrew tonic_barkbalm 1.0 120 0 overTime 0.0\nmod hearts add 1.0\nend\n");
            }
        }
    }

    private HttpResponse<String> post(String token, String squad, String events) throws Exception {
        String roster = "DTR 1\nsession auth-session squad " + squad + " tick 1\nunit a SLIME 100 100 0 0 0 1\n";
        var request = HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/api/v1/tactics/decide"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json.writeValueAsString(Map.of("roster", roster, "events", events))));
        if (token != null) request.header("Authorization", "Bearer " + token);
        try (var client = HttpClient.newHttpClient()) {
            return client.send(request.build(), HttpResponse.BodyHandlers.ofString());
        }
    }

    @Test void rejectsWrongIdentityBeforeSharedStateAndAllowsOnlyConfiguredHostSquad() throws Exception {
        assertThat(post(null, "auth-pack", "").statusCode()).isEqualTo(401);
        String attacker = tokens.issue("other-user").token();
        String engine = tokens.issue("trusted-engine").token();
        String poison = "DTE 1\ntick 1\nevent PLAYER player 999 0 0 100\n";
        var denied = post(attacker, "auth-pack", poison);
        assertThat(denied.statusCode()).isEqualTo(403);
        assertThat(json.readTree(denied.body()).get("status").asInt()).isEqualTo(403);
        assertThat(post(engine, "someone-elses-pack", poison).statusCode()).isEqualTo(403);
        var accepted = post(engine, "auth-pack", "");
        assertThat(accepted.statusCode()).isEqualTo(200);
        assertThat(json.readTree(accepted.body()).get("result").asText()).isEqualTo("APPLY");
        assertThat(json.readTree(accepted.body()).get("why").asText()).contains("no PLAYER");
        assertThat(post(attacker, "auth-pack", "").statusCode()).isEqualTo(403);
        assertThat(json.readTree(post(engine, "auth-pack", "").body()).get("result").asText()).isEqualTo("REPEAT");
    }
}
