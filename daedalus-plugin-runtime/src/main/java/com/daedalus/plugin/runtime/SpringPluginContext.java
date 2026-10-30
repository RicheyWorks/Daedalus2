// SPDX-License-Identifier: MIT

package com.daedalus.plugin.runtime;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.plugin.PluginContext;
import com.daedalus.plugin.events.PluginEvent;
import com.daedalus.solver.solvers.SolverRegistry;
import org.springframework.context.ApplicationContext;

/**
 * Spring-backed {@link PluginContext} implementation.
 *
 * <p>This is the only place in the plugin layer that touches Spring directly. The plugin-api
 * itself is Spring-free; this adapter bridges plugin-api to the Spring host that
 * {@code daedalus-plugin-runtime} provides.
 */
public final class SpringPluginContext implements PluginContext {

    private final ApplicationContext spring;
    private final GeneratorRegistry generators;
    private final SolverRegistry solvers;

    public SpringPluginContext(ApplicationContext spring,
                               GeneratorRegistry generators,
                               SolverRegistry solvers) {
        this.spring = spring;
        this.generators = generators;
        this.solvers = solvers;
    }

    @Override public GeneratorRegistry generators() { return generators; }
    @Override public SolverRegistry solvers()       { return solvers; }

    @Override
    public void publish(PluginEvent event) {
        // Spring 4.2+ accepts arbitrary objects via publishEvent(Object).
        spring.publishEvent(event);
    }

    @Override
    public <T> T bean(Class<T> type) {
        return spring.getBean(type);
    }

    /** Escape hatch for runtime-internal callers that legitimately need the Spring context. */
    public ApplicationContext spring() { return spring; }
}
