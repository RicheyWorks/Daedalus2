// SPDX-License-Identifier: MIT

package com.daedalus.plugin.runtime;

import com.daedalus.plugin.MazePlugin;
import com.daedalus.plugin.PluginManifest;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Plugin ids are claimed once, like algorithm ids. Until 2026-08-26 {@code put} was a
 * silent last-write-wins, and {@code sortedByDependencies} appended cyclic or missing
 * {@code requires} in undefined order.
 */
class PluginRegistryTest {

    private static MazePlugin plugin(String id, String... requires) {
        return () -> new PluginManifest(id, id, "1.0", "test", "test", requires);
    }

    @Test
    void aSecondPluginCannotClaimAnIdAlreadyTaken() {
        PluginRegistry registry = new PluginRegistry();
        MazePlugin first = plugin("dup");
        registry.put(first);

        assertThatThrownBy(() -> registry.put(plugin("dup")))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("dup")
                .hasMessageContaining("already claimed");
        assertThat(registry.get("dup").plugin()).isSameAs(first);
    }

    @Test
    void aCycleIsRefusedRatherThanAppended() {
        PluginRegistry registry = new PluginRegistry();
        registry.put(plugin("a", "b"));
        registry.put(plugin("b", "a"));

        assertThatThrownBy(registry::sortedByDependencies)
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("Unsatisfiable")
                .hasMessageContaining("a")
                .hasMessageContaining("b");
    }

    @Test
    void aMissingRequireIsRefusedRatherThanAppended() {
        PluginRegistry registry = new PluginRegistry();
        registry.put(plugin("child", "no-such-parent"));

        assertThatThrownBy(registry::sortedByDependencies)
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("Unsatisfiable")
                .hasMessageContaining("child");
    }

    @Test
    void aSatisfiedRequireStillBootsParentFirst() {
        PluginRegistry registry = new PluginRegistry();
        registry.put(plugin("child", "parent"));
        registry.put(plugin("parent"));

        assertThat(registry.sortedByDependencies())
                .extracting(e -> e.manifest().id())
                .containsExactly("parent", "child");
    }
}
