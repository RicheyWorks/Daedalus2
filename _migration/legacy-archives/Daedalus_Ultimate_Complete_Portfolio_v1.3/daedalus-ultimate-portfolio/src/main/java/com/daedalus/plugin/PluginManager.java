package com.daedalus.plugin;

import com.daedalus.engine.generators.GeneratorRegistry;
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
            ServiceLoader<MazePlugin> sl = ServiceLoader.load(MazePlugin.class, cl);
            for (MazePlugin p : sl) {
                register(p, jar.getFileName().toString());
            }
        } catch (Exception e) {
            log.warn("Failed to load plugin JAR {}: {}", jar, e.toString());
        }
    }

    private void register(MazePlugin p, String origin) {
        PluginManifest m = p.manifest();
        registry.put(p);
        log.info("Discovered plugin '{}' v{} ({}) from {}", m.id(), m.version(), m.author(), origin);
    }

    public void bootAll() {
        this.context = new PluginContext(
                spring,
                spring.getBean(GeneratorRegistry.class),
                spring.getBean(SolverRegistry.class));

        for (PluginRegistry.Entry e : registry.sortedByDependencies()) {
            try {
                e.plugin().init(context);
                registry.advance(e.manifest().id(), PluginLifecycle.INITIALIZED);

                e.plugin().registerAlgorithms(context);
                registry.advance(e.manifest().id(), PluginLifecycle.REGISTERED);

                e.plugin().start(context);
                registry.advance(e.manifest().id(), PluginLifecycle.STARTED);

                log.info("Started plugin '{}' v{}", e.manifest().id(), e.manifest().version());
            } catch (Throwable t) {
                registry.fail(e.manifest().id(), t);
                log.error("Plugin '{}' failed to start: {}", e.manifest().id(), t.toString(), t);
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
            }
        }
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
    public boolean exists(File f) { return f.exists() && f.isFile(); }
}
