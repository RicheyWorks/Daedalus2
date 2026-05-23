package com.daedalus.controller;

import com.daedalus.plugin.PluginManager;
import com.daedalus.plugin.PluginManifest;
import com.daedalus.plugin.PluginRegistry;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/** Read-only introspection for the plugin subsystem. */
@RestController
@RequestMapping("/api/plugins")
public class PluginController {

    private final PluginManager manager;

    public PluginController(PluginManager manager) {
        this.manager = manager;
    }

    public record PluginInfo(String id, String state, PluginManifest manifest, String error) {}

    @GetMapping
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
    public String describe() {
        return manager.describe();
    }
}
