// SPDX-License-Identifier: MIT

package com.daedalus.plugin.runtime.testfixtures;

import com.daedalus.plugin.MazePlugin;
import com.daedalus.plugin.PluginContext;
import com.daedalus.plugin.PluginManifest;

/**
 * Sample {@link MazePlugin} packaged into a real JAR by {@code PluginManagerJarDiscoveryTest}.
 *
 * <p>Lives in test sources so it compiles to {@code target/test-classes/} alongside the test
 * itself, where the test can read its bytes back and stuff them into a JAR file along with a
 * {@code META-INF/services/com.daedalus.plugin.MazePlugin} entry. The resulting JAR is a
 * faithful, minimal example of what an external plugin distribution looks like.
 *
 * <p>Tracks lifecycle calls so the test can assert that the plugin reached
 * {@code init → registerAlgorithms → start} after {@code PluginManager.bootAll()}.
 */
public class SamplePlugin implements MazePlugin {

    /**
     * Per-instance trace of lifecycle callbacks. Public so the test can read it back from the
     * registered plugin entry. Reset is a no-op — the plugin lives only for the duration of one
     * test method.
     */
    public final java.util.List<String> calls = new java.util.ArrayList<>();

    @Override
    public PluginManifest manifest() {
        return new PluginManifest(
                "sample-plugin",
                "Sample Plugin",
                "1.0.0",
                "test",
                "Tiny plugin packaged into a real JAR for the discovery test.");
    }

    @Override public void init(PluginContext ctx)               { calls.add("init"); }
    @Override public void registerAlgorithms(PluginContext ctx) { calls.add("register"); }
    @Override public void start(PluginContext ctx)              { calls.add("start"); }
    @Override public void stop(PluginContext ctx)               { calls.add("stop"); }
}
