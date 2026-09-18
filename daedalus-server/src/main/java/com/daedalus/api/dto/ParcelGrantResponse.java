// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of an extra parcel grant. {@code result} is never silent success. */
public record ParcelGrantResponse(String result, String acl, long revision, String maze) {

    public ParcelGrantResponse {
        result = result == null ? "" : result;
        acl = acl == null ? "" : acl;
        maze = maze == null ? "" : maze;
    }

    public ParcelGrantResponse(String result, String acl, long revision) {
        this(result, acl, revision, "");
    }
}
