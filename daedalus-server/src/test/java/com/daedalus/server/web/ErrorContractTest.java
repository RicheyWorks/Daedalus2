// SPDX-License-Identifier: MIT

package com.daedalus.server.web;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.client.RestTestClient;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Every way this API can say no answers in the same shape.
 *
 * <h3>What the audit found</h3>
 *
 * <p>{@code ApiExceptionHandler} announces an RFC 7807 error model in its own Javadoc and the web
 * UI's help text repeats the promise, so the contract looked settled. (The README did not mention
 * it at all, which is its own small finding — a contract nobody publishes is one nobody can hold
 * you to. It has an "Errors" section now.) Driving twenty-one distinct failure modes at a running
 * server and comparing the bodies found five outside the contract:
 *
 * <ul>
 *   <li>an unregistered {@code generatorId} answered <b>500</b> with a stack trace in the log,
 *       and so did an unregistered solver id — a client typo reported as a server fault, on the
 *       two most-used endpoints in the API, while every analytical endpoint added later answered
 *       a clean 404;</li>
 *   <li>a missing required query parameter, the wrong HTTP verb, and an unsupported
 *       {@code Content-Type} each fell through to Spring Boot's default
 *       {@code {timestamp, status, error, path}} body.</li>
 * </ul>
 *
 * <p>Only the first two were visibly broken. The other three returned the right status code with
 * the wrong body, which is the more dangerous failure: a client reading {@code detail} and
 * {@code title} gets nulls from a response that looks fine, and nothing anywhere goes red.
 *
 * <h3>Why this test generates its cases instead of listing them</h3>
 *
 * <p>The five gaps were all on paths no test drove, and a hand-written roster of failure modes is
 * a list of the paths somebody thought of — the same shape of blind spot. So the second test
 * below derives its requests from the controller sources: every mapping gets the wrong verb and a
 * malformed path variable, and <em>any</em> 4xx or 5xx that comes back without a
 * {@code type} field fails the build. A new endpoint is covered the day it is written.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "daedalus.redis.enabled=false",
        "daedalus.plugins.scan-on-startup=false",
})
class ErrorContractTest {

    /** RFC 7807's members. A response missing any of them is not a problem detail. */
    private static final List<String> RFC7807 =
            List.of("type", "title", "status", "detail", "instance");

    private static final String UUID_SHAPED = "11111111-2222-3333-4444-555555555555";

    /**
     * The one deliberate exception: {@code ResponseEntity.notFound().build()} answers 404 with no
     * body at all, at 27 call sites, meaning "the thing you addressed is not here".
     *
     * <p>This is a real inconsistency and it is recorded rather than repaired here, because the
     * repair is a mechanism (a thrown domain exception with one handler) rather than 27 hand
     * edits, and it deserves its own pass — see BACKLOG. What matters for now is that it cannot
     * grow quietly: the assertion below permits an <em>empty</em> 404 body and nothing else, so
     * any new half-populated or default-shaped error still fails.
     */
    private static final boolean ALLOW_EMPTY_404 = true;

    private static final ObjectMapper JSON = new ObjectMapper();

    @LocalServerPort
    private int port;

    @Autowired
    private org.springframework.context.ApplicationContext ctx;

    private RestTestClient client() {
        return RestTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    }

    private record Answer(int status, String contentType, String body) {

        JsonNode json() {
            try {
                return body == null || body.isBlank() ? null : JSON.readTree(body);
            } catch (Exception e) {                                          // noqa
                return null;
            }
        }
    }

    private Answer send(HttpMethod method, String uri, String body, MediaType type) {
        var spec = client().method(method).uri(uri);
        var result = (body == null
                ? spec.exchange()
                : spec.contentType(type).body(body).exchange()).returnResult(String.class);
        var ct = result.getResponseHeaders().getContentType();
        return new Answer(result.getStatus().value(), ct == null ? "" : ct.toString(),
                result.getResponseBody() == null ? "" : String.join("", result.getResponseBody()));
    }

    /** Fails with a readable message unless the answer is a complete RFC 7807 problem detail. */
    private void assertProblemDetail(String label, Answer a) {
        assertThat(a.status()).as("%s answered %d — a client mistake is not a server fault",
                label, a.status()).isLessThan(500);
        JsonNode json = a.json();
        assertThat(json).as("%s answered %d with a body that is not JSON: <%s>",
                label, a.status(), a.body()).isNotNull();
        List<String> missing = RFC7807.stream().filter(k -> !json.has(k)).toList();
        assertThat(missing).as("%s answered %d but the body is not a problem detail — "
                        + "missing %s. Body: %s", label, a.status(), missing, a.body())
                .isEmpty();
        assertThat(json.has("timestamp"))
                .as("%s fell through to Boot's default error body: %s", label, a.body())
                .isFalse();
        assertThat(a.contentType()).as("%s should be served as application/problem+json", label)
                .startsWith("application/problem+json");
    }

