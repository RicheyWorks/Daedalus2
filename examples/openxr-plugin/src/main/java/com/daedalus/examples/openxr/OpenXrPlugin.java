// SPDX-License-Identifier: MIT

package com.daedalus.examples.openxr;

import com.daedalus.plugin.AbstractPlugin;
import com.daedalus.plugin.PluginManifest;

/**
 * Lists the OpenXR runtime on {@code GET /api/v1/plugins} when dropped
 * into the host plugins directory. The explore host loads {@link OpenXrRuntime}
 * via {@code ServiceLoader}, not this class.
 */
public final class OpenXrPlugin extends AbstractPlugin {

    @Override
    public PluginManifest manifest() {
        return new PluginManifest(
                "openxr",
                "OpenXR headset",
                "1.2.0-SNAPSHOT",
                "RicheyWorks",
                "Optional XrRuntime — present only when DAEDALUS_OPENXR=1");
    }
}
