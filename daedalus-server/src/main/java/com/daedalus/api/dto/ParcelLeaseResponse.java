// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of leasing the first parcel. {@code result} is never silent success. */
public record ParcelLeaseResponse(String result, String leaseId, long revision, String maze,
                                 String place) {

    public ParcelLeaseResponse {
        maze = maze == null ? "" : maze;
        place = place == null ? "" : place;
    }

    public ParcelLeaseResponse(String result, String leaseId, long revision, String maze) {
        this(result, leaseId, revision, maze, "");
    }

    public ParcelLeaseResponse(String result, String leaseId, long revision) {
        this(result, leaseId, revision, "", "");
    }
}
