// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of dropping an extra parcel denial. {@code result} is never silent success. */
public record ParcelForgiveResponse(String result, String acl, long revision, String maze,
                                   String lease, String place) {

    public ParcelForgiveResponse {
        result = result == null ? "" : result;
        acl = acl == null ? "" : acl;
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
        place = place == null ? "" : place;
    }

    public ParcelForgiveResponse(String result, String acl, long revision, String maze,
                                String lease) {
        this(result, acl, revision, maze, lease, "");
    }

    public ParcelForgiveResponse(String result, String acl, long revision, String maze) {
        this(result, acl, revision, maze, "", "");
    }

    public ParcelForgiveResponse(String result, String acl, long revision) {
        this(result, acl, revision, "", "", "");
    }
}
