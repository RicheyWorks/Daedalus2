package com.daedalus.config;

import com.daedalus.plugin.PluginManager;
import com.daedalus.plugin.PluginRegistry;
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
 * <p>On {@link ApplicationReadyEvent}, scans {@code daedalus.plugin.dir} (default {@code ./plugins})
 * for plugin JARs and any built-in plugins registered via {@code META-INF/services/com.daedalus.plugin.MazePlugin}.
 * All discovered plugins are initialized through {@link PluginManager#bootAll}.
 */
@Configuration
public class PluginConfig {

    private static final Logger log = LoggerFactory.getLogger(PluginConfig.class);

    @Value("${daedalus.plugin.dir:./plugins}")
    private String pluginDir;

    @Bean
    public PluginRegistry pluginRegistry() {
        return new PluginRegistry();
    }

    @Bean
    public PluginManager pluginManager(PluginRegistry registry, ApplicationContext ctx) {
        return new PluginManager(registry, ctx, pluginDir);
    }

    @EventListener(ApplicationReadyEvent.class)
    public void bootPlugins(ApplicationReadyEvent event) {
        PluginManager mgr = event.getApplicationContext().getBean(PluginManager.class);
        mgr.discover();
        mgr.bootAll();
        log.info("Daedalus plugin subsystem ready — {} plugin(s) loaded", mgr.loadedCount());
    }
}
