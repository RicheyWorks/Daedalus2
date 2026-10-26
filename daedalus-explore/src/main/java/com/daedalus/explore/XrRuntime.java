// SPDX-License-Identifier: MIT

package com.daedalus.explore;

/**
 * Headset backend. Implementations live in plugin JARs (OpenXR first).
 * The host is valid with zero runtimes attached.
 */
public interface XrRuntime {

    String id();

    boolean present();

    default void attach(ExploreWorld world) {
    }

    default XrFrame beginFrame() {
        return XrFrame.none();
    }

    default void endFrame(XrFrame frame) {
    }

    default void stop() {
    }
}