    @Test
    void everyFailureModeAnswersInTheHouseShape() {
        Answer generated = send(HttpMethod.POST, "/api/v1/maze/generate",
                "{\"generatorId\":\"binary-tree\",\"rows\":11,\"cols\":11,\"seed\":1}",
                MediaType.APPLICATION_JSON);
        String mazeId = generated.json().get("id").asText();

        record Case(String label, HttpMethod method, String uri, String body, MediaType type) {}
        List<Case> cases = List.of(
                // The two that used to be 500s.
                new Case("unregistered generatorId", HttpMethod.POST, "/api/v1/maze/generate",
                        "{\"generatorId\":\"no-such-generator\",\"rows\":11,\"cols\":11}",
                        MediaType.APPLICATION_JSON),
                new Case("unregistered solver id", HttpMethod.POST,
                        "/api/v1/maze/" + mazeId + "/solve/no-such-solver", null, null),
                // The three that used to be Boot's default shape.
                new Case("missing required parameter", HttpMethod.GET, "/api/v1/complexity",
                        null, null),
                new Case("wrong http verb", HttpMethod.GET, "/api/v1/maze/" + mazeId + "/live",
                        null, null),
                new Case("unsupported media type", HttpMethod.POST, "/api/v1/maze/generate",
                        "rows=11", MediaType.TEXT_PLAIN),
                new Case("unmapped path", HttpMethod.GET, "/api/v1/no-such-endpoint", null, null),
                // The ones that already worked — kept so a regression in them is caught here too.
                new Case("constraint violation", HttpMethod.GET, "/api/v1/leaderboard?n=999",
                        null, null),
                new Case("uncoercible parameter", HttpMethod.GET, "/api/v1/leaderboard?n=abc",
                        null, null),
                new Case("uncoercible path variable", HttpMethod.GET, "/api/v1/maze/not-a-uuid",
                        null, null),
                new Case("bad enum value", HttpMethod.GET,
                        "/api/v1/maze/" + mazeId + "/heuristic-lens?heuristic=NOPE", null, null),
                new Case("malformed JSON body", HttpMethod.POST, "/api/v1/maze/generate",
                        "{not json", MediaType.APPLICATION_JSON),
                new Case("body validation", HttpMethod.POST, "/api/v1/maze/generate",
                        "{\"generatorId\":\"binary-tree\",\"rows\":-1,\"cols\":11}",
                        MediaType.APPLICATION_JSON));

        List<String> failures = new ArrayList<>();
        for (Case c : cases) {
            try {
                assertProblemDetail(c.label(), send(c.method(), c.uri(), c.body(), c.type()));
            } catch (AssertionError e) {
                failures.add(e.getMessage());
            }
        }
        assertThat(failures).as("failure modes outside the RFC 7807 contract:\n%s",
                String.join("\n", failures)).isEmpty();
    }

    @Test
    void anUnknownAlgorithmNamesTheOnesThatExist() {
        // A 404 that only says "no" makes the caller guess. This one is generated from the live
        // registry, so it cannot drift from what is actually registered.
        Answer a = send(HttpMethod.POST, "/api/v1/maze/generate",
                "{\"generatorId\":\"recursive-backtracer\",\"rows\":11,\"cols\":11}",
                MediaType.APPLICATION_JSON);
        assertProblemDetail("typo'd generatorId", a);
        JsonNode json = a.json();
        assertThat(json.get("status").asInt()).isEqualTo(404);
        assertThat(json.get("kind").asText()).isEqualTo("generator");
        assertThat(json.get("requested").asText()).isEqualTo("recursive-backtracer");

        var registry = ctx.getBean(com.daedalus.engine.generators.GeneratorRegistry.class);
        var advertised = new TreeSet<String>();
        json.get("known").forEach(n -> advertised.add(n.asText()));
        var registered = new TreeSet<String>();
        registry.all().forEach(g -> registered.add(g.id()));
        assertThat(advertised)
                .as("the 404 must list exactly what is registered, or it is worse than useless")
                .isEqualTo(registered);
        assertThat(advertised).contains("recursive-backtracker");
    }

