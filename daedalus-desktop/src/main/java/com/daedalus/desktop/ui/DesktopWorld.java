// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.api.dto.WorldEventFrame;
import com.daedalus.world.World;
import com.daedalus.world.WorldId;

/**
 * Desktop world inspect line — revision and last event, not a voxel viewport.
 * Maze generate / solve stay on their own controls.
 */
public final class DesktopWorld {

    public static final String ID = WorldId.ZERO.value();

    private DesktopWorld() {
    }

    public static String inspectLine(World world, WorldEventFrame last) {
        if (world == null) {
            return ID + " · unavailable";
        }
        return inspectLine(world.revision().value(), last);
    }

    public static String inspectLine(long revision, WorldEventFrame last) {
        if (last == null) {
            return ID + " r=" + revision + " · listening";
        }
        return ID + " r=" + revision + " · " + last.kind() + " "
                + last.x() + "," + last.y() + "," + last.z()
                + " " + last.type();
    }
}
