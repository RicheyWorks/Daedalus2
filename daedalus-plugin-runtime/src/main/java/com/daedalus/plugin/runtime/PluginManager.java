// SPDX-License-Identifier: MIT

package com.daedalus.plugin.runtime;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.plugin.MazePlugin;
import com.daedalus.plugin.PluginContext;
import com.daedalus.plugin.PluginLifecycle;
import com.daedalus.plugin.PluginManifest;
import com.daedalus.plugin.events.PluginFailedEvent;
import com.daedalus.solver.solvers.SolverRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.ApplicationContext;

import java.io.File;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.ServiceLoader;

/**
 * Plugin discovery + lifecycle orchestration.
 *
 * <p>{@link #discover()} scans:
 * <ol>
 *   <li>The classpath for {@code META-INF/services/com.daedalus.plugin.MazePlugin} entries
 *       (built-in plugins).</li>
 *   <li>The configured plugin directory for JAR files (external plugins). Each JAR is
 *       added to a child classloader; its ServiceLoader contributions are loaded.</li>
 * </ol>
 *
 * <p>{@link #bootAll()} progresses every discovered plugin through the lifecycle:
 * {@code init → registerAlgorithms → start}, in dependency order.
 */
public class PluginManager {

    private static final Logger log = LoggerFactory.getLogger(PluginManager.class);

    private final PluginRegistry registry;
    private final ApplicationContext spring;
    private final String pluginDir;
    private PluginContext context;
    private final List<URLClassLoader> externalLoaders = new ArrayList<>();

    public PluginManager(PluginRegistry registry, ApplicationContext spring, String pluginDir) {
        this.registry = registry;
        this.spring = spring;
        this.pluginDir = pluginDir;
    }

    public void discover() {
        // 1. Built-in via classpath ServiceLoader.
        for (MazePlugin p : ServiceLoader.load(MazePlugin.class)) {
            register(p, "classpath");
        }

        // 2. External JARs in pluginDir.
        Path dir = Paths.get(pluginDir);
        if (!Files.isDirectory(dir)) {
            log.info("Plugin directory {} not found — skipping external plugin scan", dir.toAbsolutePath());
            return;
        }
        try (var stream = Files.list(dir)) {
            stream
                .filter(p -> p.toString().endsWith(".jar"))
                .forEach(this::loadJar);
        } catch (Exception e) {
            log.warn("Failed scanning plugin directory {}: {}", dir, e.toString());
        }
    }

    private void loadJar(Path jar) {
        try {
            URL url = jar.toUri().toURL();
            URLClassLoader cl = new URLClassLoader(new URL[]{url}, getClass().getClassLoader());
            externalLoaders.add(cl);
            ServiceLoader<MazePlugin> sl = ServiceLoader.load(MazePlugin.class, cl);
            for (MazePlugin p : sl) {
                register(p, jar.getFileName().toString());
            }
        } catch (Throwable t) {
            // Catch Throwable rather than Exception: the most common discovery failures —
            // service file points at a missing class, points at the wrong type, plugin
            // constructor throws — all surface as ServiceConfigurationError, which extends
            // Error and would otherwise escape this method and crash discover() entirely.
            // We surface the failure to operators via PluginFailedEvent (the same channel
            // INIT/REGISTER/START/STOP failures use) instead of grepping logs.
            log.warn("Failed to load plugin JAR {}: {}", jar, t.toString());
            spring.publishEvent(new PluginFailedEvent(
                    this, jar.getFileName().toString(), null,
                    PluginFailedEvent.Phase.DISCOVER, t));
        }
    }

    private void register(MazePlugin p, String origin) {
        PluginManifest m = p.manifest();
        registry.put(p);
        log.info("Discovered plugin '{}' v{} ({}) from {}", m.id(), m.version(), m.author(), origin);
    }

    public void bootAll() {
        this.context = new SpringPluginContext(
                spring,
                spring.getBean(GeneratorRegistry.class),
                spring.getBean(SolverRegistry.class));

        for (PluginRegistry.Entry e : registry.sortedByDependencies()) {
            // Track which lifecycle phase we're attempting so the failure event reports it
            // accurately. Updated immediately before each call.
            PluginFailedEvent.Phase phase = PluginFailedEvent.Phase.INIT;
            try {
                e.plugin().init(context);
                registry.advance(e.manifest().id(), PluginLifecycle.INITIALIZED);

                phase = PluginFailedEvent.Phase.REGISTER_ALGORITHMS;
                e.plugin().registerAlgorithms(context);
                registry.advance(e.manifest().id(), PluginLifecycle.REGISTERED);

                phase = PluginFailedEvent.Phase.START;
                e.plugin().start(context);
                registry.advance(e.manifest().id(), PluginLifecycle.STARTED);

                log.info("Started plugin '{}' v{}", e.manifest().id(), e.manifest().version());
            } catch (Throwable t) {
                registry.fail(e.manifest().id(), t);
                log.error("Plugin '{}' failed in {}: {}",
                        e.manifest().id(), phase, t.toString(), t);
                spring.publishEvent(new PluginFailedEvent(
                        this, e.manifest().id(), e.manifest().version(), phase, t));
            }
        }
    }

    public void shutdownAll() {
        for (PluginRegistry.Entry e : registry.all()) {
            if (e.state() != PluginLifecycle.STARTED) continue;
            try {
                e.plugin().stop(context);
                registry.advance(e.manifest().id(), PluginLifecycle.STOPPED);
            } catch (Throwable t) {
                log.warn("Plugin '{}' threw on stop: {}", e.manifest().id(), t.toString());
                spring.publishEvent(new PluginFailedEvent(
                        this, e.manifest().id(), e.manifest().version(),
                        PluginFailedEvent.Phase.STOP, t));
            }
        }
        // Close external classloaders to release JAR file handles (prevents leaks on reload/shutdown)
        for (URLClassLoader cl : externalLoaders) {
            try {
                cl.close();
            } catch (Exception ex) {
                log.debug("Ignoring classloader close failure during shutdown", ex);
            }
        }
        externalLoaders.clear();
    }

    public int loadedCount() { return registry.size(); }
    public PluginRegistry registry() { return registry; }
    public PluginContext context() { return context; }

    /** Convenience for diagnostics — string list of all known plugins. */
    public String describe() {
        StringBuilder sb = new StringBuilder();
        for (PluginRegistry.Entry e : registry.all()) {
            sb.append(String.format("[%s] %s v%s — %s%n",
                    e.state(), e.manifest().id(), e.manifest().version(), e.manifest().description()));
        }
        return sb.toString();
    }

    /** For tests / scripted loads. */
    boolean exists(File f) { return f.exists() && f.isFile(); }
}
