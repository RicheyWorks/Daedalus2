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
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Every endpoint's authentication posture under the <b>prod</b> profile, asserted rather than
 * inherited.
 *
 * <h3>Why this is worth a test of its own</h3>
 *
 * <p>Twelve endpoints were added across ADR-007 and none of them made an authentication
 * decision. They are protected — {@code ProdSecurityConfig} ends in
 * {@code anyRequest().authenticated()}, so anything not enumerated is closed by default, which
 * is the right way round. But "protected because nobody listed it" and "protected because
 * somebody decided" look identical from the outside, and only one of them survives a future
 * matcher being widened. The prod chain already permits {@code GET /api/v1/maze/*}; a single
 * careless {@code /api/v1/maze/**} would silently make the whole analytical surface public, and
 * before this test nothing in the suite would have noticed.
 *
 * <p>What existed before: {@code SecurityConfigProfileTest} checks the {@code @Profile}
 * annotations and no actual decision, and {@code ProdProfileBootTest} pins exactly one path.
 * The README publishes an "Auth (prod)" column for the whole API and nothing kept it honest.
 *
 * <h3>The mistake the first version of this test made</h3>
 *
 * <p>Version one of the table below was filled in from what the running server actually
 * answered. It passed, and it was wrong: a test written from observed behaviour agrees with the
 * behaviour by construction and can therefore never find a behaviour bug. Four endpoints the
 * README documents as <b>public</b> — the {@code #session=} spectator permalink, its tour
 * progress, the ghost racer and the free agent re-poll — were being refused in prod by the
 * default-deny rule, so three shipped, documented features did not work there at all. Writing
 * "AUTHENTICATED" next to them made the discrepancy permanent instead of visible. The fix was in
 * {@code ProdSecurityConfig}, not here, and the guard against a repeat is
 * {@link #theReadmeAuthColumnMatchesTheEnforcedPosture()}: the specification and the enforcement
 * are now two independent sources that have to agree.
 *
 * <p>So there are three tests. {@link #everyEndpointHasTheAuthPostureItIsSupposedTo()} drives
 * real unauthenticated requests against a booted prod context.
 * {@link #everyMappingInTheControllersAppearsInTheTable()} scans the controller sources so a new
 * endpoint fails the build until somebody writes down which side of the line it belongs on.
 * {@link #theReadmeAuthColumnMatchesTheEnforcedPosture()} holds the published API table to the
 * same standard, in both directions.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "daedalus.security.jwt.secret=prod-auth-posture-secret-32-bytes!!",
        "daedalus.security.admin.password-bcrypt="
                + "$2a$10$7EqJtq98hPqEX7fNZaFWoOhi5B0h6C1JcqIcnLmVjKobXAB9Zwmqu",
        "daedalus.redis.enabled=false",
        "daedalus.plugins.scan-on-startup=false",
})
@ActiveProfiles("prod")
class ProdAuthPostureTest {

    private enum Posture { PUBLIC, AUTHENTICATED }

    private static final String ID = "11111111-2222-3333-4444-555555555555";

    /**
     * The posture every endpoint is supposed to have in prod, and the README's "Auth (prod)"
     * column made executable.
     *
     * <p>{@code PUBLIC} entries are a deliberate, short list: the login endpoint itself, the
     * algorithm catalogue, reading one maze by id (which the daily-challenge link depends on),
     * the leaderboard, and the four read-only routes a shared link has to reach. Everything else
     * costs the server real work or lets a caller change state, and is closed.
     */
    private static final Map<String, Posture> EXPECTED = new LinkedHashMap<>();

    static {
        // --- deliberately public ---
        EXPECTED.put("POST /api/v1/auth/login", Posture.PUBLIC);
        EXPECTED.put("GET /api/v1/algorithms", Posture.PUBLIC);
        EXPECTED.put("GET /api/v1/maze/" + ID, Posture.PUBLIC);
        EXPECTED.put("GET /api/v1/maze/daily", Posture.PUBLIC);
        EXPECTED.put("GET /api/v1/leaderboard", Posture.PUBLIC);
        // The share-a-link surface. Read-only, UUID-keyed, and useless if it needs the one
        // account this system has — a spectator link only the operator can open is not one.
        EXPECTED.put("GET /api/v1/session/" + ID, Posture.PUBLIC);
        EXPECTED.put("GET /api/v1/session/" + ID + "/tour", Posture.PUBLIC);
        EXPECTED.put("GET /api/v1/maze/" + ID + "/ghost", Posture.PUBLIC);
        EXPECTED.put("GET /api/v1/agent/" + ID, Posture.PUBLIC);

        // --- everything that costs work or touches state ---
        EXPECTED.put("POST /api/v1/maze/generate", Posture.AUTHENTICATED);
        EXPECTED.put("POST /api/v1/maze/breed", Posture.AUTHENTICATED);
        EXPECTED.put("POST /api/v1/maze/" + ID + "/live", Posture.AUTHENTICATED);
        EXPECTED.put("POST /api/v1/maze/" + ID + "/traffic", Posture.AUTHENTICATED);
        EXPECTED.put("POST /api/v1/maze/" + ID + "/solve/astar", Posture.AUTHENTICATED);
        EXPECTED.put("POST /api/v1/maze/" + ID + "/session", Posture.AUTHENTICATED);
        EXPECTED.put("POST /api/v1/maze/" + ID + "/agent", Posture.AUTHENTICATED);
        EXPECTED.put("POST /api/v1/agent/" + ID + "/step", Posture.AUTHENTICATED);
        EXPECTED.put("POST /api/v1/session/" + ID + "/move", Posture.AUTHENTICATED);
        EXPECTED.put("POST /api/v1/session/" + ID + "/join", Posture.AUTHENTICATED);
        EXPECTED.put("GET /api/v1/campaign", Posture.AUTHENTICATED);
        EXPECTED.put("GET /api/v1/complexity", Posture.AUTHENTICATED);
        EXPECTED.put("GET /api/v1/complexity/metrics", Posture.AUTHENTICATED);
        EXPECTED.put("GET /api/v1/tournament", Posture.AUTHENTICATED);
        EXPECTED.put("GET /api/v1/maze/" + ID + "/analysis", Posture.AUTHENTICATED);
        EXPECTED.put("GET /api/v1/maze/" + ID + "/fingerprint", Posture.AUTHENTICATED);
        EXPECTED.put("GET /api/v1/maze/" + ID + "/tour", Posture.AUTHENTICATED);
        EXPECTED.put("GET /api/v1/maze/" + ID + "/hardest-route", Posture.AUTHENTICATED);
        EXPECTED.put("GET /api/v1/maze/" + ID + "/distance-field", Posture.AUTHENTICATED);
        EXPECTED.put("GET /api/v1/maze/" + ID + "/sanctuaries", Posture.AUTHENTICATED);
        EXPECTED.put("GET /api/v1/maze/" + ID + "/heuristic-lens", Posture.AUTHENTICATED);
        // Bare @GetMapping on PluginController — invisible to the first version of the source
        // scanner below, and therefore the one endpoint in the API with no posture on record.
        EXPECTED.put("GET /api/v1/plugins", Posture.AUTHENTICATED);
        EXPECTED.put("GET /api/v1/plugins/describe", Posture.AUTHENTICATED);
    }

    @LocalServerPort
    private int port;

    @Test
    void everyEndpointHasTheAuthPostureItIsSupposedTo() {
        RestTestClient client = RestTestClient.bindToServer()
                .baseUrl("http://localhost:" + port).build();

        List<String> wrong = new ArrayList<>();
        EXPECTED.forEach((signature, posture) -> {
            String[] parts = signature.split(" ", 2);
            HttpMethod method = HttpMethod.valueOf(parts[0]);
            int status = client.method(method).uri(parts[1]).exchange()
                    .returnResult(Void.class).getStatus().value();
            boolean refused = status == 401 || status == 403;

            if (posture == Posture.AUTHENTICATED && !refused) {
                wrong.add(signature + " should require auth but answered " + status);
            }
            if (posture == Posture.PUBLIC && refused) {
                wrong.add(signature + " should be public but answered " + status);
            }
        });

        assertThat(wrong)
                .as("prod authentication posture does not match what the API documents: %s", wrong)
                .isEmpty();
    }

    @Test
    void everyMappingInTheControllersAppearsInTheTable() throws IOException {
        // Completeness. Without this, the table above is only as good as whoever last remembered
        // to extend it, which is the exact failure mode the config, cache, rate-limit and
        // coverage audits each found in their own area. A new endpoint must fail here until an
        // explicit posture is recorded for it.
        var covered = new TreeSet<String>();
        EXPECTED.keySet().forEach(k -> covered.add(normalise(k)));

        var found = new TreeSet<String>();
        int annotations = 0;
        int parsed = 0;
        Path root = Path.of("src/main/java/com/daedalus/server/controller");
        try (Stream<Path> files = Files.walk(root)) {
            for (Path file : files.filter(f -> f.toString().endsWith(".java")).toList()) {
                String text = Files.readString(file);
                // Controllers carry their own class-level base path — AuthController is mounted
                // at /api/v1/auth, PluginController at /api/v1/plugins — so assuming a bare
                // /api/v1 prefix invents endpoints that do not exist and misses the real ones.
                Matcher base = Pattern.compile(
                        "@RequestMapping\\(\"([^\"]+)\"\\)").matcher(text);
                String prefix = base.find() ? base.group(1) : "";

                Matcher bare = BARE.matcher(text);
                while (bare.find()) {
                    annotations++;
                }
                Matcher m = MAPPING.matcher(text);
                while (m.find()) {
                    parsed++;
                    found.add(normalise(
                            m.group(1).toUpperCase() + " " + prefix + pathOf(m.group(3))));
                }
            }
        }

        // The parity check is the point. Version one of this scanner required a parenthesised
        // string literal, so it silently skipped PluginController's bare `@GetMapping` and
        // MazeController's `@GetMapping(value = ..., produces = ...)`. A scanner that misses an
        // annotation form reports a clean sweep of the endpoints it can see, which is the
        // failure mode this whole family of audit tests keeps finding. Counting annotations
        // independently of parsing them means a form the parser does not understand fails here
        // rather than disappearing.
        assertThat(annotations).as("the scanner found no mappings at all, so it is broken")
                .isGreaterThan(20);
        assertThat(parsed)
                .as("the scanner saw %d mapping annotations but could only parse %d — some "
                        + "annotation form is being skipped, and whatever it declares is "
                        + "unaudited", annotations, parsed)
                .isEqualTo(annotations);

        var missing = new TreeSet<>(found);
        missing.removeAll(covered);
        assertThat(missing)
                .as("these endpoints exist but no prod auth posture is recorded for them: %s",
                        missing)
                .isEmpty();
    }

    @Test
    void theReadmeAuthColumnMatchesTheEnforcedPosture() throws IOException {
        // Two independent sources for one fact: the README says what the API promises, the boot
        // test above says what the server does. Version one of this class only had the second,
        // so four endpoints documented public and enforced closed agreed with themselves and
        // nothing noticed. Both directions are checked — a row the README omits is as much a
        // defect as a row it gets wrong, and it omitted two.
        Path readme = Path.of("..", "README.md");
        assertThat(Files.exists(readme)).as("README.md not found at %s", readme.toAbsolutePath())
                .isTrue();

        Map<String, Posture> documented = new LinkedHashMap<>();
        boolean inTable = false;
        for (String line : Files.readAllLines(readme)) {
            if (line.startsWith("| Method ") && line.contains("Auth (prod)")) {
                inTable = true;
                continue;
            }
            if (!inTable) {
                continue;
            }
            if (!line.startsWith("|")) {
                break;
            }
            Matcher row = README_ROW.matcher(line);
            if (row.find()) {
                String path = row.group(2).split("\\?", 2)[0];
                documented.put(normalise(row.group(1) + " " + path),
                        "public".equals(row.group(3)) ? Posture.PUBLIC : Posture.AUTHENTICATED);
            }
        }

        assertThat(documented).as("the README API table did not parse, so this test is blind")
                .hasSizeGreaterThan(20);

        Map<String, Posture> enforced = new LinkedHashMap<>();
        EXPECTED.forEach((k, v) -> enforced.put(normalise(k), v));

        List<String> disagreements = new ArrayList<>();
        enforced.forEach((sig, posture) -> {
            Posture doc = documented.get(sig);
            if (doc == null) {
                disagreements.add(sig + ": enforced " + posture + ", absent from the README table");
            } else if (doc != posture) {
                disagreements.add(sig + ": README says " + doc + ", prod enforces " + posture);
            }
        });
        documented.keySet().stream().filter(sig -> !enforced.containsKey(sig))
                .forEach(sig -> disagreements.add(sig + ": documented but not in the posture table"));

        assertThat(disagreements)
                .as("the README's Auth (prod) column and the enforced posture disagree: %s",
                        disagreements)
                .isEmpty();
    }

    /**
     * Accepts every mapping form the codebase actually uses: {@code @GetMapping},
     * {@code @GetMapping("/x")} and {@code @GetMapping(value = "/x", produces = ...)}.
     */
    private static final Pattern MAPPING = Pattern.compile(
            "@(Get|Post|Put|Patch|Delete)Mapping\\b\\s*(\\(([^)]*)\\))?");

    private static final Pattern BARE =
            Pattern.compile("@(?:Get|Post|Put|Patch|Delete)Mapping\\b");

    private static final Pattern NAMED_PATH =
            Pattern.compile("(?:value|path)\\s*=\\s*\"([^\"]*)\"");

    private static final Pattern LITERAL = Pattern.compile("\"(/[^\"]*)\"");

    private static final Pattern README_ROW = Pattern.compile(
            "^\\|\\s*`(\\w+)`\\s*\\|\\s*`([^`]+)`\\s*\\|\\s*(public|required)\\s*\\|");

    /** Pull the mapped path out of an annotation's argument list, if it declares one. */
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

    /** Collapse concrete ids and path variables to {@code *} so the two sources compare. */
    private static String normalise(String signature) {
        return signature
                .replace(ID, "*")
                .replaceAll("\\{[^}]+}", "*")
                .replaceAll("/astar", "/*")
                .replaceAll("/+$", "");
    }
}
