// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.junit.jupiter.api.Test;
import org.yaml.snakeyaml.Yaml;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
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
 * Keeps {@code application.yml} and the {@code @Value} annotations honest about each other.
 *
 * <h3>Why this exists</h3>
 *
 * <p>An audit after ADR-007 found five configuration blocks that the code reads and the shipped
 * {@code application.yml} never mentions, and — worse — two keys the yml documents that nothing
 * reads:
 *
 * <pre>
 *   daedalus.cache.maze-cache-size:        256    (documented, dead)
 *   daedalus.cache.maze-cache-ttl-minutes:  30    (documented, dead)
 *   daedalus.maze.cache.max-size:         5000    (live, undocumented)
 *   daedalus.maze.cache.idle-ttl:           2h    (live, undocumented)
 * </pre>
 *
 * <p>So the file told an operator the maze cache held 256 entries for half an hour, while the
 * service actually held 5,000 for two — a twentyfold difference in footprint — and tuning the
 * documented knob did nothing at all. Undocumented configuration is a nuisance; configuration
 * that is documented and inert is a lie, and it is the kind that survives review because the
 * value looks deliberate.
 *
 * <p>Both directions are checked, because each catches a different mistake: a key in the code but
 * not the file is an operator who cannot find the knob, and a key in the file but not the code is
 * an operator turning a knob attached to nothing.
 */
class ConfigCoverageTest {

    private static final Pattern VALUE_KEY =
            Pattern.compile("\\$\\{(daedalus\\.[A-Za-z0-9.-]+?)(?::|})");

    /** {@code @ConfigurationProperties("daedalus.x")} — a whole subtree bound without any @Value. */
    private static final Pattern PROPERTIES_PREFIX =
            Pattern.compile("@ConfigurationProperties\\(\"(daedalus\\.[A-Za-z0-9.-]+)\"\\)");

    /**
     * Keys that are deliberately absent from {@code application.yml}.
     *
     * <p>Kept deliberately short. Anything here should be a knob whose default is correct
     * everywhere and which exists only so a test or a profile can override it.
     */
    private static final Set<String> INTENTIONALLY_UNDOCUMENTED = Set.of(
            "daedalus.session.multiplayer",   // opt-in feature flag, off unless a profile sets it
            "daedalus.redis.enabled");        // set per profile (dev off, prod on), never here

    @Test
    void everyConfigKeyTheCodeReadsIsDocumentedInApplicationYml() throws IOException {
        Set<String> used = keysReferencedInSource();
        Set<String> documented = keysDeclaredInYaml();

        Set<String> missing = new TreeSet<>(used);
        missing.removeAll(documented);
        missing.removeAll(INTENTIONALLY_UNDOCUMENTED);

        assertThat(missing)
                .as("these keys are read by @Value but appear nowhere in application.yml, so an "
                        + "operator has no way to discover them: %s", missing)
                .isEmpty();
    }

    @Test
    void everyKeyApplicationYmlDeclaresIsActuallyReadBySomething() throws IOException {
        Set<String> used = keysReferencedInSource();
        Set<String> boundPrefixes = configurationPropertiesPrefixes();
        Set<String> documented = keysDeclaredInYaml();

        // A @ConfigurationProperties class binds a whole subtree without a single ${...}, so a
        // scanner that only knows about @Value would report every security and rate-limit key as
        // dead. That is a false positive, and reporting eight of them alongside two real ones is
        // how a useful check gets muted.
        Set<String> dead = new TreeSet<>(documented);
        dead.removeAll(used);
        dead.removeIf(key -> boundPrefixes.stream().anyMatch(p -> key.startsWith(p + ".")));

        assertThat(dead)
                .as("application.yml documents these keys but no @Value reads them — a knob "
                        + "attached to nothing, which reads as a deliberate setting: %s", dead)
                .isEmpty();
    }

    /** Every {@code ${daedalus.x.y}} referenced from the server's main sources. */
    private static Set<String> keysReferencedInSource() throws IOException {
        Set<String> keys = new LinkedHashSet<>();
        Path root = Path.of("src/main/java");
        assertThat(Files.isDirectory(root))
                .as("expected to run from the daedalus-server module directory")
                .isTrue();
        try (Stream<Path> files = Files.walk(root)) {
            for (Path file : files.filter(p -> p.toString().endsWith(".java")).toList()) {
                Matcher m = VALUE_KEY.matcher(Files.readString(file, StandardCharsets.UTF_8));
                while (m.find()) {
                    keys.add(m.group(1));
                }
            }
        }
        assertThat(keys).as("the scanner found no keys at all, so it is broken").isNotEmpty();
        return keys;
    }

    /** Prefixes bound wholesale by a {@code @ConfigurationProperties} class. */
    private static Set<String> configurationPropertiesPrefixes() throws IOException {
        Set<String> prefixes = new LinkedHashSet<>();
        try (Stream<Path> files = Files.walk(Path.of("src/main/java"))) {
            for (Path file : files.filter(p -> p.toString().endsWith(".java")).toList()) {
                Matcher m = PROPERTIES_PREFIX.matcher(
                        Files.readString(file, StandardCharsets.UTF_8));
                while (m.find()) {
                    prefixes.add(m.group(1));
                }
            }
        }
        return prefixes;
    }

    /** Every leaf under {@code daedalus:} in application.yml, flattened to dotted keys. */
    private static Set<String> keysDeclaredInYaml() throws IOException {
        try (InputStream in = Files.newInputStream(Path.of("src/main/resources/application.yml"))) {
            Map<String, Object> root = new Yaml().load(in);
            Object daedalus = root.get("daedalus");
            assertThat(daedalus).as("application.yml has no daedalus block").isNotNull();
            Set<String> keys = new LinkedHashSet<>();
            flatten("daedalus", daedalus, keys);
            return keys;
        }
    }

    @SuppressWarnings("unchecked")
    private static void flatten(String prefix, Object node, Set<String> out) {
        if (node instanceof Map<?, ?> map) {
            map.forEach((k, v) -> flatten(prefix + "." + k, v, out));
        } else if (!(node instanceof List<?>)) {
            out.add(prefix);
        }
    }

    @Test
    void theConfigurationPropertiesEscapeHatchIsNarrow_notABlanketExemption() throws IOException {
        // A guard on the guard. The dead-key check forgives anything under a
        // @ConfigurationProperties prefix, which is correct but is also the obvious place for
        // this test to quietly stop working — one prefix of "daedalus" would forgive everything.
        Set<String> prefixes = configurationPropertiesPrefixes();

        assertThat(prefixes)
                .as("the scanner must actually find the binding classes")
                .isNotEmpty()
                .allSatisfy(p -> assertThat(p)
                        .as("a prefix this broad would exempt the entire config tree")
                        .isNotEqualTo("daedalus")
                        .startsWith("daedalus."));
        assertThat(keysDeclaredInYaml()).anyMatch(k -> k.startsWith("daedalus.security."));
    }
}
