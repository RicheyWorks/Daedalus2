// SPDX-License-Identifier: MIT

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
 *
 * <p>Failures during any lifecycle phase are caught by the host, recorded on the plugin's
 * registry entry, and re-published as a {@code PluginFailedEvent} (see
 * {@code com.daedalus.plugin.events.PluginFailedEvent}). Implementations should let
 * unrecoverable problems propagate so the host can isolate them — don't swallow exceptions
 * silently.
 *
 * @since 1.0
 */
public interface MazePlugin {

    /**
     * The plugin's identity card — id, version, dependencies. Must never return {@code null};
     * the {@link PluginManifest} compact constructor enforces non-null required fields.
     *
     * @since 1.0
     */
    PluginManifest manifest();

    /**
     * Convenience accessor for the plugin version. Default delegates to
     * {@code manifest().version()}; overriding is rarely useful.
     *
     * @return the manifest's version string (never {@code null})
     * @since 1.0
     */
    default String version() {
        return manifest().version();
    }

    /**
     * Called once at load, before any other lifecycle method.
     *
     * @apiNote Stash the {@link PluginContext} if you need it later — for instance, to publish
     *          events from a non-lifecycle thread. {@link AbstractPlugin} does this for you.
     *
     * @param ctx the host-supplied service handle (generators, solvers, event publisher)
     * @since 1.0
     */
    default void init(PluginContext ctx) {}

    /**
     * Register additional generators/solvers via {@code ctx.generators().register(...)}
     * and {@code ctx.solvers().register(...)}. Called once after {@link #init}.
     *
     * @apiNote Algorithms registered here automatically appear in
     *          {@code GET /api/algorithms} and the UI dropdowns. The registries are thread-safe;
     *          you may also register additional algorithms later (e.g. on a config reload).
     *
     * @param ctx the host-supplied service handle
     * @since 1.0
     */
    default void registerAlgorithms(PluginContext ctx) {}

    /**
     * Called after registration, when the application is up and live.
     *
     * @apiNote This is the right place to start background threads, open connections, or
     *          register listeners that should only be active once the host is fully booted.
     *
     * @param ctx the host-supplied service handle
     * @since 1.0
     */
    default void start(PluginContext ctx) {}

    /**
     * Called on shutdown — release resources, unsubscribe listeners.
     *
     * @apiNote The host catches throwables here and publishes a {@code PluginFailedEvent} with
     *          {@code phase=STOP}, but does not abort other plugins' shutdown.
     *
     * @param ctx the host-supplied service handle
     * @since 1.0
     */
    default void stop(PluginContext ctx) {}

    /**
     * Optional list of algorithms this plugin contributes — used for UI listing in places
     * where the host wants to render "what does this plugin add?" without consulting the
     * shared registries.
     *
     * <p><b>Example.</b> A plugin that contributes one generator and one solver:
     *
     * <pre>{@code
     * @Override
     * public List<AlgorithmDescriptor> contributedAlgorithms() {
     *     return List.of(
     *         new AlgorithmDescriptor(
     *             "biome-forest",
     *             "Forest Biome Generator",
     *             "generator",
     *             "O(n) time, O(n) space",
     *             "favours organic, branching corridors",
     *             "Carves a maze that loosely resembles tree canopies."),
     *         new AlgorithmDescriptor(
     *             "river-flow",
     *             "River-Flow Solver",
     *             "solver",
     *             "O(n log n) time, O(n) space",
     *             "no bias",
     *             "Flood-fill solver that prefers downhill corridors first.")
     *     );
     * }
     * }</pre>
     *
     * <p>Default implementation returns an empty list. Returning {@code null} is not
     * permitted — callers iterate the result without null guards.
     *
     * @return descriptors for every generator/solver this plugin contributes
     * @since 1.0
     */
    default List<AlgorithmDescriptor> contributedAlgorithms() { return List.of(); }
}
