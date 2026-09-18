// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** NPC inspect — same facts automation reads. Place, lot, box, and maze are empty off a slab. */
public record NpcInspectResponse(
        String id, String worldId, int x, int y, int z, String state,
        String place, String lot, String acl, String drive, String driveActor, String driveAt,
        String box, String maze) {

    public NpcInspectResponse {
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        acl = acl == null ? "" : acl;
        drive = drive == null ? "" : drive;
        driveActor = driveActor == null ? "" : driveActor;
        driveAt = driveAt == null ? "" : driveAt;
        box = box == null ? "" : box;
        maze = maze == null ? "" : maze;
    }

    public NpcInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot, String acl, String drive, String driveActor, String driveAt,
            String box) {
        this(id, worldId, x, y, z, state, place, lot, acl, drive, driveActor, driveAt, box, "");
    }

    public NpcInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot, String acl, String drive, String driveActor, String driveAt) {
        this(id, worldId, x, y, z, state, place, lot, acl, drive, driveActor, driveAt, "", "");
    }

    public NpcInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot, String acl, String drive, String driveActor) {
        this(id, worldId, x, y, z, state, place, lot, acl, drive, driveActor, "", "", "");
    }

    public NpcInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot, String acl) {
        this(id, worldId, x, y, z, state, place, lot, acl, "", "", "", "", "");
    }

    public NpcInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot) {
        this(id, worldId, x, y, z, state, place, lot, "", "", "", "", "", "");
    }

    public NpcInspectResponse(String id, String worldId, int x, int y, int z, String state) {
        this(id, worldId, x, y, z, state, "", "", "", "", "", "", "", "");
    }
}
