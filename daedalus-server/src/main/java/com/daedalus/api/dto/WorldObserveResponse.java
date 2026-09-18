// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Read-back after a drive. Inspect: does not bump revision.
 * {@code place} and {@code lot} are empty off a slab.
 */
public record WorldObserveResponse(String worldId, long revision, int x, int y, int z,
                                   String blockType, String doorState, String place, String lot,
                                   String occupant, String acl, String drive, String driveActor,
                                   String driveAt) {

    public WorldObserveResponse {
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        occupant = occupant == null ? "" : occupant;
        acl = acl == null ? "" : acl;
        drive = drive == null ? "" : drive;
        driveActor = driveActor == null ? "" : driveActor;
        driveAt = driveAt == null ? "" : driveAt;
    }

    public WorldObserveResponse(String worldId, long revision, int x, int y, int z,
                                String blockType, String doorState, String place, String lot,
                                String occupant, String acl, String drive, String driveActor) {
        this(worldId, revision, x, y, z, blockType, doorState, place, lot, occupant, acl,
                drive, driveActor, "");
    }

    public WorldObserveResponse(String worldId, long revision, int x, int y, int z,
                                String blockType, String doorState, String place, String lot,
                                String occupant, String acl) {
        this(worldId, revision, x, y, z, blockType, doorState, place, lot, occupant, acl, "", "", "");
    }

    public WorldObserveResponse(String worldId, long revision, int x, int y, int z,
                                String blockType, String doorState, String place, String lot,
                                String occupant) {
        this(worldId, revision, x, y, z, blockType, doorState, place, lot, occupant, "", "", "", "");
    }
}
