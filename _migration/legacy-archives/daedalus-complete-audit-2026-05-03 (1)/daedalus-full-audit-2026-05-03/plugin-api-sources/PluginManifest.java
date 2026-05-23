package com.daedalus.plugin;

/**
 * Plugin metadata. Surfaced via {@code GET /api/plugins} so clients can list everything
 * loaded.
 */
public record PluginManifest(
        String id,           // unique slug, e.g. "biome-generators"
        String displayName,
        String version,
        String author,
        String description,
        String[] requires    // ids of other plugins this depends on (loaded first)
) {
    public PluginManifest(String id, String displayName, String version, String author, String description) {
        this(id, displayName, version, author, description, new String[0]);
    }
}
