// SPDX-License-Identifier: MIT

package com.daedalus.server.plugintest;

import com.daedalus.plugin.MazePlugin;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.client.RestTestClient;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.jar.JarEntry;
import java.util.jar.JarOutputStream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The plugin SPI, end to end through a real server: a JAR on disk → discovery → lifecycle →
 * registry → the REST catalog → an actual generation over HTTP. Every prior plugin test
 * stopped at the runtime module; nothing proved the server's wiring of the same chain — and
 * that wiring was in fact broken twice over (see {@code PluginConfig}'s config-audit note:
 * the directory property name didn't match the config, and {@code scan-on-startup} was read
 * by nothing). This test fails against both pre-fix bugs: with the directory ignored the JAR
 * is never found, and it is the pin that keeps {@code scan-on-startup} honest.
 *
 * <p>The JAR is packaged at test time from the fixture's compiled class files, the same
 * recipe as the runtime module's discovery tests. Fresh context by construction (unique
 * property values), so this is one of the suite's expensive tests — deliberately, since a
 * cached context cannot prove startup wiring.
 *
 * <p>Shutdown is the other half of the same wiring and is pinned by
 * {@link com.daedalus.server.config.PluginHostShutdownTest}: this class must not close the
 * Spring Test-managed context mid-method.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class PluginSpiEndToEndTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final Path PLUGIN_DIR = buildPluginDir();

    @DynamicPropertySource
    static void pluginProperties(DynamicPropertyRegistry registry) {
        registry.add("daedalus.plugins.directory", () -> PLUGIN_DIR.toAbsolutePath().toString());
        registry.add("daedalus.plugins.scan-on-startup", () -> "true");
    }

    @LocalServerPort
    private int port;

    @Test
    void aPluginJarOnDiskContributesAGeneratorReachableOverRest() throws Exception {
        RestTestClient client = RestTestClient.bindToServer()
                .baseUrl("http://localhost:" + port).build();

        // 1. The catalog lists the plugin's generator alongside the built-ins.
        JsonNode algorithms = MAPPER.readTree(client.get().uri("/api/v1/algorithms")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        List<String> ids = new ArrayList<>();
        algorithms.get("generators").forEach(g -> ids.add(g.get("id").asText()));
        assertThat(ids).contains("plugin-echo", "recursive-backtracker");

        // 2. And it actually generates over HTTP — registration, not just listing.
        JsonNode maze = MAPPER.readTree(client.post().uri("/api/v1/maze/generate")
                .header("Content-Type", "application/json")
                .body("{\"generatorId\":\"plugin-echo\",\"rows\":8,\"cols\":8,\"seed\":7}")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        assertThat(maze.get("generatorId").asText()).isEqualTo("plugin-echo");

        // 3. The ops surface agrees with the product surface.
        JsonNode actuate = MAPPER.readTree(client.get().uri("/actuator/algorithms")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        List<String> opsIds = new ArrayList<>();
        actuate.get("generators").forEach(g -> opsIds.add(g.get("id").asText()));
        assertThat(opsIds).contains("plugin-echo");

        // 4. The plugin introspection endpoint reports it loaded and healthy.
        JsonNode plugins = MAPPER.readTree(client.get().uri("/api/v1/plugins")
                .exchange().expectStatus().isOk()
                .expectBody().returnResult().getResponseBody());
        boolean listed = false;
        for (JsonNode p : plugins) {
            if ("echo-plugin".equals(p.get("id").asText())) {
                listed = true;
                assertThat(p.get("state").asText()).isEqualTo("STARTED");
            }
        }
        assertThat(listed).as("/api/v1/plugins lists the loaded plugin").isTrue();
    }

    /* ---------------------------------------------------------------------- */
    /* JAR packaging — the runtime discovery tests' recipe, fixture classes    */
    /* read from this module's test classpath.                                 */
    /* ---------------------------------------------------------------------- */

    private static Path buildPluginDir() {
        try {
            Path dir = Files.createTempDirectory("daedalus-spi-e2e-plugins");
            Path jarPath = dir.resolve("echo-plugin.jar");
            String pluginResource = EchoPlugin.class.getName().replace('.', '/') + ".class";
            String generatorResource =
                    EchoPlugin.EchoGenerator.class.getName().replace('.', '/') + ".class";

            try (JarOutputStream jar = new JarOutputStream(Files.newOutputStream(jarPath))) {
                for (String resource : List.of(pluginResource, generatorResource)) {
                    jar.putNextEntry(new JarEntry(resource));
                    jar.write(classBytes(resource));
                    jar.closeEntry();
                }
                jar.putNextEntry(new JarEntry("META-INF/services/" + MazePlugin.class.getName()));
                jar.write((EchoPlugin.class.getName() + "\n").getBytes(StandardCharsets.UTF_8));
                jar.closeEntry();
            }
            return dir;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static byte[] classBytes(String resource) throws IOException {
        try (InputStream in = PluginSpiEndToEndTest.class.getClassLoader()
                .getResourceAsStream(resource)) {
            if (in == null) {
                throw new IllegalStateException("fixture class not on test classpath: " + resource);
            }
            return in.readAllBytes();
        }
    }
}
