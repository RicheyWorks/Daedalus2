// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.plugin.PluginLifecycle;
import com.daedalus.plugin.runtime.PluginManager;
import com.daedalus.server.plugintest.EchoPlugin;
import com.daedalus.solver.solvers.SolverRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.config.BeanDefinition;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The host must actually call {@link PluginManager#shutdownAll} when its context closes.
 *
 * <p>The runtime module already proves what shutdown does (stop, unregister, close
 * classloaders). {@link com.daedalus.server.plugintest.PluginSpiEndToEndTest} already
 * proves the host <em>boots</em>
 * plugins. Until 2026-08-26 nothing proved the other half of {@link PluginConfig}:
 * {@code shutdownAll} existed, the runtime suite called it, and Spring never did,
 * because the {@code PluginManager} bean had no destroy method. README still claimed
 * clean shutdown.
 *
 * <p>This test owns the context — it is not Spring Test-managed — so {@code close()}
 * is ours to call and assert after. Closing a {@code @SpringBootTest} context in-method
 * leaves after-test listeners talking to a dead LifecycleProcessor.
 */
class PluginHostShutdownTest {

    @Test
    void closingTheHostStopsPluginsAndDropsTheirAlgorithms() {
        AnnotationConfigApplicationContext ctx = new AnnotationConfigApplicationContext();
        ctx.register(PluginConfig.class, HostRegistries.class);
        ctx.refresh();

        BeanDefinition pluginManager = ctx.getBeanDefinition("pluginManager");
        assertThat(pluginManager.getDestroyMethodName())
                .as("the gap: PluginConfig shipped PluginManager with no destroy method")
                .isEqualTo("shutdownAll");

        PluginManager manager = ctx.getBean(PluginManager.class);
        GeneratorRegistry generators = ctx.getBean(GeneratorRegistry.class);
        manager.registry().put(new EchoPlugin());
        manager.bootAll();

        assertThat(generators.ids()).contains("plugin-echo", "recursive-backtracker");
        assertThat(manager.registry().get("echo-plugin").state())
                .isEqualTo(PluginLifecycle.STARTED);

        ctx.close();

        assertThat(manager.registry().get("echo-plugin").state())
                .as("Spring must invoke destroyMethod=shutdownAll on context close")
                .isEqualTo(PluginLifecycle.STOPPED);
        assertThat(generators.ids())
                .as("a stopped plugin's generator must leave the catalog, not stay callable")
                .doesNotContain("plugin-echo");
        assertThat(generators.ids())
                .as("unload must not take a built-in with it")
                .contains("recursive-backtracker");
    }

    @Configuration
    static class HostRegistries {
        @Bean
        GeneratorRegistry generatorRegistry() {
            return new GeneratorRegistry(List.of(
                    new RecursiveBacktrackerGenerator(),
                    new BinaryTreeGenerator()));
        }

        @Bean
        SolverRegistry solverRegistry() {
            return new SolverRegistry(List.of());
        }
    }
}