    @Test
    void noGeneratedRequestEscapesTheContract() throws IOException {
        // Every mapping, driven two ways it is not meant to be driven. The five gaps this class
        // was written for were all on paths no test happened to visit, so the cases here are
        // derived from the sources rather than chosen.
        var mappings = scanMappings();
        assertThat(mappings).as("the scanner found no mappings, so this test is blind")
                .hasSizeGreaterThan(25);

        List<String> failures = new ArrayList<>();
        int checked = 0;
        for (var m : mappings) {
            String uri = m.path().replaceAll("\\{[^}]+}", UUID_SHAPED);

            // 1. The wrong verb. Universal: every path rejects at least one method.
            HttpMethod wrong = m.method() == HttpMethod.GET ? HttpMethod.DELETE : HttpMethod.GET;
            checked += record(failures, wrong + " " + m.path() + " (wrong verb)",
                    send(wrong, uri, null, null));

            // 2. A path variable that cannot be coerced. Skipped where there is no variable.
            if (m.path().contains("{")) {
                String bad = m.path().replaceAll("\\{[^}]+}", "definitely-not-a-uuid");
                checked += record(failures, m.method() + " " + m.path() + " (bad path variable)",
                        send(m.method(), bad, null, null));
            }
        }

        assertThat(checked).as("no generated request produced an error, so nothing was checked")
                .isGreaterThan(25);
        assertThat(failures).as("generated requests that escaped the error contract (%d):\n%s",
                failures.size(), String.join("\n", failures)).isEmpty();
    }

    /**
     * Records a failure unless the answer is inside the contract. Returns 1 if the answer was an
     * error at all, so the caller can prove the generated requests actually exercised something.
     */
    private int record(List<String> failures, String label, Answer a) {
        if (a.status() < 400) {
            return 0;
        }
        if (ALLOW_EMPTY_404 && a.status() == 404 && a.body().isEmpty()) {
            return 1;   // the documented bodiless-404 exemption; see ALLOW_EMPTY_404
        }
        try {
            assertProblemDetail(label, a);
        } catch (AssertionError e) {
            failures.add("  " + e.getMessage().replace("\n", " "));
        }
        return 1;
    }

    @Test
    void errorBodiesNeverLeakInternals() {
        // A problem detail is written for the caller. Class names, package paths and stack frames
        // are for the log. The 500s this audit removed were leaking all three.
        List<String> banned = List.of("com.daedalus", "org.springframework", "java.lang",
                "Exception", "\tat ", "Caused by");
        record Probe(String label, HttpMethod method, String uri, String body, MediaType type) {}
        List<Probe> probes = List.of(
                new Probe("unregistered generator", HttpMethod.POST, "/api/v1/maze/generate",
                        "{\"generatorId\":\"nope\",\"rows\":11,\"cols\":11}",
                        MediaType.APPLICATION_JSON),
                new Probe("malformed body", HttpMethod.POST, "/api/v1/maze/generate",
                        "{\"rows\":", MediaType.APPLICATION_JSON),
                new Probe("bad path variable", HttpMethod.GET, "/api/v1/maze/nope", null, null),
                new Probe("missing parameter", HttpMethod.GET, "/api/v1/complexity", null, null),
                new Probe("unsupported media type", HttpMethod.POST, "/api/v1/maze/generate",
                        "x", MediaType.TEXT_PLAIN));

        List<String> leaks = new ArrayList<>();
        for (Probe p : probes) {
            String body = send(p.method(), p.uri(), p.body(), p.type()).body();
            banned.stream().filter(body::contains)
                    .forEach(b -> leaks.add(p.label() + " leaks \"" + b.strip() + "\": " + body));
        }
        assertThat(leaks).as("error bodies leaking internals:\n%s", String.join("\n", leaks))
                .isEmpty();
    }

    // ---------- source scan ----------

    private record Mapping(HttpMethod method, String path) {}

    private static final Pattern MAPPING = Pattern.compile(
            "@(Get|Post|Put|Patch|Delete)Mapping\\b\\s*(\\(([^)]*)\\))?");
    private static final Pattern NAMED_PATH =
            Pattern.compile("(?:value|path)\\s*=\\s*\"([^\"]*)\"");
    private static final Pattern LITERAL = Pattern.compile("\"(/[^\"]*)\"");

    private Set<Mapping> scanMappings() throws IOException {
        var found = new LinkedHashSet<Mapping>();
        Path root = Path.of("src/main/java/com/daedalus/server/controller");
        try (Stream<Path> files = Files.walk(root)) {
            for (Path file : files.filter(f -> f.toString().endsWith(".java")).toList()) {
                String text = Files.readString(file);
                Matcher base = Pattern.compile("@RequestMapping\\(\"([^\"]+)\"\\)").matcher(text);
                String prefix = base.find() ? base.group(1) : "";
                Matcher m = MAPPING.matcher(text);
                while (m.find()) {
                    found.add(new Mapping(
                            HttpMethod.valueOf(m.group(1).toUpperCase(Locale.ROOT)),
                            prefix + pathOf(m.group(3))));
                }
            }
        }
        return found;
    }

    private static String pathOf(String args) {
        if (args == null || args.isBlank()) {
            return "";
        }
        Matcher named = NAMED_PATH.matcher(args);
        if (named.find()) {
            return named.group(1);
        }
        Matcher literal = LITERAL.matcher(args);
        return literal.find() ? literal.group(1) : "";
    }
}
