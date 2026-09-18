// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * World-level inspect. Not a maze snapshot — no tiles, no Caffeine id.
 * Street fields are empty strings when the world has no plots.
 */
public record WorldInspectResponse(
        String id,
        long revision,
        int chunkCount,
        int plots,
        String street,
        String lot,
        String maze,
        String lease,
        String place,
        String occupants,
        String stands,
        String acl,
        String drive) {

    public WorldInspectResponse {
        street = street == null ? "" : street;
        lot = lot == null ? "" : lot;
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
        place = place == null ? "" : place;
        occupants = occupants == null ? "" : occupants;
        stands = stands == null ? "" : stands;
        acl = acl == null ? "" : acl;
        drive = drive == null ? "" : drive;
        if (plots < 0) {
            throw new IllegalArgumentException("plots must be at least 0");
        }
    }

    public WorldInspectResponse(
            String id, long revision, int chunkCount, int plots,
            String street, String lot, String maze, String lease, String place,
            String occupants, String stands, String acl) {
        this(id, revision, chunkCount, plots, street, lot, maze, lease, place,
                occupants, stands, acl, "");
    }

    public WorldInspectResponse(
            String id, long revision, int chunkCount, int plots,
            String street, String lot, String maze, String lease, String place,
            String occupants, String stands) {
        this(id, revision, chunkCount, plots, street, lot, maze, lease, place,
                occupants, stands, "", "");
    }

    public WorldInspectResponse(
            String id, long revision, int chunkCount, int plots,
            String street, String lot, String maze, String lease, String place,
            String occupants) {
        this(id, revision, chunkCount, plots, street, lot, maze, lease, place,
                occupants, "", "", "");
    }
}
