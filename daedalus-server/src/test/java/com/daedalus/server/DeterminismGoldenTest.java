// SPDX-License-Identifier: MIT

package com.daedalus.server;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Determinism, checked across a process boundary instead of across a cache hit.
 *
 * <h3>Why the existing tests could not have caught this class of bug</h3>
 *
 * <p>Determinism is one of this project's loudest claims — a campaign link "replays
 * byte-identical stages anywhere with no stored state", waypoints "derive from the maze alone",
 * complexity fits are counter-based "so any fit reproduces exactly". Every test of it runs
 * inside one JVM, and almost every one of these endpoints sits behind a Caffeine cache keyed on
 * its inputs. Call twice in one process and the second call returns the first call's object
 * without recomputing, so the assertion passes whether or not the computation is deterministic.
 *
 * <p>What breaks across a process boundary and not within one is a real and specific family:
 * anything that depends on {@code Object.hashCode()} identity, on {@code HashSet} iteration
 * order over enums (enum {@code hashCode} is identity-based, so the order is stable within a run
 * and arbitrary between runs), on {@code String.hashCode} seeding, or on ambient state that
 * happens to be warm. A tie-break that reads from such an order gives every user a different
 * "optimal" route depending on when the server last restarted, and no in-process test can see it.
 *
 * <p>This test's oracle is a JSON file of digests recorded by a <em>different JVM on a different
 * day</em>, checked into the repository. Every build is therefore a cross-process comparison.
 *
 * <h3>The two exclusions, and why they are exactly two</h3>
 *
 * <p>An audit run on 2026-07-31 reported three endpoints drifting across a restart. All three
 * were the probe's fault, and both mistakes are worth keeping as design constraints:
 *
 * <ul>
 *   <li><b>Identifiers.</b> Maze and session UUIDs are minted per process by design; the first
 *       probe stripped only top-level keys and so "found" drift in {@code /maze/daily} (which
 *       nests its maze) and {@code /campaign} (a {@code mazeId} per stage). Stripped at any
 *       depth here.</li>
 *   <li><b>Wall clock.</b> {@code elapsedMs} on a solve was 5 on the first solve after a cold
 *       start and 0–2 once the JIT had warmed. That is the field doing its job, not
 *       nondeterminism — the route, {@code visited} and {@code explored} were identical.</li>
 * </ul>
 *
 * <p>Both exclusions are checked for necessity by {@link #everyExclusionIsStillEarningItsPlace()},
 * because an exemption that costs nothing to keep is one nobody removes — and each additional
 * excluded field is a field this test has stopped checking.
 *
 * <h3>When this fails</h3>
 *
 * <p>Investigate before re-recording. A drift here means one of these endpoints answers
 * differently on a fresh JVM than it did on the machine that recorded the file, which is the bug
 * this exists to find. Re-record only after establishing that the change was intended (a
 * generator's seed derivation changed, a response gained a field), by running with
 * {@code -Ddeterminism.record=true} and committing the diff as part of that change.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "daedalus.redis.enabled=false",
        "daedalus.plugins.scan-on-startup=false",
})
@ActiveProfiles("test")
class DeterminismGoldenTest {

    /**
     * Fields dropped before hashing, at any depth. Deliberately tiny — see the class docs.
     * {@code elapsedMs} is a measurement of the machine; the rest are per-process identifiers.
     */
    private static final Set<String> VOLATILE_FIELDS = Set.of("elapsedMs");

    /**
     * Any UUID, anywhere in any string value, becomes a placeholder.
     *
     * <p>This started as a list of id <em>field names</em> and that was the wrong shape twice
     * over. The first version stripped only top-level keys and missed the daily maze's nested
     * {@code maze.id}; the second missed {@code instance} on a problem detail, whose value is a
     * request path with the maze UUID inside it — so a 404 hashed differently every run and the
     * test reported nondeterminism in a solver that uses nothing but arrays. Identifiers are
     * per-process wherever they appear, and matching them by shape catches the ones hiding in
     * strings that no exclusion list would have named.
     */
    private static final java.util.regex.Pattern UUID_ANYWHERE = java.util.regex.Pattern.compile(
            "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}");

    private static final String GOLDEN = "determinism-golden.json";
    private static final ObjectMapper JSON = new ObjectMapper();

    /** Fixed seeds throughout: a golden file that depends on today's date expires at midnight. */
    private static final String SEEDED_MAZE =
            "{\"generatorId\":\"recursive-backtracker\",\"rows\":21,\"cols\":21,\"seed\":424242}";

    @LocalServerPort
    private int port;

