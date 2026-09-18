// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of an extra parcel deny. {@code result} is never silent success. */
public record ParcelDenyResponse(String result, String acl, long revision, String maze,
                                String lease) {

    public ParcelDenyResponse {
        result = result == null ? "" : result;
        acl = acl == null ? "" : acl;
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
    }

    public ParcelDenyResponse(String result, String acl, long revision, String maze) {
        this(result, acl, revision, maze, "");
    }

    public ParcelDenyResponse(String result, String acl, long revision) {
        this(result, acl, revision, "", "");
    }
}
