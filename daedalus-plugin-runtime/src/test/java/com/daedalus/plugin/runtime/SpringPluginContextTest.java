// SPDX-License-Identifier: MIT

package com.daedalus.plugin.runtime;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.plugin.events.PluginEvent;
import com.daedalus.solver.solvers.SolverRegistry;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.NoSuchBeanDefinitionException;
import org.springframework.context.PayloadApplicationEvent;
import org.springframework.context.support.GenericApplicationContext;

import java.time.Clock;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Unit test for {@link SpringPluginContext} — the seam plugins actually receive, previously
 * referenced by zero tests.
 *
 * <p>Everything here is contract a plugin author will depend on, so each behavior is pinned
 * deliberately rather than left implementation-defined:
 *
 * <ul>
 *   <li>the two registries hand back exactly what the host wired in — no copying, no
 *       wrapping, because plugins register algorithms into these instances and the host must
 *       see them;</li>
 *   <li>{@code publish} delegates to the Spring context, and a POJO {@link PluginEvent}
 *       arrives at Spring listeners as the payload (the whole point of the Spring-free
 *       plugin-api event base);</li>
 *   <li>{@code bean(Class)} resolves from the host context, and asking for something
 *       unavailable <b>fails fast</b> with Spring's {@link NoSuchBeanDefinitionException}
 *       rather than returning {@code null} — a plugin discovering a missing dependency at
 *       lookup time beats a {@code NullPointerException} three calls later.</li>
 * </ul>
 *
 * <p>Uses a real (empty-ish) {@link GenericApplicationContext} rather than a mock: publishing
 * and bean lookup are exactly the behaviors under test, and mocking them would only prove the
 * mock agrees with itself.
 */
class SpringPluginContextTest {

    /** Trivial concrete event — PluginEvent itself is abstract. */
    private static final class ProbeEvent extends PluginEvent {
        ProbeEvent(Object source) {
            super(source);
        }
    }

    private GenericApplicationContext spring;
    private GeneratorRegistry generators;
    private SolverRegistry solvers;
    private SpringPluginContext context;

    @BeforeEach
    void setUp() {
        spring = new GenericApplicationContext();
        spring.registerBean(Clock.class, Clock::systemUTC);
        spring.refresh();
        generators = new GeneratorRegistry(List.of());
        solvers = new SolverRegistry(List.of());
        context = new SpringPluginContext(spring, generators, solvers);
    }

    @AfterEach
    void tearDown() {
        spring.close();
    }

    @Test
    void registriesAreTheExactInstancesTheHostWiredIn() {
        assertThat(context.generators()).isSameAs(generators);
        assertThat(context.solvers()).isSameAs(solvers);
        assertThat(context.spring()).isSameAs(spring);
    }

    @Test
    void publishDeliversThePojoEventToSpringListeners() {
        List<Object> received = new ArrayList<>();
        spring.addApplicationListener(event -> {
            if (event instanceof PayloadApplicationEvent<?> payload) {
                received.add(payload.getPayload());
            }
        });

        ProbeEvent event = new ProbeEvent(this);
        context.publish(event);

        // Same instance, not a copy — listeners may rely on identity (e.g. transient fields).
        assertThat(received).containsExactly(event);
    }

    @Test
    void beanResolvesFromTheHostContext() {
        assertThat(context.bean(Clock.class)).isSameAs(spring.getBean(Clock.class));
    }

    @Test
    void beanFailsFastWhenTheTypeIsUnavailable() {
        // Pinned on purpose: fail-fast, not null. Plugin authors will depend on whichever
        // behavior ships, so a change here is a breaking change to the plugin contract.
        assertThatThrownBy(() -> context.bean(Runnable.class))
                .isInstanceOf(NoSuchBeanDefinitionException.class);
    }
}
