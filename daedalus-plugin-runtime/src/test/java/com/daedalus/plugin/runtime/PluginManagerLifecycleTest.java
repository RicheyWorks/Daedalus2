// SPDX-License-Identifier: MIT

package com.daedalus.plugin.runtime;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.plugin.MazePlugin;
import com.daedalus.plugin.PluginContext;
import com.daedalus.plugin.PluginLifecycle;
import com.daedalus.plugin.PluginManifest;
import com.daedalus.plugin.events.PluginFailedEvent;
import com.daedalus.solver.solvers.SolverRegistry;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.ArgumentCaptor;
import org.springframework.context.ApplicationContext;

import java.io.IOException;
import java.lang.reflect.Field;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Covers the audit's findings for {@code daedalus-plugin-runtime}:
 *
 * <ol>
 *   <li>{@link PluginManager#bootAll()} progresses every discovered plugin through
 *       {@code init → registerAlgorithms → start} in dependency order, with per-plugin error
 *       isolation.</li>
 *   <li>{@link PluginManager#shutdownAll()} closes every {@code URLClassLoader} created for
 *       external JAR plugins (the leak fix from {@code 01-pluginmanager-classloader-leak.patch}).</li>
 * </ol>
 *
 * <p>Tests intentionally bypass {@link PluginManager#discover()} where possible — we drive the
 * registry directly so we don't need to ship a real JAR + ServiceLoader manifest in test
 * resources. The classloader test reaches the leak-fix code via reflection on the private
 * {@code externalLoaders} list, which is the same pattern the fix itself uses (see the audit's
 * decision to demote {@code exists(File)} to package-private).
 */
class PluginManagerLifecycleTest {

    /* ---------------------------------------------------------------------- */
    /* Fixtures                                                               */
    /* ---------------------------------------------------------------------- */

    /** Records every lifecycle callback so tests can assert order and per-plugin progression. */
    private static final class TrackingPlugin implements MazePlugin {
        private final PluginManifest manifest;
        private final List<String> calls;
        private final boolean throwOnInit;

        TrackingPlugin(String id, List<String> calls, String... requires) {
            this(id, calls, false, requires);
        }

        TrackingPlugin(String id, List<String> calls, boolean throwOnInit, String... requires) {
            this.manifest = new PluginManifest(id, id, "1.0", "test", "test plugin", requires);
            this.calls = calls;
            this.throwOnInit = throwOnInit;
        }

        @Override public PluginManifest manifest() { return manifest; }

        @Override public void init(PluginContext ctx) {
            calls.add(manifest.id() + ":init");
            if (throwOnInit) throw new RuntimeException("boom in init for " + manifest.id());
        }
        @Override public void registerAlgorithms(PluginContext ctx) {
            calls.add(manifest.id() + ":register");
        }
        @Override public void start(PluginContext ctx) {
            calls.add(manifest.id() + ":start");
        }
        @Override public void stop(PluginContext ctx) {
            calls.add(manifest.id() + ":stop");
        }
    }

    private PluginManager managerWith(PluginRegistry registry, Path pluginDir) {
        return rigWith(registry, pluginDir).manager;
    }

    /** Bundles the manager with its mock {@link ApplicationContext} for tests that need both. */
    private record Rig(PluginManager manager, ApplicationContext spring) {}

    private Rig rigWith(PluginRegistry registry, Path pluginDir) {
        ApplicationContext spring = mock(ApplicationContext.class);
        when(spring.getBean(GeneratorRegistry.class)).thenReturn(new GeneratorRegistry(List.of()));
        when(spring.getBean(SolverRegistry.class)).thenReturn(new SolverRegistry(List.of()));
        PluginManager mgr = new PluginManager(registry, spring, pluginDir.toString());
        return new Rig(mgr, spring);
    }

    /* ---------------------------------------------------------------------- */
    /* Lifecycle + dependency ordering                                        */
    /* ---------------------------------------------------------------------- */

    @Test
    void bootAll_drivesEachPluginThroughInitRegisterStart(@TempDir Path pluginDir) {
        List<String> calls = new ArrayList<>();
        PluginRegistry registry = new PluginRegistry();
        registry.put(new TrackingPlugin("alpha", calls));

        PluginManager mgr = managerWith(registry, pluginDir);
        mgr.bootAll();

        assertThat(calls).containsExactly("alpha:init", "alpha:register", "alpha:start");
        assertThat(registry.get("alpha").state()).isEqualTo(PluginLifecycle.STARTED);
    }

    @Test
    void bootAll_respectsDeclaredDependencies(@TempDir Path pluginDir) {
        // "child" requires "parent" — parent must be initialised + registered + started before
        // child gets any of its lifecycle calls.
        List<String> calls = new ArrayList<>();
        PluginRegistry registry = new PluginRegistry();
        registry.put(new TrackingPlugin("child", calls, "parent"));
        registry.put(new TrackingPlugin("parent", calls));

        PluginManager mgr = managerWith(registry, pluginDir);
        mgr.bootAll();

        // Parent must finish all three phases before child begins. (The current implementation
        // actually finishes parent fully — init→register→start — before touching child, because
        // sortedByDependencies returns parent first and bootAll iterates linearly.)
        assertThat(calls).containsExactly(
                "parent:init", "parent:register", "parent:start",
                "child:init", "child:register", "child:start");
    }

    @Test
    void bootAll_isolatesFailures_perPlugin(@TempDir Path pluginDir) {
        List<String> calls = new ArrayList<>();
        PluginRegistry registry = new PluginRegistry();
        registry.put(new TrackingPlugin("good", calls));
        registry.put(new TrackingPlugin("broken", calls, /*throwOnInit*/ true));

        PluginManager mgr = managerWith(registry, pluginDir);
        mgr.bootAll();

        // The broken plugin's failure must not stop the good one from reaching STARTED.
        assertThat(registry.get("good").state()).isEqualTo(PluginLifecycle.STARTED);
        assertThat(registry.get("broken").state()).isEqualTo(PluginLifecycle.FAILED);
        assertThat(registry.get("broken").error()).isNotNull();
        assertThat(calls).contains("good:start");
    }

    @Test
    void bootAll_publishesPluginFailedEvent_whenInitThrows(@TempDir Path pluginDir) {
        List<String> calls = new ArrayList<>();
        PluginRegistry registry = new PluginRegistry();
        registry.put(new TrackingPlugin("broken", calls, /*throwOnInit*/ true));

        Rig rig = rigWith(registry, pluginDir);
        rig.manager.bootAll();

        ArgumentCaptor<Object> events = ArgumentCaptor.forClass(Object.class);
        verify(rig.spring).publishEvent(events.capture());
        Object published = events.getValue();
        assertThat(published).isInstanceOf(PluginFailedEvent.class);

        PluginFailedEvent event = (PluginFailedEvent) published;
        assertThat(event.pluginId()).isEqualTo("broken");
        assertThat(event.pluginVersion()).isEqualTo("1.0");
        assertThat(event.phase()).isEqualTo(PluginFailedEvent.Phase.INIT);
        assertThat(event.errorClass()).isEqualTo(RuntimeException.class.getName());
        assertThat(event.errorMessage()).contains("boom in init for broken");
        assertThat(event.cause()).isNotNull();
        assertThat(event.getTimestamp()).isPositive();
    }

    @Test
    void bootAll_doesNotPublishEvent_onSuccess(@TempDir Path pluginDir) {
        List<String> calls = new ArrayList<>();
        PluginRegistry registry = new PluginRegistry();
        registry.put(new TrackingPlugin("alpha", calls));

        Rig rig = rigWith(registry, pluginDir);
        rig.manager.bootAll();

        // No publishEvent call at all when every plugin starts cleanly.
        verify(rig.spring, never()).publishEvent(org.mockito.ArgumentMatchers.any());
    }

    @Test
    void shutdownAll_publishesPluginFailedEvent_whenStopThrows(@TempDir Path pluginDir) {
        // Plugin starts cleanly but throws on stop — the event payload should report STOP phase.
        PluginRegistry registry = new PluginRegistry();
        MazePlugin throwOnStop = new MazePlugin() {
            private final PluginManifest m = new PluginManifest("flaky", "Flaky", "2.1", "test", "throws on stop");
            @Override public PluginManifest manifest() { return m; }
            @Override public void stop(PluginContext ctx) { throw new IllegalStateException("stop boom"); }
        };
        registry.put(throwOnStop);

        Rig rig = rigWith(registry, pluginDir);
        rig.manager.bootAll();

        // Sanity: STARTED, no events yet.
        assertThat(registry.get("flaky").state()).isEqualTo(PluginLifecycle.STARTED);

        rig.manager.shutdownAll();

        ArgumentCaptor<Object> events = ArgumentCaptor.forClass(Object.class);
        verify(rig.spring).publishEvent(events.capture());
        PluginFailedEvent event = (PluginFailedEvent) events.getValue();
        assertThat(event.pluginId()).isEqualTo("flaky");
        assertThat(event.pluginVersion()).isEqualTo("2.1");
        assertThat(event.phase()).isEqualTo(PluginFailedEvent.Phase.STOP);
        assertThat(event.errorClass()).isEqualTo(IllegalStateException.class.getName());
        assertThat(event.errorMessage()).isEqualTo("stop boom");
    }

    @Test
    void shutdownAll_callsStop_onlyForStartedPlugins(@TempDir Path pluginDir) {
        List<String> calls = new ArrayList<>();
        PluginRegistry registry = new PluginRegistry();
        registry.put(new TrackingPlugin("good", calls));
        registry.put(new TrackingPlugin("broken", calls, /*throwOnInit*/ true));

        PluginManager mgr = managerWith(registry, pluginDir);
        mgr.bootAll();
        calls.clear();
        mgr.shutdownAll();

        assertThat(calls).containsExactly("good:stop");
        assertThat(registry.get("good").state()).isEqualTo(PluginLifecycle.STOPPED);
        // 'broken' was never STARTED so stop() must not have been called.
        assertThat(registry.get("broken").state()).isEqualTo(PluginLifecycle.FAILED);
    }

    /* ---------------------------------------------------------------------- */
    /* Classloader leak fix (the audit's plugin-runtime patch)                */
    /* ---------------------------------------------------------------------- */

    @Test
    @SuppressWarnings("unchecked")
    void shutdownAll_closesAndClearsExternalClassloaders(@TempDir Path pluginDir) throws Exception {
        PluginManager mgr = managerWith(new PluginRegistry(), pluginDir);

        // Simulate two external JARs' classloaders without actually building JARs. We poke the
        // private list directly — same field name + type the production fix introduced.
        Field loaders = PluginManager.class.getDeclaredField("externalLoaders");
        loaders.setAccessible(true);
        List<URLClassLoader> externalLoaders = (List<URLClassLoader>) loaders.get(mgr);

        TrackingClassLoader cl1 = new TrackingClassLoader();
        TrackingClassLoader cl2 = new TrackingClassLoader();
        externalLoaders.add(cl1);
        externalLoaders.add(cl2);

        // Sanity: both open before shutdown.
        assertThat(externalLoaders).hasSize(2);
        assertThat(cl1.wasClosed()).isFalse();
        assertThat(cl2.wasClosed()).isFalse();

        mgr.shutdownAll();

        assertThat(externalLoaders)
                .as("shutdownAll must clear the tracking list to release references")
                .isEmpty();
        assertThat(cl1.wasClosed()).as("cl1 must have been closed").isTrue();
        assertThat(cl2.wasClosed()).as("cl2 must have been closed").isTrue();
    }

    @Test
    void discover_onMissingPluginDir_doesNotThrow(@TempDir Path baseTempDir) {
        // The audit specifically calls out graceful handling of a missing plugin directory.
        // Use a path that doesn't exist (subpath of TempDir).
        Path missing = baseTempDir.resolve("nope-not-here");
        PluginManager mgr = managerWith(new PluginRegistry(), missing);

        // discover() must not raise — it should log + skip the external scan. Built-in
        // ServiceLoader pass may or may not find anything depending on classpath; we don't
        // assert on that.
        mgr.discover();
    }

    /**
     * URLClassLoader has no public {@code isClosed()} accessor and the JDK-internal {@code closed}
     * field has shifted across releases, so we observe close() through a subclass instead. This
     * keeps the test portable across Java versions.
     */
    private static final class TrackingClassLoader extends URLClassLoader {
        private final AtomicBoolean closed = new AtomicBoolean(false);
        TrackingClassLoader() {
            super(new URL[0], PluginManagerLifecycleTest.class.getClassLoader());
        }
        @Override public void close() throws IOException {
            closed.set(true);
            super.close();
        }
        boolean wasClosed() { return closed.get(); }
    }
}
