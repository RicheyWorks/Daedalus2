// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.api.dto.WorldEventFrame;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.WorldService;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.Parcel;
import com.daedalus.world.World;
import com.daedalus.world.WorldId;
import com.daedalus.world.stamp.StampResult;

/**
 * Desktop world inspect line — revision and last event, not a voxel viewport.
 * Maze generate / solve stay on their own controls.
 */
public final class DesktopWorld {

    public static final String ID = WorldId.ZERO.value();
    /** Torch wood — same as well {@code #worldBox .place} / explore MAP_BLOCK. */
    public static final String PLACE_INK = "#94612e";
    public static final String PLACE_CLASS = "world-place";

    private DesktopWorld() {
    }

    /**
     * Project a generated lab maze into world-zero. Occupied origin
     * walks +X. Daily / campaign stay inspect-only.
     */
    public static StampResult projectLab(WorldService worlds, MazeGenerationService.Cached maze) {
        if (worlds == null || maze == null || maze.grid() == null
                || maze.metadata() == null || maze.metadata().id() == null) {
            return null;
        }
        return worlds.stamp(ID, new BlockCoordinate(0, 0, 0), maze.grid(),
                maze.metadata().id(), true);
    }

    public static String inspectLine(World world, WorldEventFrame last) {
        if (world == null) {
            return ID + " · unavailable";
        }
        return inspectLine(world.revision().value(), world.parcels().size(), firstPlace(world),
                lastLease(world), lastMaze(world), last);
    }

    public static String inspectLine(long revision, WorldEventFrame last) {
        return inspectLine(revision, "", last);
    }

    public static String inspectLine(long revision, String place, WorldEventFrame last) {
        return inspectLine(revision, place, "", last);
    }

    public static String inspectLine(long revision, String place, String lease, WorldEventFrame last) {
        return inspectLine(revision, place, lease, "", last);
    }

    public static String inspectLine(long revision, String place, String lease, String maze,
            WorldEventFrame last) {
        return inspectLine(revision, 0, place, lease, maze, last);
    }

    public static String inspectLine(long revision, int plots, String place, String lease, String maze,
            WorldEventFrame last) {
        String head = ID + " r=" + revision;
        if (plots > 1) {
            head += " · " + plots + " plots";
        }
        if (place != null && !place.isBlank()) {
            head += " · " + place;
        }
        if (lease != null && !lease.isBlank()) {
            head += " · " + lease;
        }
        if (maze != null && !maze.isBlank()) {
            head += " · " + maze;
        }
        if (last == null) {
            return head + " · listening";
        }
        return head + " · " + last.kind() + " "
                + last.x() + "," + last.y() + "," + last.z()
                + " " + last.type();
    }

    /** First inspired toponym on inspect — same well place row, not GIS. */
    public static String firstPlace(World world) {
        if (world == null) {
            return "";
        }
        for (Parcel parcel : world.parcels()) {
            if (parcel != null && !parcel.placeName().isEmpty()) {
                return parcel.placeName();
            }
        }
        return "";
    }

    /** Newest lease string on inspect — account key, not a wallet. */
    public static String lastLease(World world) {
        if (world == null) {
            return "";
        }
        String found = "";
        for (Parcel parcel : world.parcels()) {
            if (parcel != null && !parcel.leaseId().isEmpty()) {
                found = parcel.leaseId();
            }
        }
        return found;
    }

    /** First lease string on inspect — account key, not a wallet. */
    public static String firstLease(World world) {
        if (world == null) {
            return "";
        }
        for (Parcel parcel : world.parcels()) {
            if (parcel != null && !parcel.leaseId().isEmpty()) {
                return parcel.leaseId();
            }
        }
        return "";
    }

    /** Newest lab maze id on inspect — not a wallet. */
    public static String lastMaze(World world) {
        if (world == null) {
            return "";
        }
        String found = "";
        for (Parcel parcel : world.parcels()) {
            if (parcel != null && !parcel.mazeRef().isEmpty()) {
                found = parcel.mazeRef();
            }
        }
        return found;
    }

    /** First lab maze id on inspect — not a wallet. */
    public static String firstMaze(World world) {
        if (world == null) {
            return "";
        }
        for (Parcel parcel : world.parcels()) {
            if (parcel != null && !parcel.mazeRef().isEmpty()) {
                return parcel.mazeRef();
            }
        }
        return "";
    }
}
