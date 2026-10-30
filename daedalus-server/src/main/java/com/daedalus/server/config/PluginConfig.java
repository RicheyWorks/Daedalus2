// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import com.daedalus.plugin.runtime.PluginManager;
import com.daedalus.plugin.runtime.PluginRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.event.EventListener;

/**
 * Plugin subsystem wiring.
 *
 * <p>On {@link ApplicationReadyEvent}, when {@code daedalus.plugins.scan-on-startup} is true,
 * scans {@code daedalus.plugins.directory} for plugin JARs and any built-in plugins registered
 * via {@code META-INF/services/com.daedalus.plugin.MazePlugin}. All discovered plugins are
 * initialized through {@link PluginManager#bootAll}. On context close, Spring calls
 * {@link PluginManager#shutdownAll} via the bean destroy method so {@code stop()} runs,
 * contributed algorithms leave the registries, and external {@code URLClassLoader}s close.
 * Until 2026-08-26 that destroy method was unset: {@code shutdownAll} existed and the
 * runtime suite called it, but the host never did.
 *
 * <p><b>Config-audit note (2026-07-29):</b> this class used to read {@code daedalus.plugin.dir}
 * while every profile configured {@code daedalus.plugins.directory} — the configured directory
 * (and the {@code DAEDALUS_PLUGIN_DIR} env var) was silently ignored, and plugins loaded from
 * {@code ./plugins} relative to the working directory. Worse, {@code scan-on-startup} was set
 * in every profile ({@code false} under test) and read by <em>nothing</em>: startup scanning
 * ran unconditionally, and the test profile only appeared to disable it. Both are wired now
 * and pinned by {@code PluginSpiEndToEndTest}. Shutdown is pinned by
 * {@code PluginHostShutdownTest}.
 */
@Configuration
public class PluginConfig {

    private static final Logger log = LoggerFactory.getLogger(PluginConfig.class);

    @Value("${daedalus.plugins.directory:${user.home}/.daedalus/plugins}")
    private String pluginDir;

    @Value("${daedalus.plugins.scan-on-startup:true}")
    private boolean scanOnStartup;

    @Bean
    public PluginRegistry pluginRegistry() {
        return new PluginRegistry();
    }

    @Bean(destroyMethod = "shutdownAll")
    public PluginManager pluginManager(PluginRegistry registry, ApplicationContext ctx) {
        return new PluginManager(registry, ctx, pluginDir);
    }

    @EventListener(ApplicationReadyEvent.class)
    public void bootPlugins(ApplicationReadyEvent event) {
        if (!scanOnStartup) {
            log.info("Plugin startup scan disabled (daedalus.plugins.scan-on-startup=false)");
            return;
        }
        PluginManager mgr = event.getApplicationContext().getBean(PluginManager.class);
        mgr.discover();
        mgr.bootAll();
        log.info("Daedalus plugin subsystem ready — {} plugin(s) loaded", mgr.loadedCount());
    }
}
