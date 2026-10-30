// SPDX-License-Identifier: MIT

package com.daedalus.explore;

/** One headset frame's look intent. Desktop GLFW still owns translation. */
public record XrFrame(double yawDelta, double pitchDelta, boolean snapLeft, boolean snapRight) {
    public static XrFrame none() {
        return new XrFrame(0, 0, false, false);
    }
}
