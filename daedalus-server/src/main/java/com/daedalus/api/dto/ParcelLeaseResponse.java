// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of leasing the first parcel. {@code result} is never silent success. */
public record ParcelLeaseResponse(String result, String leaseId, long revision, String maze,
                                 String place, String lot) {

    public ParcelLeaseResponse {
        maze = maze == null ? "" : maze;
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
    }

    public ParcelLeaseResponse(String result, String leaseId, long revision, String maze,
                              String place) {
        this(result, leaseId, revision, maze, place, "");
    }

    public ParcelLeaseResponse(String result, String leaseId, long revision, String maze) {
        this(result, leaseId, revision, maze, "", "");
    }

    public ParcelLeaseResponse(String result, String leaseId, long revision) {
        this(result, leaseId, revision, "", "", "");
    }
}
