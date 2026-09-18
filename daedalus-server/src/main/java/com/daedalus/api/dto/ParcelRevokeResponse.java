// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of dropping an extra parcel grant. {@code result} is never silent success. */
public record ParcelRevokeResponse(String result, String acl, long revision, String maze) {

    public ParcelRevokeResponse {
        result = result == null ? "" : result;
        acl = acl == null ? "" : acl;
        maze = maze == null ? "" : maze;
    }

    public ParcelRevokeResponse(String result, String acl, long revision) {
        this(result, acl, revision, "");
    }
}
