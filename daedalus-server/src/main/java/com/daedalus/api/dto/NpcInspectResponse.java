// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** NPC inspect — same facts automation reads. Place and lot are empty off a slab. */
public record NpcInspectResponse(
        String id, String worldId, int x, int y, int z, String state,
        String place, String lot, String acl, String drive, String driveActor) {

    public NpcInspectResponse {
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        acl = acl == null ? "" : acl;
        drive = drive == null ? "" : drive;
        driveActor = driveActor == null ? "" : driveActor;
    }

    public NpcInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot, String acl) {
        this(id, worldId, x, y, z, state, place, lot, acl, "", "");
    }

    public NpcInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot) {
        this(id, worldId, x, y, z, state, place, lot, "", "", "");
    }

    public NpcInspectResponse(String id, String worldId, int x, int y, int z, String state) {
        this(id, worldId, x, y, z, state, "", "", "", "", "");
    }
}
