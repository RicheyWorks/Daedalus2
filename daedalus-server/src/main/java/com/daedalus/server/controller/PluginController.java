// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.PluginInfo;
import com.daedalus.plugin.runtime.PluginManager;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/** Read-only introspection for the plugin subsystem. */
@RestController
@RequestMapping("/api/v1/plugins")
@Tag(name = "Plugins", description = "Inspect plugins discovered and loaded by the runtime.")
public class PluginController {

    private final PluginManager manager;

    public PluginController(PluginManager manager) {
        this.manager = manager;
    }

    @GetMapping
    @Operation(summary = "List currently-loaded plugins with lifecycle state and any failure cause.")
    public List<PluginInfo> list() {
        return manager.registry().all().stream()
                .map(e -> new PluginInfo(
                        e.manifest().id(),
                        e.state().name(),
                        e.manifest(),
                        e.error() == null ? null : e.error().toString()))
                .toList();
    }

    @GetMapping("/describe")
    @Operation(summary = "Human-readable plugin tree (one line per plugin, lifecycle state included).")
    public String describe() {
        return manager.describe();
    }
}
