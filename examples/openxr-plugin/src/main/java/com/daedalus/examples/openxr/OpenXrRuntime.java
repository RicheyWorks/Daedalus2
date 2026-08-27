// SPDX-License-Identifier: MIT

package com.daedalus.examples.openxr;

import com.daedalus.explore.ExploreWorld;
import com.daedalus.explore.XrFrame;
import com.daedalus.explore.XrRuntime;

/**
 * OpenXR backend. {@link #present()} is opt-in so CI never loads a headset
 * runtime. A later slice can bind LWJGL OpenXR behind this same SPI.
 */
public final class OpenXrRuntime implements XrRuntime {

    public static final String ENV = "DAEDALUS_OPENXR";

    private boolean attached;
    private boolean stopped;
    private int frames;

    @Override
    public String id() {
        return "openxr";
    }

    @Override
    public boolean present() {
        return "1".equals(System.getenv(ENV));
    }

    @Override
    public void attach(ExploreWorld world) {
        this.attached = world != null;
    }

    @Override
    public XrFrame beginFrame() {
        frames++;
        return XrFrame.none();
    }

    @Override
    public void endFrame(XrFrame frame) {
    }

    @Override
    public void stop() {
        stopped = true;
    }

    boolean attached() {
        return attached;
    }

    boolean stopped() {
        return stopped;
    }

    int frames() {
        return frames;
    }
}
