// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Door inspect — same facts automation reads. Place, lot, box, maze, and lease are empty off a slab. */
public record DoorInspectResponse(
        String id, String worldId, int x, int y, int z, String state,
        String place, String lot, String acl, String drive, String driveActor, String driveAt,
        String box, String maze, String lease) {

    public DoorInspectResponse {
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        acl = acl == null ? "" : acl;
        drive = drive == null ? "" : drive;
        driveActor = driveActor == null ? "" : driveActor;
        driveAt = driveAt == null ? "" : driveAt;
        box = box == null ? "" : box;
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
    }

    public DoorInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot, String acl, String drive, String driveActor, String driveAt,
            String box, String maze) {
        this(id, worldId, x, y, z, state, place, lot, acl, drive, driveActor, driveAt, box, maze, "");
    }

    public DoorInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot, String acl, String drive, String driveActor, String driveAt,
            String box) {
        this(id, worldId, x, y, z, state, place, lot, acl, drive, driveActor, driveAt, box, "", "");
    }

    public DoorInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot, String acl, String drive, String driveActor, String driveAt) {
        this(id, worldId, x, y, z, state, place, lot, acl, drive, driveActor, driveAt, "", "", "");
    }

    public DoorInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot, String acl, String drive, String driveActor) {
        this(id, worldId, x, y, z, state, place, lot, acl, drive, driveActor, "", "", "", "");
    }

    public DoorInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot, String acl) {
        this(id, worldId, x, y, z, state, place, lot, acl, "", "", "", "", "", "");
    }

    public DoorInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot) {
        this(id, worldId, x, y, z, state, place, lot, "", "", "", "", "", "", "");
    }

    public DoorInspectResponse(String id, String worldId, int x, int y, int z, String state) {
        this(id, worldId, x, y, z, state, "", "", "", "", "", "", "", "", "");
    }
}
