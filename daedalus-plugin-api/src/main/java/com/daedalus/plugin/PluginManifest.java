// SPDX-License-Identifier: MIT

package com.daedalus.plugin;

import java.util.Objects;

/**
 * Plugin metadata. Surfaced via {@code GET /api/plugins} so clients can list everything
 * loaded.
 *
 * <p><b>Required fields</b> (rejected at construction time when {@code null}):
 * {@link #id()}, {@link #displayName()}, {@link #version()}.
 *
 * <p><b>Optional fields</b>: {@link #author()}, {@link #description()}, {@link #requires()}.
 * The compact constructor normalises a {@code null} {@code requires} to an empty array so
 * downstream code (the registry's dependency sort, the REST surface) can iterate without
 * null checks.
 *
 * @since 1.0
 */
public record PluginManifest(
        String id,           // unique slug, e.g. "biome-generators"
        String displayName,
        String version,
        String author,
        String description,
        String[] requires    // ids of other plugins this depends on (loaded first)
) {
    /**
     * Compact constructor — enforces non-null required fields and normalises optional ones.
     * Plugin authors typically don't call this directly; they use the 5-arg convenience
     * constructor below or the 6-arg canonical form when they have explicit dependencies.
     *
     * @throws NullPointerException if {@code id}, {@code displayName}, or {@code version}
     *                              is {@code null}.
     */
    public PluginManifest {
        Objects.requireNonNull(id, "PluginManifest.id must not be null");
        Objects.requireNonNull(displayName, "PluginManifest.displayName must not be null");
        Objects.requireNonNull(version, "PluginManifest.version must not be null");
        if (requires == null) requires = new String[0];
    }

    /** Convenience constructor for plugins with no declared dependencies on other plugins. */
    public PluginManifest(String id, String displayName, String version, String author, String description) {
        this(id, displayName, version, author, description, new String[0]);
    }
}
