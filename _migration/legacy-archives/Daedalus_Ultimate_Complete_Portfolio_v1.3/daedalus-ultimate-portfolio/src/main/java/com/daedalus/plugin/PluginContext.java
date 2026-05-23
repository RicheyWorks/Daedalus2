package com.daedalus.plugin;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.solver.solvers.SolverRegistry;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationEventPublisher;

/**
 * Service handle handed to every plugin during lifecycle calls.
 *
 * <p>Plugins use this to:
 * <ul>
 *   <li>Register algorithms via {@link #generators()} / {@link #solvers()}.</li>
 *   <li>Publish events via {@link #events()} (subscribed to with @EventListener).</li>
 *   <li>Look up arbitrary Spring beans via {@link #beans()} when they need deeper hooks.</li>
 * </ul>
 */
public final class PluginContext {

    private final ApplicationContext spring;
    private final GeneratorRegistry generators;
    private final SolverRegistry solvers;

    public PluginContext(ApplicationContext spring,
                         GeneratorRegistry generators,
                         SolverRegistry solvers) {
        this.spring = spring;
        this.generators = generators;
        this.solvers = solvers;
    }

    public GeneratorRegistry generators() { return generators; }
    public SolverRegistry solvers()       { return solvers; }
    public ApplicationContext beans()     { return spring; }
    public ApplicationEventPublisher events() { return spring; }

    public <T> T bean(Class<T> type) {
        return spring.getBean(type);
    }
}
