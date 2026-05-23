// SPDX-License-Identifier: MIT

package com.daedalus.plugin;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;

/**
 * Locks in the SPI polish from {@code FULL_PROJECT_AUDIT.md}: the {@link PluginManifest}
 * compact constructor must reject {@code null} for the three required fields ({@code id},
 * {@code displayName}, {@code version}) and normalise a {@code null} {@code requires} array
 * into an empty array so dependency-sorting code never trips a NPE.
 *
 * <p>The remaining fields ({@code author}, {@code description}) are intentionally allowed
 * to be {@code null} — many internal/test plugins don't bother filling them in.
 */
class PluginManifestNullGuardTest {

    /* ---------- required fields ---------- */

    @Test
    void rejectsNullId() {
        assertThatNullPointerException()
                .isThrownBy(() -> new PluginManifest(
                        null, "Display", "1.0", "author", "description"))
                .withMessageContaining("id");
    }

    @Test
    void rejectsNullDisplayName() {
        assertThatNullPointerException()
                .isThrownBy(() -> new PluginManifest(
                        "my-plugin", null, "1.0", "author", "description"))
                .withMessageContaining("displayName");
    }

    @Test
    void rejectsNullVersion() {
        assertThatNullPointerException()
                .isThrownBy(() -> new PluginManifest(
                        "my-plugin", "Display", null, "author", "description"))
                .withMessageContaining("version");
    }

    /* ---------- optional fields ---------- */

    @Test
    void allowsNullAuthorAndDescription() {
        // Convenience constructor passes through null for these two — the registry and the
        // REST surface tolerate it. We just want to confirm construction succeeds.
        PluginManifest m = new PluginManifest("my-plugin", "Display", "1.0", null, null);
        assertThat(m.author()).isNull();
        assertThat(m.description()).isNull();
        assertThat(m.requires()).isEmpty();
    }

    @Test
    void normalisesNullRequiresIntoEmptyArray() {
        // Direct call to the canonical (6-arg) constructor with a null requires array — the
        // compact constructor should swap it for an empty array so dependency iteration is
        // null-safe.
        PluginManifest m = new PluginManifest(
                "my-plugin", "Display", "1.0", "author", "description", null);
        assertThat(m.requires()).isNotNull().isEmpty();
    }

    /* ---------- MazePlugin.version() default ---------- */

    @Test
    void mazePluginVersionDefault_delegatesToManifest() {
        // Tiny anonymous plugin — only manifest() is overridden, version() should fall through
        // to the default that reads manifest().version().
        MazePlugin plugin = () -> new PluginManifest("v-test", "V Test", "9.9.9", null, null);
        assertThat(plugin.version()).isEqualTo("9.9.9");
    }

    /* ---------- happy path ---------- */

    @Test
    void allFieldsPopulatedRoundTrip() {
        PluginManifest m = new PluginManifest(
                "biome-pack", "Biome Pack", "0.4.2", "Anthropic", "Adds biome generators",
                new String[] {"core-themes"});
        assertThat(m.id()).isEqualTo("biome-pack");
        assertThat(m.displayName()).isEqualTo("Biome Pack");
        assertThat(m.version()).isEqualTo("0.4.2");
        assertThat(m.author()).isEqualTo("Anthropic");
        assertThat(m.description()).isEqualTo("Adds biome generators");
        assertThat(m.requires()).containsExactly("core-themes");
    }
}
