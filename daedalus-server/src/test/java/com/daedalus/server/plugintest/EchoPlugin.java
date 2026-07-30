// SPDX-License-Identifier: MIT

package com.daedalus.server.plugintest;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.plugin.MazePlugin;
import com.daedalus.plugin.PluginContext;
import com.daedalus.plugin.PluginManifest;

/**
 * Test-fixture plugin for {@code PluginSpiEndToEndTest}: contributes one generator with an id
 * no built-in uses, so its presence in the registries proves the whole discovery → lifecycle
 * → registration chain ran. Packaged into a JAR at test time from its compiled class file
 * (same recipe as the runtime module's discovery tests).
 */
public final class EchoPlugin implements MazePlugin {

    /** Delegates to BinaryTree under a plugin-owned id — texture is irrelevant, identity isn't. */
    public static final class EchoGenerator implements MazeGenerator {
        private final BinaryTreeGenerator delegate = new BinaryTreeGenerator();

        @Override
        public String id() {
            return "plugin-echo";
        }

        @Override
        public String displayName() {
            return "Echo (plugin fixture)";
        }

        @Override
        public AlgorithmDescriptor descriptor() {
            return new AlgorithmDescriptor(id(), displayName(), "generator",
                    "O(n) time", "Delegates to Binary Tree",
                    "Test-fixture generator contributed by EchoPlugin.");
        }

        @Override
        public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
            return delegate.generate(rows, cols, seed, stats);
        }
    }

    @Override
    public PluginManifest manifest() {
        return new PluginManifest("echo-plugin", "Echo Plugin", "1.0.0",
                "fixture", "SPI end-to-end test fixture");
    }

    @Override
    public void registerAlgorithms(PluginContext ctx) {
        ctx.generators().register(new EchoGenerator());
    }
}