    private RestTestClient client() {
        return RestTestClient.bindToServer().baseUrl("http://localhost:" + port).build();
    }

    private String raw(HttpMethod method, String uri, String body) {
        var spec = client().method(method).uri(uri);
        var result = (body == null ? spec.exchange()
                : spec.contentType(MediaType.APPLICATION_JSON).body(body).exchange())
                .returnResult(String.class);
        var chunks = result.getResponseBody();
        return chunks == null ? "" : String.join("", chunks);
    }

    /** Recursively drop the volatile fields and sort keys, so the digest is order-independent. */
    private JsonNode canonical(JsonNode node) {
        if (node.isObject()) {
            var sorted = new TreeMap<String, JsonNode>();
            node.properties().forEach(e -> {
                if (!VOLATILE_FIELDS.contains(e.getKey())) {
                    sorted.put(e.getKey(), canonical(e.getValue()));
                }
            });
            ObjectNode out = JSON.createObjectNode();
            sorted.forEach(out::set);
            return out;
        }
        if (node.isArray()) {
            ArrayNode out = JSON.createArrayNode();
            node.forEach(child -> out.add(canonical(child)));
            return out;
        }
        if (node.isTextual()) {
            return JSON.getNodeFactory().textNode(
                    UUID_ANYWHERE.matcher(node.asText()).replaceAll("<uuid>"));
        }
        return node;
    }

