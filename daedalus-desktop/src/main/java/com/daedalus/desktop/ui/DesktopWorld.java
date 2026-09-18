// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.api.dto.WorldEventFrame;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.WorldService;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.ChunkCoordinate;
import com.daedalus.world.Parcel;
import com.daedalus.world.World;
import com.daedalus.world.WorldId;
import com.daedalus.world.auto.DriveTrace;
import com.daedalus.world.auto.WorldOps;
import com.daedalus.world.stamp.StampResult;

import java.util.ArrayList;
import java.util.List;

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
        StampResult stamped = worlds.stamp(ID, new BlockCoordinate(0, 0, 0), maze.grid(),
                maze.metadata().id(), true);
        if (stamped != null && stamped.ok()) {
            worlds.leaseParcel(ID);
        }
        return stamped;
    }

    public static String inspectLine(World world, WorldEventFrame last, DriveTrace.Step lastDrive) {
        String line = inspectLine(world, last);
        String driven = driveLine(lastDrive);
        if (!driven.isEmpty()) {
            line = line + " · " + driven;
        }
        String actor = actorLine(world);
        return actor.isEmpty() ? line : line + " · " + actor;
    }

    /** Last driven capability and named result — same well builder line. */
    public static String driveLine(DriveTrace.Step last) {
        return WorldOps.driveLine(last);
    }

    /**
     * Account key that last drove a mutation. Empty until a mutation.
     * Never a wallet type.
     */
    public static String actorLine(World world) {
        return WorldOps.actorLine(world);
    }

    public static String inspectLine(World world, WorldEventFrame last) {
        if (world == null) {
            return ID + " · unavailable";
        }
        String place = streetLine(world);
        if (world.parcels().size() > 1) {
            String lots = streetLots(world);
            if (!lots.isEmpty()) {
                place = place.isEmpty() ? lots : place + " · " + lots;
            }
        }
        String line = inspectLine(world.revision().value(), world.parcels().size(), place,
                lastLease(world), streetMazes(world), last);
        String occ = occupancyLine(world);
        if (occ.isEmpty()) {
            occ = chunkOccupants(world, last);
            String stands = chunkStands(world, last);
            if (!stands.isEmpty()) {
                occ = occ.isEmpty() ? stands : occ + " · " + stands;
            }
        }
        if (!occ.isEmpty()) {
            line = line + " · " + occ;
        }
        String at = eventLot(world, last);
        if (!at.isEmpty()) {
            line = line + " · " + at;
        }
        String acl = aclLine(world);
        return acl.isEmpty() ? line : line + " · " + acl;
    }

    /**
     * Extra grants and denials. Owner stays implicit. Empty with no extras.
     */
    public static String aclLine(World world) {
        return WorldOps.aclLine(world);
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

    /**
     * Occupancy objects in the live 16³. Last-event chunk when
     * a frame is present, otherwise origin. Empty far off the volume.
     */
    public static String chunkOccupants(World world, WorldEventFrame last) {
        if (world == null) {
            return "";
        }
        ChunkCoordinate cc = last == null
                ? new ChunkCoordinate(0, 0, 0)
                : new BlockCoordinate(last.x(), last.y(), last.z()).chunk();
        return WorldOps.occupantsInChunk(world, cc);
    }

    /**
     * Occupancy cells in the live 16³ as kind + x,y,z.
     * Occupants stay names-only. Empty far off the volume.
     */
    public static String chunkStands(World world, WorldEventFrame last) {
        if (world == null) {
            return "";
        }
        ChunkCoordinate cc = last == null
                ? new ChunkCoordinate(0, 0, 0)
                : new BlockCoordinate(last.x(), last.y(), last.z()).chunk();
        return WorldOps.standsInChunk(world, cc);
    }

    /**
     * Occupancy cells that sit on a slab, oldest object first.
     * Off-plot door-zero stays silent.
     */
    public static String occupancyLine(World world) {
        if (world == null) {
            return "";
        }
        List<String> rows = new ArrayList<>();
        addOccupancy(rows, "door", world.door() == null ? null : world.door().at(), world);
        addOccupancy(rows, "trap", world.trap() == null ? null : world.trap().at(), world);
        addOccupancy(rows, "portal", world.portal() == null ? null : world.portal().at(), world);
        addOccupancy(rows, "npc", world.npc() == null ? null : world.npc().at(), world);
        return String.join(" · ", rows);
    }

    private static void addOccupancy(List<String> rows, String kind, BlockCoordinate at, World world) {
        if (at == null) {
            return;
        }
        String named = WorldOps.placeAt(world, at);
        String lot = WorldOps.lotAt(world, at);
        if (named.isEmpty() && lot.isEmpty()) {
            return;
        }
        String label = named.isEmpty() ? lot : (lot.isEmpty() ? named : named + " " + lot);
        rows.add(kind + " " + label);
    }

    /**
     * Place, lot, and occupant under the last event cube.
     * Empty off a slab unless that cell is door, trap, portal, or NPC.
     */
    public static String eventLot(World world, WorldEventFrame last) {
        if (world == null || last == null) {
            return "";
        }
        BlockCoordinate cell = new BlockCoordinate(last.x(), last.y(), last.z());
        String named = WorldOps.placeAt(world, cell);
        String lot = WorldOps.lotAt(world, cell);
        String who = WorldOps.occupantAt(world, cell);
        String at = named.isEmpty() ? lot : (lot.isEmpty() ? named : named + " " + lot);
        if (at.isEmpty()) {
            return who;
        }
        return who.isEmpty() ? at : at + " " + who;
    }

    /** All inspired toponyms on inspect — not GIS. */
    public static String streetLine(World world) {
        return WorldOps.streetLine(world);
    }

    /** Newest slab origin as {@code x,z}. */
    public static String lastLot(World world) {
        return WorldOps.lastLot(world);
    }

    /** All slab origins as {@code x,z}, oldest first. */
    public static String streetLots(World world) {
        return WorldOps.streetLots(world);
    }

    /** Newest inspired toponym on inspect — not GIS. */
    public static String lastPlace(World world) {
        if (world == null) {
            return "";
        }
        String found = "";
        for (Parcel parcel : world.parcels()) {
            if (parcel != null && !parcel.placeName().isEmpty()) {
                found = parcel.placeName();
            }
        }
        return found;
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

    /** All lab maze ids on inspect — not a wallet. */
    public static String streetMazes(World world) {
        return WorldOps.streetMazes(world);
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
