package com.daedalus.actuator;

import com.daedalus.plugin.PluginManager;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

/**
 * Custom health indicator for the plugin subsystem.
 */
@Component
public class PluginHealthIndicator implements HealthIndicator {

    private final PluginManager pluginManager;

    public PluginHealthIndicator(PluginManager pluginManager) {
        this.pluginManager = pluginManager;
    }

    @Override
    public Health health() {
        int count = pluginManager.loadedCount();
        if (count > 0) {
            return Health.up()
                    .withDetail("pluginsLoaded", count)
                    .withDetail("status", "All plugins started successfully")
                    .build();
        } else {
            return Health.down()
                    .withDetail("pluginsLoaded", 0)
                    .withDetail("status", "No plugins loaded")
                    .build();
        }
    }
}