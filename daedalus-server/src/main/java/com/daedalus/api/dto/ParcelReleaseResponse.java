// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of releasing the first leased parcel. {@code result} is never silent success. */
public record ParcelReleaseResponse(String result, String leaseId, long revision, String maze) {

    public ParcelReleaseResponse {
        result = result == null ? "" : result;
        leaseId = leaseId == null ? "" : leaseId;
        maze = maze == null ? "" : maze;
    }

    public ParcelReleaseResponse(String result, String leaseId, long revision) {
        this(result, leaseId, revision, "");
    }
}
