// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Portal inspect — same facts automation reads. Place, lot, and box are empty off a slab. */
public record PortalInspectResponse(
        String id, String worldId, int x, int y, int z, String state,
        String place, String lot, String acl, String drive, String driveActor, String driveAt,
        String box) {

    public PortalInspectResponse {
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        acl = acl == null ? "" : acl;
        drive = drive == null ? "" : drive;
        driveActor = driveActor == null ? "" : driveActor;
        driveAt = driveAt == null ? "" : driveAt;
        box = box == null ? "" : box;
    }

    public PortalInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot, String acl, String drive, String driveActor, String driveAt) {
        this(id, worldId, x, y, z, state, place, lot, acl, drive, driveActor, driveAt, "");
    }

    public PortalInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot, String acl, String drive, String driveActor) {
        this(id, worldId, x, y, z, state, place, lot, acl, drive, driveActor, "", "");
    }

    public PortalInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot, String acl) {
        this(id, worldId, x, y, z, state, place, lot, acl, "", "", "", "");
    }

    public PortalInspectResponse(
            String id, String worldId, int x, int y, int z, String state,
            String place, String lot) {
        this(id, worldId, x, y, z, state, place, lot, "", "", "", "", "");
    }

    public PortalInspectResponse(String id, String worldId, int x, int y, int z, String state) {
        this(id, worldId, x, y, z, state, "", "", "", "", "", "", "");
    }
}
