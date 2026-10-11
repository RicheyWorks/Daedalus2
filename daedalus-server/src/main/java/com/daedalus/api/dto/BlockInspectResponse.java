// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * One cube. {@code present} is false when the cell is AIR (missing chunk or removed).
 * Street fields are empty off a slab.
 */
public record BlockInspectResponse(int x, int y, int z, String type, boolean present,
                                   String place, String lot, String lease, String maze,
                                   String occupant, String acl, String drive, String driveActor,
                                   String driveAt, String box) {

    public BlockInspectResponse {
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        lease = lease == null ? "" : lease;
        maze = maze == null ? "" : maze;
        occupant = occupant == null ? "" : occupant;
        acl = acl == null ? "" : acl;
        drive = drive == null ? "" : drive;
        driveActor = driveActor == null ? "" : driveActor;
        driveAt = driveAt == null ? "" : driveAt;
        box = box == null ? "" : box;
    }

    public BlockInspectResponse(int x, int y, int z, String type, boolean present,
                                String place, String lot, String lease, String maze,
                                String occupant, String acl, String drive, String driveActor,
                                String driveAt) {
        this(x, y, z, type, present, place, lot, lease, maze, occupant, acl, drive, driveActor,
                driveAt, "");
    }

    public BlockInspectResponse(int x, int y, int z, String type, boolean present,
                                String place, String lot, String lease, String maze,
                                String occupant, String acl, String drive, String driveActor) {
        this(x, y, z, type, present, place, lot, lease, maze, occupant, acl, drive, driveActor,
                "", "");
    }

    public BlockInspectResponse(int x, int y, int z, String type, boolean present,
                                String place, String lot, String lease, String maze,
                                String occupant, String acl) {
        this(x, y, z, type, present, place, lot, lease, maze, occupant, acl, "", "", "", "");
    }

    public BlockInspectResponse(int x, int y, int z, String type, boolean present,
                                String place, String lot, String lease, String maze,
                                String occupant) {
        this(x, y, z, type, present, place, lot, lease, maze, occupant, "", "", "", "", "");
    }
}
