// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of open or seal. {@code result} is never silent success. */
public record PortalMutationResponse(String id, String state, String result, long revision,
                                     String maze, String lease, String place, String lot,
                                     String box, String acl) {

    public PortalMutationResponse {
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        box = box == null ? "" : box;
        acl = acl == null ? "" : acl;
    }

    public PortalMutationResponse(String id, String state, String result, long revision,
                                  String maze, String lease, String place, String lot,
                                  String box) {
        this(id, state, result, revision, maze, lease, place, lot, box, "");
    }

    public PortalMutationResponse(String id, String state, String result, long revision,
                                  String maze, String lease, String place, String lot) {
        this(id, state, result, revision, maze, lease, place, lot, "", "");
    }

    public PortalMutationResponse(String id, String state, String result, long revision,
                                  String maze, String lease, String place) {
        this(id, state, result, revision, maze, lease, place, "", "", "");
    }

    public PortalMutationResponse(String id, String state, String result, long revision,
                                  String maze, String lease) {
        this(id, state, result, revision, maze, lease, "", "", "", "");
    }

    public PortalMutationResponse(String id, String state, String result, long revision,
                                  String maze) {
        this(id, state, result, revision, maze, "", "", "", "", "");
    }

    public PortalMutationResponse(String id, String state, String result, long revision) {
        this(id, state, result, revision, "", "", "", "", "", "");
    }
}
