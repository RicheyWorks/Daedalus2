// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * STOMP frame on {@code /topic/world/{id}/events}. Separate from maze {@code /state}.
 */
public record WorldEventFrame(
        String worldId,
        String kind,
        int x,
        int y,
        int z,
        String type,
        String previous,
        long revision,
        String place,
        String lot,
        String occupant,
        String drive,
        String driveActor,
        String driveAt,
        String box,
        String maze,
        String lease) {

    public WorldEventFrame {
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        occupant = occupant == null ? "" : occupant;
        drive = drive == null ? "" : drive;
        driveActor = driveActor == null ? "" : driveActor;
        driveAt = driveAt == null ? "" : driveAt;
        box = box == null ? "" : box;
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
    }

    public WorldEventFrame(String worldId, String kind, int x, int y, int z,
            String type, String previous, long revision, String place, String lot,
            String occupant, String drive, String driveActor, String driveAt,
            String box, String maze) {
        this(worldId, kind, x, y, z, type, previous, revision, place, lot, occupant,
                drive, driveActor, driveAt, box, maze, "");
    }

    public WorldEventFrame(String worldId, String kind, int x, int y, int z,
            String type, String previous, long revision, String place, String lot,
            String occupant, String drive, String driveActor, String driveAt,
            String box) {
        this(worldId, kind, x, y, z, type, previous, revision, place, lot, occupant,
                drive, driveActor, driveAt, box, "", "");
    }

    public WorldEventFrame(String worldId, String kind, int x, int y, int z,
            String type, String previous, long revision, String place, String lot,
            String occupant, String drive, String driveActor, String driveAt) {
        this(worldId, kind, x, y, z, type, previous, revision, place, lot, occupant,
                drive, driveActor, driveAt, "", "", "");
    }

    public WorldEventFrame(String worldId, String kind, int x, int y, int z,
            String type, String previous, long revision, String place, String lot,
            String occupant) {
        this(worldId, kind, x, y, z, type, previous, revision, place, lot, occupant,
                "", "", "", "", "", "");
    }

    public WorldEventFrame(String worldId, String kind, int x, int y, int z,
            String type, String previous, long revision) {
        this(worldId, kind, x, y, z, type, previous, revision, "", "", "", "", "", "",
                "", "", "");
    }

    public WorldEventFrame(String worldId, String kind, int x, int y, int z,
            String type, String previous, long revision, String place, String lot) {
        this(worldId, kind, x, y, z, type, previous, revision, place, lot, "", "", "",
                "", "", "", "");
    }
}
