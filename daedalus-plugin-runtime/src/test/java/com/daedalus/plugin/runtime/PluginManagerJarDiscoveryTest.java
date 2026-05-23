// SPDX-License-Identifier: MIT

package com.daedalus.plugin.runtime;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.plugin.MazePlugin;
import com.daedalus.plugin.PluginLifecycle;
import com.daedalus.plugin.events.PluginFailedEvent;
import com.daedalus.plugin.runtime.testfixtures.SamplePlugin;
import com.daedalus.solver.solvers.SolverRegistry;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.ArgumentCaptor;
import org.springframework.context.ApplicationContext;

import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.jar.JarEntry;
import java.util.jar.JarOutputStream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Real-JAR coverage for {@link PluginManager#discover()}. Builds a minimal plugin distribution
 * at test-runtime — a JAR that contains both the {@link SamplePlugin} class file and a
 * {@code META-INF/services/com.daedalus.plugin.MazePlugin} entry naming it — drops the JAR into
 * a temp directory, points {@code PluginManager} at that directory, and asserts:
 *
 * <ul>
 *   <li>discover() finds the plugin via {@link java.util.ServiceLoader} and registers it</li>
 *   <li>a {@link URLClassLoader} is tracked in the manager's {@code externalLoaders} list</li>
 *   <li>bootAll() drives the plugin through {@code init → registerAlgorithms → start}</li>
 *   <li>shutdownAll() closes the classloader and clears the tracking list</li>
 * </ul>
 *
 * <p>This complements {@code PluginManagerLifecycleTest}, which exercises lifecycle behaviour
 * by populating the registry directly. Together they cover both halves of the plugin
 * subsystem: discovery (here) and orchestration (there).
 */
class PluginManagerJarDiscoveryTest {

    private static final String SAMPLE_FQN = "com.daedalus.plugin.runtime.testfixtures.SamplePlugin";
    private static final String SAMPLE_RESOURCE = SAMPLE_FQN.replace('.', '/') + ".class";
    private static final String OTHER_FQN = "com.daedalus.plugin.runtime.testfixtures.OtherSamplePlugin";
    private static final String OTHER_RESOURCE = OTHER_FQN.replace('.', '/') + ".class";
    private static final String SERVICE_FILE = "META-INF/services/" + MazePlugin.class.getName();

    /**
     * Per-test PluginManager handle. Assigned by every test method that calls
     * {@link PluginManager#discover()} so that {@link #closeManager()} can release the
     * {@link URLClassLoader}s the discovery opens. Without this, Windows refuses to delete
     * the JAR files when JUnit's {@code @TempDir} extension cleans up — the loaders still
     * hold them open and {@code java.nio.file.Files#delete} throws {@code AccessDeniedException}.
     */
    private PluginManager mgr;

    @AfterEach
    void closeManager() {
        if (mgr != null) {
            // shutdownAll() is idempotent: tests that already called it themselves leave
            // externalLoaders empty, so this second pass is a no-op for them. Wrap defensively
            // anyway — a misbehaving plugin's stop() shouldn't keep @TempDir from cleaning up.
            try { mgr.shutdownAll(); } catch (Exception ignored) {}
            mgr = null;
        }
    }

    /* ---------------------------------------------------------------------- */
    /* Helpers                                                                */
    /* ---------------------------------------------------------------------- */

    /** Build a minimal plugin JAR in {@code dir}, return its path. */
    private static Path buildSamplePluginJar(Path dir) throws IOException {
        Path jarPath = dir.resolve("sample-plugin.jar");

        // The .class file must be readable from the test classpath — that's where Maven
        // surefire wires it after compiling test sources.
        ClassLoader cl = PluginManagerJarDiscoveryTest.class.getClassLoader();
        byte[] classBytes;
        try (InputStream in = cl.getResourceAsStream(SAMPLE_RESOURCE)) {
            if (in == null) {
                throw new IllegalStateException(
                        "Test resource not found on classpath: " + SAMPLE_RESOURCE
                                + " — Maven test-compile didn't run, or SamplePlugin moved.");
            }
            classBytes = in.readAllBytes();
        }

        try (JarOutputStream jar = new JarOutputStream(Files.newOutputStream(jarPath))) {
            // 1. The class file under its package path.
            jar.putNextEntry(new JarEntry(SAMPLE_RESOURCE));
            jar.write(classBytes);
            jar.closeEntry();

            // 2. The ServiceLoader manifest entry.
            jar.putNextEntry(new JarEntry(SERVICE_FILE));
            jar.write((SAMPLE_FQN + "\n").getBytes(StandardCharsets.UTF_8));
            jar.closeEntry();
        }

        return jarPath;
    }

    /**
     * Build a second, structurally-distinct plugin JAR carrying {@code OtherSamplePlugin}.
     * Same packaging recipe as {@link #buildSamplePluginJar(Path)} but a different class
     * file and a different ServiceLoader entry, so the two JARs declare two different
     * plugin ids and exercise multi-JAR discovery without registry-id collision.
     */
    private static Path buildOtherSamplePluginJar(Path dir) throws IOException {
        Path jarPath = dir.resolve("other-sample-plugin.jar");

        ClassLoader cl = PluginManagerJarDiscoveryTest.class.getClassLoader();
        byte[] classBytes;
        try (InputStream in = cl.getResourceAsStream(OTHER_RESOURCE)) {
            if (in == null) {
                throw new IllegalStateException(
                        "Test resource not found on classpath: " + OTHER_RESOURCE
                                + " — Maven test-compile didn't run, or OtherSamplePlugin moved.");
            }
            classBytes = in.readAllBytes();
        }

        try (JarOutputStream jar = new JarOutputStream(Files.newOutputStream(jarPath))) {
            jar.putNextEntry(new JarEntry(OTHER_RESOURCE));
            jar.write(classBytes);
            jar.closeEntry();

            jar.putNextEntry(new JarEntry(SERVICE_FILE));
            jar.write((OTHER_FQN + "\n").getBytes(StandardCharsets.UTF_8));
            jar.closeEntry();
        }

        return jarPath;
    }

    private static PluginManager managerFor(Path pluginDir) {
        return rigFor(pluginDir).manager;
    }

    /**
     * Manager + the spring mock it was wired to. Use this overload when a test needs to
     * verify {@link ApplicationContext#publishEvent(Object)} interactions; the simpler
     * {@link #managerFor(Path)} above just discards the mock.
     */
    private record Rig(PluginManager manager, ApplicationContext spring) {}

    private static Rig rigFor(Path pluginDir) {
        ApplicationContext spring = mock(ApplicationContext.class);
        when(spring.getBean(GeneratorRegistry.class)).thenReturn(new GeneratorRegistry(List.of()));
        when(spring.getBean(SolverRegistry.class)).thenReturn(new SolverRegistry(List.of()));
        PluginManager mgr = new PluginManager(new PluginRegistry(), spring, pluginDir.toString());
        return new Rig(mgr, spring);
    }

    @SuppressWarnings("unchecked")
    private static List<URLClassLoader> externalLoadersOf(PluginManager mgr) throws Exception {
        Field f = PluginManager.class.getDeclaredField("externalLoaders");
        f.setAccessible(true);
        return (List<URLClassLoader>) f.get(mgr);
    }

    /* ---------------------------------------------------------------------- */
    /* Tests                                                                  */
    /* ---------------------------------------------------------------------- */

    @Test
    void discover_loadsPluginFromJar_andTracksItsClassloader(@TempDir Path pluginDir) throws Exception {
        buildSamplePluginJar(pluginDir);

        mgr = managerFor(pluginDir);
        mgr.discover();

        // Plugin reached the registry.
        assertThat(mgr.loadedCount()).isEqualTo(1);
        PluginRegistry.Entry entry = mgr.registry().get("sample-plugin");
        assertThat(entry).isNotNull();
        assertThat(entry.manifest().displayName()).isEqualTo("Sample Plugin");
        assertThat(entry.manifest().version()).isEqualTo("1.0.0");
        assertThat(entry.state()).isEqualTo(PluginLifecycle.DISCOVERED);
        assertThat(entry.plugin()).isInstanceOf(MazePlugin.class);

        // The leak-fix tracking list received the JAR's classloader.
        List<URLClassLoader> loaders = externalLoadersOf(mgr);
        assertThat(loaders)
                .as("loadJar() must register the URLClassLoader so shutdownAll() can close it")
                .hasSize(1);
    }

    @Test
    void discover_thenBootAll_drivesPluginToStarted(@TempDir Path pluginDir) throws Exception {
        buildSamplePluginJar(pluginDir);

        mgr = managerFor(pluginDir);
        mgr.discover();
        mgr.bootAll();

        PluginRegistry.Entry entry = mgr.registry().get("sample-plugin");
        assertThat(entry).isNotNull();
        assertThat(entry.state()).isEqualTo(PluginLifecycle.STARTED);

        // SamplePlugin records every lifecycle call into its public 'calls' list — read it
        // back through the registered MazePlugin instance.
        SamplePlugin plugin = (SamplePlugin) entry.plugin();
        assertThat(plugin.calls).containsExactly("init", "register", "start");
    }

    @Test
    void shutdownAll_closesClassloaderRegisteredByDiscover(@TempDir Path pluginDir) throws Exception {
        buildSamplePluginJar(pluginDir);

        mgr = managerFor(pluginDir);
        mgr.discover();
        mgr.bootAll();

        List<URLClassLoader> loaders = externalLoadersOf(mgr);
        URLClassLoader plugged = loaders.get(0);

        mgr.shutdownAll();

        // List cleared.
        assertThat(externalLoadersOf(mgr)).isEmpty();

        // Loader closed: a closed URLClassLoader's findResource returns null for any new
        // resource lookup. (Stable behaviour across JDKs 8+.) We use a randomised name to
        // dodge any caching the loader may have done while open.
        String probe = "__probe_" + System.nanoTime();
        assertThat(plugged.findResource(probe))
                .as("URLClassLoader should be closed after shutdownAll()")
                .isNull();

        // And the underlying plugin's stop() must have been called.
        PluginRegistry.Entry entry = mgr.registry().get("sample-plugin");
        SamplePlugin plugin = (SamplePlugin) entry.plugin();
        assertThat(plugin.calls).contains("stop");
    }

    @Test
    void discover_withMultipleJars_isolatesEachInItsOwnClassloader(@TempDir Path pluginDir) throws Exception {
        // Drop two structurally-distinct plugin JARs into the same plugin directory.
        // Each JAR carries a different MazePlugin class with a different manifest id, so
        // both can coexist in the registry's id-keyed map without collision.
        Path sampleJar = buildSamplePluginJar(pluginDir);
        Path otherJar = buildOtherSamplePluginJar(pluginDir);

        mgr = managerFor(pluginDir);
        mgr.discover();

        // Both plugins reached the registry under their declared ids.
        assertThat(mgr.loadedCount()).isEqualTo(2);
        PluginRegistry.Entry sample = mgr.registry().get("sample-plugin");
        PluginRegistry.Entry other = mgr.registry().get("other-sample-plugin");
        assertThat(sample).isNotNull();
        assertThat(other).isNotNull();
        assertThat(sample.manifest().displayName()).isEqualTo("Sample Plugin");
        assertThat(other.manifest().displayName()).isEqualTo("Other Sample Plugin");
        assertThat(sample.manifest().version()).isEqualTo("1.0.0");
        assertThat(other.manifest().version()).isEqualTo("2.0.0");

        // Each JAR was loaded into its own URLClassLoader — that's the isolation guarantee
        // PluginManager.loadJar() advertises (one rogue plugin's classes can't leak into
        // another's), and the tracking list must hold both so shutdownAll() can release them.
        List<URLClassLoader> loaders = externalLoadersOf(mgr);
        assertThat(loaders)
                .as("each plugin JAR must be loaded into its own URLClassLoader")
                .hasSize(2);
        assertThat(loaders.get(0))
                .as("multi-JAR discovery must produce distinct loader instances per JAR — "
                        + "if loadJar() ever collapsed jars into a single loader, isolation breaks")
                .isNotSameAs(loaders.get(1));

        // Verify each loader's URL list points to exactly one of the two jars we wrote.
        // (We don't assert that plugin.getClass().getClassLoader() is the URLClassLoader
        // because Maven surefire's parent-first delegation lets the parent CL — which has
        // both fixture .class files on the classpath — define the class. That's a quirk
        // of the test runner, not a property of PluginManager. The loader-URL check below
        // is a more direct probe of the isolation invariant.)
        Set<String> trackedJarFiles = new HashSet<>();
        for (URLClassLoader cl : loaders) {
            URL[] urls = cl.getURLs();
            assertThat(urls)
                    .as("each per-jar URLClassLoader is created with exactly one jar URL")
                    .hasSize(1);
            trackedJarFiles.add(Paths.get(urls[0].toURI()).getFileName().toString());
        }
        assertThat(trackedJarFiles)
                .as("the two tracked classloaders cover both jars (no jar dropped, no jar duplicated)")
                .containsExactlyInAnyOrder(
                        sampleJar.getFileName().toString(),
                        otherJar.getFileName().toString());
    }

    @Test
    void discover_ignoresNonJarFiles_butStillLoadsJarsBesideThem(@TempDir Path pluginDir) throws Exception {
        // Drop a real JAR plus a few decoys with the wrong extension. PluginManager's
        // .endsWith(".jar") filter should pick the JAR and skip everything else, so
        // operators can leave READMEs, configs, and unrelated archives in the plugin
        // directory without breaking discovery.
        buildSamplePluginJar(pluginDir);
        Files.writeString(pluginDir.resolve("README.txt"), "ops notes — not a plugin");
        Files.writeString(pluginDir.resolve("config.yml"), "key: value");
        // Genuine ZIP magic bytes — proves the filter is extension-based, not content-sniffing.
        Files.write(pluginDir.resolve("archive.zip"), new byte[]{0x50, 0x4B, 0x03, 0x04});
        // A jar-named subdirectory must also be skipped (Files.list returns it but it
        // isn't a regular .jar file). The filter happens to do the right thing because
        // a directory's name often won't end in ".jar"; we explicitly use a non-.jar name.
        Files.createDirectory(pluginDir.resolve("subdir"));

        mgr = managerFor(pluginDir);
        mgr.discover();

        // Exactly the one real JAR was loaded.
        assertThat(mgr.loadedCount()).isEqualTo(1);
        assertThat(mgr.registry().get("sample-plugin")).isNotNull();
        assertThat(externalLoadersOf(mgr))
                .as("only the .jar should produce a tracked classloader")
                .hasSize(1);
    }

    @Test
    void discover_jarWithNoServiceFile_tracksLoaderButRegistersNothing(@TempDir Path pluginDir) throws Exception {
        // Build a JAR that has the SamplePlugin class file in it but NO
        // META-INF/services/com.daedalus.plugin.MazePlugin entry. ServiceLoader has
        // nothing to find, so iteration yields zero plugins — but the URLClassLoader
        // was still created and must still be tracked so shutdownAll() can release
        // its file handle (otherwise the JAR stays locked open).
        Path jarPath = pluginDir.resolve("no-service-file.jar");
        ClassLoader cl = PluginManagerJarDiscoveryTest.class.getClassLoader();
        byte[] classBytes;
        try (InputStream in = cl.getResourceAsStream(SAMPLE_RESOURCE)) {
            assertThat(in).as("test fixture missing on classpath").isNotNull();
            classBytes = in.readAllBytes();
        }
        try (JarOutputStream jar = new JarOutputStream(Files.newOutputStream(jarPath))) {
            jar.putNextEntry(new JarEntry(SAMPLE_RESOURCE));
            jar.write(classBytes);
            jar.closeEntry();
            // intentionally NO META-INF/services entry
        }

        mgr = managerFor(pluginDir);
        mgr.discover();

        // Registry stays empty — ServiceLoader had nothing to discover.
        assertThat(mgr.loadedCount()).isZero();
        assertThat(mgr.registry().get("sample-plugin")).isNull();

        // But the classloader was still created and tracked. This matters because
        // URLClassLoader takes a file handle on the JAR; without tracking,
        // shutdownAll() couldn't close it and Windows would refuse to delete the
        // jar from a temp dir.
        assertThat(externalLoadersOf(mgr))
                .as("loadJar() always tracks the URLClassLoader, even when ServiceLoader yields nothing")
                .hasSize(1);

        // Closing path still works cleanly.
        mgr.shutdownAll();
        assertThat(externalLoadersOf(mgr)).isEmpty();
    }

    @Test
    void discover_corruptJar_publishesPluginFailedEvent_discoverPhase(@TempDir Path pluginDir) throws Exception {
        // Build a JAR whose service file names a class that doesn't exist on the classpath
        // and isn't bundled inside the JAR. ServiceLoader will read the service entry, try
        // to load "com.example.GhostPlugin" from the per-jar URLClassLoader, fail with
        // ClassNotFoundException, and wrap that into ServiceConfigurationError.
        //
        // Because ServiceConfigurationError extends Error (not Exception), the original
        // catch (Exception e) in PluginManager.loadJar() did NOT catch it — discover() would
        // crash mid-iteration and the PluginFailedEvent.Phase.DISCOVER branch was effectively
        // unreachable. catch (Throwable t) closes that gap; this test locks it in.
        Path jarPath = pluginDir.resolve("ghost-plugin.jar");
        try (JarOutputStream jar = new JarOutputStream(Files.newOutputStream(jarPath))) {
            jar.putNextEntry(new JarEntry(SERVICE_FILE));
            jar.write("com.example.GhostPlugin\n".getBytes(StandardCharsets.UTF_8));
            jar.closeEntry();
            // Note: no class file for GhostPlugin — that's the whole point.
        }

        Rig rig = rigFor(pluginDir);
        mgr = rig.manager;

        // discover() must complete normally instead of escalating the Error up the stack.
        mgr.discover();

        // No plugins reached the registry — the only candidate was unloadable.
        assertThat(mgr.loadedCount()).isZero();

        // The classloader was still tracked (it was created before iteration failed) so
        // shutdownAll() will release the JAR file handle.
        assertThat(externalLoadersOf(mgr))
                .as("loadJar() tracks the URLClassLoader before iteration so shutdownAll() can close it")
                .hasSize(1);

        // The failure surfaced as a PluginFailedEvent on the DISCOVER phase. We capture
        // every event published during discover() — a healthy run publishes none, a single
        // corrupt jar must produce exactly one.
        ArgumentCaptor<Object> events = ArgumentCaptor.forClass(Object.class);
        verify(rig.spring).publishEvent(events.capture());
        Object published = events.getValue();
        assertThat(published).isInstanceOf(PluginFailedEvent.class);

        PluginFailedEvent event = (PluginFailedEvent) published;
        assertThat(event.pluginId())
                .as("when the plugin id is unknowable (the class never loaded), we report the JAR filename")
                .isEqualTo("ghost-plugin.jar");
        assertThat(event.phase()).isEqualTo(PluginFailedEvent.Phase.DISCOVER);
        assertThat(event.cause())
                .as("the underlying ServiceConfigurationError is preserved on the event for diagnostics")
                .isNotNull();
    }
}