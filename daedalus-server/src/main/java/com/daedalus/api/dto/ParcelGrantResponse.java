// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of an extra parcel grant. {@code result} is never silent success. */
public record ParcelGrantResponse(String result, String acl, long revision, String maze,
                                 String lease, String place, String lot, String box) {

    public ParcelGrantResponse {
        result = result == null ? "" : result;
        acl = acl == null ? "" : acl;
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        box = box == null ? "" : box;
    }

    public ParcelGrantResponse(String result, String acl, long revision, String maze,
                              String lease, String place, String lot) {
        this(result, acl, revision, maze, lease, place, lot, "");
    }

    public ParcelGrantResponse(String result, String acl, long revision, String maze,
                              String lease, String place) {
        this(result, acl, revision, maze, lease, place, "", "");
    }

    public ParcelGrantResponse(String result, String acl, long revision, String maze,
                              String lease) {
        this(result, acl, revision, maze, lease, "", "", "");
    }

    public ParcelGrantResponse(String result, String acl, long revision, String maze) {
        this(result, acl, revision, maze, "", "", "", "");
    }

    public ParcelGrantResponse(String result, String acl, long revision) {
        this(result, acl, revision, "", "", "", "", "");
    }
}
