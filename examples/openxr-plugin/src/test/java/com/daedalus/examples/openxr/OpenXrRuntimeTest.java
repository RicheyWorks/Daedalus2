// SPDX-License-Identifier: MIT

package com.daedalus.examples.openxr;

import com.daedalus.explore.ExploreWorld;
import com.daedalus.explore.XrFrame;
import com.daedalus.plugin.PluginManifest;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class OpenXrRuntimeTest {

    @Test
    void absentByDefaultSoVerifyNeedsNoHeadset() {
        OpenXrRuntime runtime = new OpenXrRuntime();
        assertThat(runtime.present()).isFalse();
        assertThat(runtime.id()).isEqualTo("openxr");
        runtime.attach(ExploreWorld.dungeon(5, 5, 1L));
        assertThat(runtime.attached()).isTrue();
        assertThat(runtime.beginFrame()).isEqualTo(XrFrame.none());
        runtime.endFrame(XrFrame.none());
        runtime.stop();
        assertThat(runtime.stopped()).isTrue();
        assertThat(runtime.frames()).isEqualTo(1);
    }

    @Test
    void thePluginListsTheRuntime() {
        OpenXrPlugin plugin = new OpenXrPlugin();
        PluginManifest manifest = plugin.manifest();
        assertThat(manifest.id()).isEqualTo("openxr");
        assertThat(manifest.displayName()).contains("OpenXR");
    }
}
