package com.daedalus.plugin;

import com.daedalus.model.AlgorithmDescriptor;

import java.util.List;

/**
 * Service Provider Interface for Daedalus plugins.
 *
 * <p>A plugin can extend the engine in three ways:
 * <ol>
 *   <li>Register new generators / solvers (see {@link #registerAlgorithms}).</li>
 *   <li>Subscribe to lifecycle and gameplay events (see {@code events/}).</li>
 *   <li>Expose REST endpoints, themes, or controllers — anything Spring can wire.
 *       Plugin classpath JARs are added to the classloader before the
 *       Spring context refreshes.</li>
 * </ol>
 *
 * <p>Discovery: built-in plugins are listed in
 * {@code META-INF/services/com.daedalus.plugin.MazePlugin}. External plugins go in the
 * {@code plugins/} directory next to the application JAR; their JAR manifests must
 * declare the same {@code ServiceLoader} entry.
 *
 * <p>Lifecycle: {@link #init} → {@link #registerAlgorithms} → {@link #start} → ... → {@link #stop}.
 */
public interface MazePlugin {

    PluginManifest manifest();

    /** Called once at load. Stash the context if you need it later. */
    default void init(PluginContext ctx) {}

    /**
     * Register additional generators/solvers via {@code ctx.generators().register(...)}
     * and {@code ctx.solvers().register(...)}. Called once after {@link #init}.
     */
    default void registerAlgorithms(PluginContext ctx) {}

    /** Called after registration, when the application is up and live. */
    default void start(PluginContext ctx) {}

    /** Called on shutdown — release resources, unsubscribe listeners. */
    default void stop(PluginContext ctx) {}

    /** Optional list of algorithms this plugin contributes — used for UI listing. */
    default List<AlgorithmDescriptor> contributedAlgorithms() { return List.of(); }
}
