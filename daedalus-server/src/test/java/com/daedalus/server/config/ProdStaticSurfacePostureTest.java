// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpMethod;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The prod posture of everything that is <em>not</em> a controller mapping.
 *
 * <p>{@link ProdAuthPostureTest} is thorough about the API and structurally blind to this. Its
 * completeness half walks {@code controller/**.java} and extracts {@code @…Mapping} annotations,
 * so a file served off the classpath can never appear in its table — not because anyone forgot,
 * but because a static resource has no annotation to find. The gap is not in the table; it is in
 * what the table is capable of containing.
 *
 * <p><b>What was in the gap.</b> The README publishes the web UI as "served at {@code /}". In
 * prod it answered <b>401</b> — {@code anyRequest().authenticated()} is fail-closed and static
 * resources are requests like any other. That is not a cosmetic outage, because it lands on a
 * feature this project had already fixed once at the other layer. {@code ProdSecurityConfig}
 * opens {@code GET /api/v1/session/&#123;id&#125;}, its tour, the ghost run and the agent
 * re-poll, and explains why at length: a spectator link that only the operator can open is not a
 * spectator link, and until 2026-07-31 those endpoints "did not work in prod at all". But the
 * link the UI actually hands out is {@code https://host/#session=&#123;id&#125;} — origin root
 * plus a fragment. Every one of those endpoints was reachable and the page that calls them was
 * not, so the feature still did not work; the fix had been applied to the half that had a test.
 *
 * <p>So this test is the missing table, kept the same way: an explicit posture per path, driven
 * against a real prod boot, plus a completeness check that fails when a static file exists with
 * no row. The allowlist in {@code ProdSecurityConfig} is enumerated rather than globbed for the
 * same reason — {@code /**} over a static directory publishes whatever later lands in it.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "daedalus.security.jwt.secret=prod-static-posture-secret-32-bytes!",
        "daedalus.security.admin.password-bcrypt="
                + "$2a$10$7EqJtq98hPqEX7fNZaFWoOhi5B0h6C1JcqIcnLmVjKobXAB9Zwmqu",
        "daedalus.redis.enabled=false",
        "daedalus.plugins.scan-on-startup=false",
})
@ActiveProfiles("prod")
class ProdStaticSurfacePostureTest {

    private enum Posture { PUBLIC, REFUSED }

    /** Every non-API path with a decision recorded against it. */
    private static final Map<String, Posture> EXPECTED = new LinkedHashMap<>();

    static {
        // The UI, by both the name a browser asks for and the name on disk. A user types the
        // first; the welcome-page forward resolves to the second; a matcher covering one and not
        // the other is a coin flip on which request shape a real visitor makes.
        EXPECTED.put("GET /", Posture.PUBLIC);
        EXPECTED.put("GET /index.html", Posture.PUBLIC);
        EXPECTED.put("GET /draw.js", Posture.PUBLIC);
        EXPECTED.put("GET /api.js", Posture.PUBLIC);
        EXPECTED.put("GET /share.js", Posture.PUBLIC);
        EXPECTED.put("GET /fog.js", Posture.PUBLIC);
        EXPECTED.put("GET /seat.js", Posture.PUBLIC);
        EXPECTED.put("GET /lab.js", Posture.PUBLIC);
        EXPECTED.put("GET /caption.js", Posture.PUBLIC);
        EXPECTED.put("GET /mint.js", Posture.PUBLIC);
        EXPECTED.put("GET /campaign.js", Posture.PUBLIC);
        EXPECTED.put("GET /spectate.js", Posture.PUBLIC);
        EXPECTED.put("GET /hunt.js", Posture.PUBLIC);
        EXPECTED.put("GET /solve.js", Posture.PUBLIC);
        EXPECTED.put("GET /theory.js", Posture.PUBLIC);
        EXPECTED.put("GET /live.js", Posture.PUBLIC);
        EXPECTED.put("GET /session.js", Posture.PUBLIC);
        EXPECTED.put("GET /fogwalk.js", Posture.PUBLIC);
        EXPECTED.put("GET /app.js", Posture.PUBLIC);

        // SockJS info is the first request a browser makes. Closing /ws/** made that 401, so
        // a signed-in CONNECT never happened — the token was on a frame the handshake blocked.
        EXPECTED.put("GET /ws/info", Posture.PUBLIC);

        // The method is half the decision and the first version of this table left it out —
        // every row said GET, so dropping `HttpMethod.GET` from the matcher in
        // ProdSecurityConfig changed nothing any assertion could see. Mutation found that: 4 of
        // 5, with the method-scope mutation the survivor. Serving a page is a read; a matcher
        // that permits every verb on that path is the same fail-open widening as a '*' becoming
        // '**', in the other axis.
        EXPECTED.put("POST /", Posture.REFUSED);
        EXPECTED.put("POST /index.html", Posture.REFUSED);
        EXPECTED.put("PUT /index.html", Posture.REFUSED);
        EXPECTED.put("DELETE /index.html", Posture.REFUSED);
        EXPECTED.put("POST /draw.js", Posture.REFUSED);
        EXPECTED.put("POST /api.js", Posture.REFUSED);
        EXPECTED.put("POST /share.js", Posture.REFUSED);
        EXPECTED.put("POST /fog.js", Posture.REFUSED);
        EXPECTED.put("POST /seat.js", Posture.REFUSED);
        EXPECTED.put("POST /lab.js", Posture.REFUSED);
        EXPECTED.put("POST /caption.js", Posture.REFUSED);
        EXPECTED.put("POST /mint.js", Posture.REFUSED);
        EXPECTED.put("POST /campaign.js", Posture.REFUSED);
        EXPECTED.put("POST /spectate.js", Posture.REFUSED);
        EXPECTED.put("POST /hunt.js", Posture.REFUSED);
        EXPECTED.put("POST /solve.js", Posture.REFUSED);
        EXPECTED.put("POST /theory.js", Posture.REFUSED);
        EXPECTED.put("POST /live.js", Posture.REFUSED);
        EXPECTED.put("POST /session.js", Posture.REFUSED);
        EXPECTED.put("POST /fogwalk.js", Posture.REFUSED);
        EXPECTED.put("POST /app.js", Posture.REFUSED);

        // Nothing else is served, and the fail-closed default is the feature. A path that does
        // not exist must not be distinguishable from one that is merely protected.
        EXPECTED.put("GET /application.yml", Posture.REFUSED);
        EXPECTED.put("GET /application-prod.yml", Posture.REFUSED);
        EXPECTED.put("GET /BOOT-INF/classes/application.yml", Posture.REFUSED);
        EXPECTED.put("GET /swagger-ui.html", Posture.REFUSED);
        EXPECTED.put("GET /v3/api-docs", Posture.REFUSED);
        EXPECTED.put("GET /actuator/env", Posture.REFUSED);
    }

    /** The path half of a {@code "METHOD /path"} table key. */
    private static String pathOf(String signature) {
        return signature.split(" ", 2)[1];
    }

    @LocalServerPort
    private int port;

    @Test
    void everyNonApiPathHasThePostureItIsSupposedTo() {
        RestTestClient client = RestTestClient.bindToServer()
                .baseUrl("http://localhost:" + port).build();

        List<String> wrong = new ArrayList<>();
        EXPECTED.forEach((signature, posture) -> {
            String[] parts = signature.split(" ", 2);
            int status = client.method(HttpMethod.valueOf(parts[0])).uri(parts[1]).exchange()
                    .returnResult(byte[].class).getStatus().value();
            // 401 or 403 only, and the exclusion of 405 is the whole point of the write rows.
            // Drop `HttpMethod.GET` from the matcher and `POST /` still fails — but it fails at
            // 405, from the servlet layer, because the *security* layer said yes and handed the
            // request on. Counting that as refused makes the method-scope mutation invisible,
            // which is exactly what happened on this harness's first run. The property is not
            // "the write fails", it is "the security layer is the thing that refused it".
            boolean refused = status == 401 || status == 403;

            if (posture == Posture.REFUSED && !refused) {
                wrong.add(signature + " should not be served but answered " + status);
            }
            if (posture == Posture.PUBLIC && refused) {
                wrong.add(signature + " should be public but answered " + status
                        + " — this is the exact state the spectator permalink shipped in");
            }
        });

        assertThat(wrong)
                .as("prod posture for the non-API surface does not match what is documented: %s",
                        wrong)
                .isEmpty();
    }

    @Test
    void theUiIsActuallyServedAndNotJustUnrefused() {
        // A 200 with an empty body would satisfy the table above and still leave a blank page in
        // front of every spectator. Assert the page is the page: the share-link feature depends
        // on the script that builds those links being present in what prod hands back.
        RestTestClient client = RestTestClient.bindToServer()
                .baseUrl("http://localhost:" + port).build();

        byte[] body = client.method(HttpMethod.GET).uri("/").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] painter = client.method(HttpMethod.GET).uri("/draw.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] api = client.method(HttpMethod.GET).uri("/api.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] share = client.method(HttpMethod.GET).uri("/share.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] fog = client.method(HttpMethod.GET).uri("/fog.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] seat = client.method(HttpMethod.GET).uri("/seat.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] lab = client.method(HttpMethod.GET).uri("/lab.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] caption = client.method(HttpMethod.GET).uri("/caption.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] mint = client.method(HttpMethod.GET).uri("/mint.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] campaign = client.method(HttpMethod.GET).uri("/campaign.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] spectate = client.method(HttpMethod.GET).uri("/spectate.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] hunt = client.method(HttpMethod.GET).uri("/hunt.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] solve = client.method(HttpMethod.GET).uri("/solve.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] theory = client.method(HttpMethod.GET).uri("/theory.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] live = client.method(HttpMethod.GET).uri("/live.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] session = client.method(HttpMethod.GET).uri("/session.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] fogwalk = client.method(HttpMethod.GET).uri("/fogwalk.js").exchange()
                .returnResult(byte[].class).getResponseBody();
        byte[] script = client.method(HttpMethod.GET).uri("/app.js").exchange()
                .returnResult(byte[].class).getResponseBody();

        assertThat(body).as("prod served nothing at /").isNotNull();
        assertThat(painter).as("prod served nothing at /draw.js").isNotNull();
        assertThat(api).as("prod served nothing at /api.js").isNotNull();
        assertThat(share).as("prod served nothing at /share.js").isNotNull();
        assertThat(fog).as("prod served nothing at /fog.js").isNotNull();
        assertThat(seat).as("prod served nothing at /seat.js").isNotNull();
        assertThat(lab).as("prod served nothing at /lab.js").isNotNull();
        assertThat(caption).as("prod served nothing at /caption.js").isNotNull();
        assertThat(mint).as("prod served nothing at /mint.js").isNotNull();
        assertThat(campaign).as("prod served nothing at /campaign.js").isNotNull();
        assertThat(spectate).as("prod served nothing at /spectate.js").isNotNull();
        assertThat(hunt).as("prod served nothing at /hunt.js").isNotNull();
        assertThat(solve).as("prod served nothing at /solve.js").isNotNull();
        assertThat(theory).as("prod served nothing at /theory.js").isNotNull();
        assertThat(live).as("prod served nothing at /live.js").isNotNull();
        assertThat(session).as("prod served nothing at /session.js").isNotNull();
        assertThat(fogwalk).as("prod served nothing at /fogwalk.js").isNotNull();
        assertThat(script).as("prod served nothing at /app.js").isNotNull();
        String html = new String(body);
        String js = new String(painter) + new String(api) + new String(share)
                + new String(fog) + new String(seat) + new String(lab)
                + new String(caption) + new String(mint) + new String(campaign)
                + new String(spectate) + new String(hunt) + new String(solve)
                + new String(theory)
                + new String(live) + new String(session)
                + new String(fogwalk) + new String(script);
        assertThat(html).contains("<html", "/draw.js", "/api.js", "/share.js",
                "/fog.js", "/seat.js", "/lab.js", "/caption.js", "/mint.js",
                "/campaign.js", "/spectate.js", "/hunt.js", "/solve.js",
                "/theory.js", "/live.js", "/session.js", "/fogwalk.js",
                "/app.js");
        assertThat(js).contains("#session=", "DaedalusDraw", "DaedalusApi",
                "DaedalusShare", "DaedalusFog", "DaedalusSeat", "DaedalusLab",
                "DaedalusCaption", "DaedalusMint", "DaedalusCampaign",
                "DaedalusSpectate",
                "DaedalusHunt", "DaedalusSolve", "DaedalusTheory",
                "connectStomp", "async function play",
                "async function startFog");
        assertThat(html.length() + js.length())
                .as("the page+script prod serves is %d bytes, which is not the UI",
                        html.length() + js.length())
                .isGreaterThan(10_000);
    }

    @Test
    void everyStaticFileOnTheClasspathAppearsInTheTable() throws IOException {
        // Completeness, and the reason this class exists rather than another row in the auth
        // table. ProdAuthPostureTest's scanner walks controllers for annotations; a file has
        // none, so its absence there was invisible by construction. This walks the static
        // directory instead, so adding a second asset fails the build until somebody records
        // whether prod should hand it out — which is also why the matcher in ProdSecurityConfig
        // enumerates paths instead of globbing a directory.
        Path root = Path.of("src/main/resources/static");
        assertThat(Files.isDirectory(root))
                .as("static resource root not found at %s, so this test is blind",
                        root.toAbsolutePath())
                .isTrue();

        var undocumented = new TreeSet<String>();
        int seen = 0;
        try (Stream<Path> files = Files.walk(root)) {
            for (Path file : files.filter(Files::isRegularFile).toList()) {
                seen++;
                String served = "/" + root.relativize(file).toString().replace('\\', '/');
                boolean documented = EXPECTED.keySet().stream()
                        .anyMatch(k -> pathOf(k).equals(served));
                if (!documented) {
                    undocumented.add(served);
                }
            }
        }

        assertThat(seen).as("the static scan found no files at all, so it is broken")
                .isPositive();
        assertThat(undocumented)
                .as("these files are on the classpath but no prod posture is recorded for "
                        + "them, so nobody has decided whether prod hands them out: %s",
                        undocumented)
                .isEmpty();
    }
}
