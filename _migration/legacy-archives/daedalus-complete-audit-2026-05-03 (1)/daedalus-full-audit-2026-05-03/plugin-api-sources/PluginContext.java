package com.daedalus.plugin;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.plugin.events.PluginEvent;
import com.daedalus.solver.solvers.SolverRegistry;

/**
 * Service handle handed to every plugin during lifecycle calls.
 *
 * <p>This is a Spring-free interface — the concrete implementation lives in
 * {@code daedalus-plugin-runtime} ({@code SpringPluginContext}). A non-Spring host
 * could supply its own implementation if it wanted to embed the SPI without Spring.
 *
 * <p>Plugins use this to:
 * <ul>
 *   <li>Register algorithms via {@link #generators()} / {@link #solvers()}.</li>
 *   <li>Publish events via {@link #publish(PluginEvent)} (subscribed to with @EventListener
 *       on the event subclass when running under a Spring host).</li>
 *   <li>Look up framework-managed beans by type via {@link #bean(Class)} when they need
 *       deeper hooks. The semantics of "bean" are host-defined; under Spring this is a
 *       {@code ApplicationContext.getBean} call.</li>
 * </ul>
 */
public interface PluginContext {

    GeneratorRegistry generators();

    SolverRegistry solvers();

    /** Publish an event to any subscribers registered with the host. */
    void publish(PluginEvent event);

    /** Look up a host-managed bean by type. */
    <T> T bean(Class<T> type);
}