    private String digest(String body) {
        try {
            byte[] canonical = JSON.writeValueAsBytes(canonical(JSON.readTree(body)));
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(canonical);
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < 8; i++) {
                sb.append(String.format("%02x", hash[i]));
            }
            return sb.toString();
        } catch (Exception e) {                                              // noqa
            throw new IllegalStateException("could not canonicalise: " + body, e);
        }
    }

    /** Every endpoint whose answer is claimed to be a pure function of its inputs. */
    private Map<String, String> collect() {
        String mazeId = JSON.createObjectNode().textNode("").asText();
        String generated = raw(HttpMethod.POST, "/api/v1/maze/generate", SEEDED_MAZE);
        try {
            mazeId = JSON.readTree(generated).get("id").asText();
        } catch (Exception e) {                                              // noqa
            throw new IllegalStateException("generate failed: " + generated, e);
        }

        var out = new LinkedHashMap<String, String>();
        out.put("POST /maze/generate seed=424242", digest(generated));
        out.put("GET /maze/{id}", digest(raw(HttpMethod.GET, "/api/v1/maze/" + mazeId, null)));
        // Deliberately no /maze/daily or bare /campaign: both derive from today's date, so a
        // golden digest for them would expire at midnight UTC and the failure would say
        // "nondeterministic" about a clock. Their determinism is pinned by DailyMazeServiceTest
        // and CampaignServiceTest, which control the date.
        out.put("GET /campaign?seed=7",
                digest(raw(HttpMethod.GET, "/api/v1/campaign?seed=7", null)));
        for (String[] pair : new String[][] {
                {"analysis", "/analysis"},
                {"fingerprint", "/fingerprint"},
                {"tour k=5", "/tour?count=5"},
                {"hardest-route", "/hardest-route"},
                {"distance-field", "/distance-field"},
                {"sanctuaries k=5", "/sanctuaries?k=5"},
                {"heuristic-lens MANHATTAN", "/heuristic-lens?heuristic=MANHATTAN"},
                {"heuristic-lens LANDMARK", "/heuristic-lens?heuristic=LANDMARK"},
        }) {
            out.put("GET /maze/{id}" + pair[0],
                    digest(raw(HttpMethod.GET, "/api/v1/maze/" + mazeId + pair[1], null)));
        }
        out.put("GET /tournament seed=99", digest(raw(HttpMethod.GET,
                "/api/v1/tournament?generator=binary-tree&size=11&mazes=5&seed=99", null)));
        out.put("GET /complexity prims seed=5", digest(raw(HttpMethod.GET,
                "/api/v1/complexity?generator=prims&metric=maxFrontierSize&seed=5", null)));
        // Every solver, not just A*: a tie-break that reads a hash order would show up in
        // whichever solver happens to use one, and picking a favourite would miss it.
        // Ids taken from the registry, not from memory: "bidirectional-bfs" was a guess, it
        // 404s, and the resulting problem detail hashed differently every run because its
        // `instance` field carries the request path — maze UUID included. The test duly
        // reported a nondeterministic solver that is implemented entirely with int arrays.
        for (String solver : List.of("astar", "bfs", "dijkstra", "dial", "dfs",
                "bidirectional", "dead-end-filling", "tremaux", "wall-follower")) {
            out.put("POST /maze/{id}/solve/" + solver, digest(raw(HttpMethod.POST,
                    "/api/v1/maze/" + mazeId + "/solve/" + solver, null)));
        }
        out.put("GET /algorithms", digest(raw(HttpMethod.GET, "/api/v1/algorithms", null)));
        return out;
    }

    @Test
    void everyDeterministicEndpointMatchesTheDigestsRecordedByAnEarlierProcess()
            throws IOException {
        Map<String, String> now = collect();

        if (Boolean.getBoolean("determinism.record")) {
            Path target = Path.of("src/test/resources", GOLDEN);
            Files.writeString(target, JSON.writerWithDefaultPrettyPrinter()
                    .writeValueAsString(new TreeMap<>(now)) + "\n");
            throw new AssertionError("Recorded " + now.size() + " digests to " + target
                    + ". This is not a passing run — review the diff and re-run without "
                    + "-Ddeterminism.record=true.");
        }

        Map<String, String> golden;
        try (InputStream in = getClass().getClassLoader().getResourceAsStream(GOLDEN)) {
            assertThat(in).as("%s is missing; record it with -Ddeterminism.record=true", GOLDEN)
                    .isNotNull();
            golden = JSON.readValue(new String(in.readAllBytes(), StandardCharsets.UTF_8),
                    JSON.getTypeFactory().constructMapType(TreeMap.class, String.class,
                            String.class));
        }

        List<String> drift = new ArrayList<>();
        now.forEach((name, value) -> {
            String was = golden.get(name);
            if (was == null) {
                drift.add(name + ": not in the golden file (new endpoint? record it)");
            } else if (!was.equals(value)) {
                drift.add(name + ": recorded " + was + ", this process answered " + value);
            }
        });
        golden.keySet().stream().filter(k -> !now.containsKey(k))
                .forEach(k -> drift.add(k + ": in the golden file but no longer collected"));

        assertThat(drift)
                .as("These answers differ from the ones a previous JVM recorded. That is what "
                        + "nondeterminism looks like from a user's side: the same seed, a "
                        + "different answer, because the server restarted. Investigate before "
                        + "re-recording.%n%s", String.join("\n", drift))
                .isEmpty();
        assertThat(now).as("nothing was collected, so nothing was compared").hasSizeGreaterThan(15);
    }

    @Test
    void everyExclusionIsStillEarningItsPlace() {
        // Each excluded field is a field this test no longer checks, so the list must stay
        // minimal and must stay *needed*. An exclusion for a field nothing returns any more is
        // dead permission — the same failure mode as ErrorContractTest's ALLOW_EMPTY_404, which
        // sat enabled and inert until a mutation exposed it.
        String generated = raw(HttpMethod.POST, "/api/v1/maze/generate", SEEDED_MAZE);
        String mazeId;
        try {
            mazeId = JSON.readTree(generated).get("id").asText();
        } catch (Exception e) {                                              // noqa
            throw new IllegalStateException(e);
        }
        String corpus = generated
                + raw(HttpMethod.GET, "/api/v1/maze/" + mazeId, null)
                + raw(HttpMethod.POST, "/api/v1/maze/" + mazeId + "/solve/astar", null)
                + raw(HttpMethod.POST, "/api/v1/maze/" + mazeId + "/session?player=x", null)
                + raw(HttpMethod.GET, "/api/v1/campaign?seed=7", null);

        List<String> unused = VOLATILE_FIELDS.stream()
                .filter(field -> !corpus.contains("\"" + field + "\""))
                .sorted().toList();
        assertThat(unused)
                .as("these fields are excluded from the determinism digest but no endpoint "
                        + "returns them any more — stop excluding them: %s", unused)
                .isEmpty();
        assertThat(VOLATILE_FIELDS)
                .as("every addition here is a field this test stopped checking, so it needs a "
                        + "reason in the class Javadoc")
                .hasSize(1);

        // The UUID redaction is the other exclusion, and it needs the same proof of life: if it
        // stopped matching, every digest would silently start including per-process ids and the
        // golden comparison would fail for a reason that has nothing to do with determinism.
        assertThat(UUID_ANYWHERE.matcher(corpus).find())
                .as("no UUID appeared in any response, so the redaction is either unnecessary "
                        + "or broken").isTrue();
        assertThat(UUID_ANYWHERE.matcher("not-a-uuid-at-all").find())
                .as("the redaction pattern matches things that are not UUIDs").isFalse();
    }
}
