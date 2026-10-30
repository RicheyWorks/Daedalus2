// SPDX-License-Identifier: MIT

package com.daedalus.server.ratelimit;

import org.junit.jupiter.api.Test;
import org.yaml.snakeyaml.Yaml;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Every endpoint that changes server state must cost the caller something.
 *
 * <h3>The measurement behind this</h3>
 *
 * <p>An audit counted the annotations: 10 of 32 endpoints carried no {@code @PerKeyRateLimit}.
 * Most were cheap reads and fine. One was not — {@code POST /session/{id}/move}, which mutates
 * the session, feeds traffic tracking and ghost recording, and publishes a
 * {@code PlayerMovedEvent} to every plugin listener <em>synchronously, inside the session lock</em>.
 *
 * <p>Measured against the running server on the default profile, the contrast with its own twin
 * was stark:
 *
 * <pre>
 *   POST /session/{id}/move   1206 accepted in 6.0 s (201/s) — never throttled
 *   POST /agent/{id}/step     1200 accepted, then 429       — agentStep budget, working
 * </pre>
 *
 * <p>Both are "hundreds of tiny state-mutating requests by design"; the agent endpoint's own
 * config comment says exactly that as the reason it has a budget. The player endpoint had none,
 * and would have sustained roughly ten times the rate its twin was allowed. That is the kind of
 * gap that opens quietly: nobody removed the annotation, it was simply never added, and no test
 * was watching the set.
 *
 * <h3>Why writes only</h3>
 *
 * <p>The rule is deliberately scoped to POST/PUT/PATCH/DELETE. The unlimited reads — the
 * algorithm catalogue, a maze by id, the leaderboard, a session view — serve cached state and
 * bounding them would cost more than it buys. Extending the rule to GET would force a dozen
 * annotations whose only effect is noise, and a rule everyone waives is worse than no rule.
 */
class RateLimitCoverageTest {

    private static final Pattern MAPPING = Pattern.compile(
            "@(Post|Put|Patch|Delete)Mapping\\s*\\(([^)]*)\\)");

    /**
     * Write endpoints that are deliberately unmetered.
     *
     * <p>Empty, and worth keeping that way. An entry here is a claim that a state change costs
     * the server nothing worth bounding, which should be rare enough to argue for individually.
     */
    private static final Set<String> INTENTIONALLY_UNMETERED = Set.of();

    @Test
    void everyStateChangingEndpointIsRateLimited() throws IOException {
        List<String> unmetered = new ArrayList<>();
        int writeEndpoints = 0;

        for (Path file : controllerSources()) {
            String text = Files.readString(file);
            Matcher m = MAPPING.matcher(text);
            while (m.find()) {
                writeEndpoints++;
                int signatureStart = text.indexOf("public", m.end());
                String annotations = signatureStart < 0
                        ? text.substring(m.end()) : text.substring(m.end(), signatureStart);
                String name = file.getFileName() + " " + m.group(1).toUpperCase() + " " + m.group(2);
                if (!annotations.contains("@PerKeyRateLimit")
                        && !INTENTIONALLY_UNMETERED.contains(name)) {
                    unmetered.add(name);
                }
            }
        }

        assertThat(writeEndpoints)
                .as("the scanner found no write endpoints at all, so it is broken")
                .isGreaterThanOrEqualTo(8);
        assertThat(unmetered)
                .as("these endpoints change server state with no per-caller cost: %s", unmetered)
                .isEmpty();
    }

    @Test
    void everyBudgetNamedInCodeIsConfigured() throws IOException {
        Set<String> named = new TreeSet<>();
        Pattern budget = Pattern.compile("@PerKeyRateLimit\\(\"([^\"]+)\"\\)");
        for (Path file : controllerSources()) {
            Matcher m = budget.matcher(Files.readString(file));
            while (m.find()) {
                named.add(m.group(1));
            }
        }

        Set<String> configured = configuredLimiters();
        Set<String> missing = new TreeSet<>(named);
        missing.removeAll(configured);

        assertThat(named).as("no budgets found — the scanner is broken").isNotEmpty();
        assertThat(missing)
                .as("a @PerKeyRateLimit naming an instance that application.yml does not define "
                        + "silently limits nothing: %s", missing)
                .isEmpty();
    }

    @Test
    void everyConfiguredBudgetIsActuallyUsed() throws IOException {
        Set<String> named = new TreeSet<>();
        Pattern budget = Pattern.compile("@PerKeyRateLimit\\(\"([^\"]+)\"\\)");
        for (Path file : controllerSources()) {
            Matcher m = budget.matcher(Files.readString(file));
            while (m.find()) {
                named.add(m.group(1));
            }
        }

        Set<String> unused = new TreeSet<>(configuredLimiters());
        unused.removeAll(named);

        assertThat(unused)
                .as("application.yml configures these limiter instances but no endpoint names "
                        + "them — a budget guarding nothing: %s", unused)
                .isEmpty();
    }

    private static List<Path> controllerSources() throws IOException {
        Path root = Path.of("src/main/java/com/daedalus/server/controller");
        assertThat(Files.isDirectory(root))
                .as("expected to run from the daedalus-server module directory").isTrue();
        try (Stream<Path> files = Files.walk(root)) {
            return files.filter(p -> p.toString().endsWith(".java")).sorted().toList();
        }
    }

    @SuppressWarnings("unchecked")
    private static Set<String> configuredLimiters() throws IOException {
        try (InputStream in = Files.newInputStream(Path.of("src/main/resources/application.yml"))) {
            Map<String, Object> root = new Yaml().load(in);
            Map<String, Object> r4j = (Map<String, Object>) root.get("resilience4j");
            Map<String, Object> limiter = (Map<String, Object>) r4j.get("ratelimiter");
            Map<String, Object> instances = (Map<String, Object>) limiter.get("instances");
            return new LinkedHashSet<>(instances.keySet());
        }
    }
}
