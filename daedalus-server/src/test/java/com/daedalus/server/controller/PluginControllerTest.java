// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.plugin.PluginLifecycle;
import com.daedalus.plugin.PluginManifest;
import com.daedalus.plugin.runtime.PluginManager;
import com.daedalus.plugin.runtime.PluginRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;

import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.nullValue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Slice test for {@code PluginController} — previously the only coverage this controller had was
 * {@code ApplicationSmokeTest} proving {@code /api/v1/plugins} appears in the OpenAPI document,
 * which says nothing about what the endpoint returns.
 *
 * <p>Pins the {@code PluginInfo} projection (id, lifecycle state name, embedded manifest, and the
 * stringified error), the empty-registry shape (an empty JSON array, not an error), and the
 * failure passthrough that lets operators see <em>why</em> a plugin died without grepping logs.
 *
 * <p>Standalone {@code MockMvc} setup, matching the other controller slices — auth posture for
 * this read-only endpoint is governed by {@code SecurityConfig}'s HTTP rules, which have their
 * own tests.
 */
class PluginControllerTest {

    private PluginManager manager;
    private PluginRegistry registry;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        manager = mock(PluginManager.class);
        registry = mock(PluginRegistry.class);
        when(manager.registry()).thenReturn(registry);
        mvc = MockMvcBuilders.standaloneSetup(new PluginController(manager)).build();
    }

    @Test
    void list_projectsRegistryEntriesIntoPluginInfo() throws Exception {
        PluginManifest manifest = new PluginManifest(
                "biome-generators", "Biome Generators", "1.2.0", "richey", "Adds biome mazes");
        when(registry.all()).thenReturn(List.of(
                new PluginRegistry.Entry(null, manifest, PluginLifecycle.STARTED, null)));

        mvc.perform(get("/api/v1/plugins"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].id", equalTo("biome-generators")))
                .andExpect(jsonPath("$[0].state", equalTo("STARTED")))
                .andExpect(jsonPath("$[0].manifest.version", equalTo("1.2.0")))
                .andExpect(jsonPath("$[0].manifest.displayName", equalTo("Biome Generators")))
                .andExpect(jsonPath("$[0].error", nullValue()));
    }

    @Test
    void list_surfacesTheFailureCauseForFailedPlugins() throws Exception {
        PluginManifest manifest = new PluginManifest(
                "broken-plugin", "Broken Plugin", "0.1.0", "someone", "Throws on start");
        when(registry.all()).thenReturn(List.of(
                new PluginRegistry.Entry(null, manifest, PluginLifecycle.FAILED,
                        new IllegalStateException("boom during start"))));

        mvc.perform(get("/api/v1/plugins"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].state", equalTo("FAILED")))
                .andExpect(jsonPath("$[0].error",
                        equalTo("java.lang.IllegalStateException: boom during start")));
    }

    @Test
    void list_returnsAnEmptyArrayWhenNoPluginsAreLoaded() throws Exception {
        // The common case for a fresh checkout (no plugin dir). Must be [] with 200 — clients
        // iterate the list; a 404 or error envelope here would break them for no reason.
        when(registry.all()).thenReturn(List.of());

        mvc.perform(get("/api/v1/plugins"))
                .andExpect(status().isOk())
                .andExpect(content().json("[]"));
    }

    @Test
    void describe_returnsTheManagersHumanReadableTree() throws Exception {
        when(manager.describe()).thenReturn("plugins:\n  biome-generators [STARTED]\n");

        mvc.perform(get("/api/v1/plugins/describe"))
                .andExpect(status().isOk())
                .andExpect(content().string("plugins:\n  biome-generators [STARTED]\n"));
    }
}
