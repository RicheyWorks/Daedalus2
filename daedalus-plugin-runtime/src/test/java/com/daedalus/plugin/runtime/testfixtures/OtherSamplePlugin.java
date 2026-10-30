// SPDX-License-Identifier: MIT

package com.daedalus.plugin.runtime.testfixtures;

import com.daedalus.plugin.MazePlugin;
import com.daedalus.plugin.PluginContext;
import com.daedalus.plugin.PluginManifest;

/**
 * Second {@link MazePlugin} fixture — a sibling of {@link SamplePlugin} with a different
 * manifest id ("other-sample-plugin").
 *
 * <p>Used by {@code PluginManagerJarDiscoveryTest#discover_withMultipleJars_*} to verify
 * that {@link com.daedalus.plugin.runtime.PluginManager#discover()} correctly handles
 * <em>multiple</em> plugin JARs in the same directory: each gets its own
 * {@link java.net.URLClassLoader}, both reach the registry, and the registry's
 * id-keyed map can hold them both without collision.
 *
 * <p>Lives in test sources so it compiles to {@code target/test-classes/} alongside
 * {@code SamplePlugin}, where the test reads its bytes back into a JAR file with its
 * own {@code META-INF/services/com.daedalus.plugin.MazePlugin} entry.
 */
public class OtherSamplePlugin implements MazePlugin {

    /** Per-instance trace of lifecycle callbacks. Public so the test can read it back. */
    public final java.util.List<String> calls = new java.util.ArrayList<>();

    @Override
    public PluginManifest manifest() {
        return new PluginManifest(
                "other-sample-plugin",
                "Other Sample Plugin",
                "2.0.0",
                "test",
                "Second tiny plugin used to assert multi-JAR discovery + classloader isolation.");
    }

    @Override public void init(PluginContext ctx)               { calls.add("init"); }
    @Override public void registerAlgorithms(PluginContext ctx) { calls.add("register"); }
    @Override public void start(PluginContext ctx)              { calls.add("start"); }
    @Override public void stop(PluginContext ctx)               { calls.add("stop"); }
}
