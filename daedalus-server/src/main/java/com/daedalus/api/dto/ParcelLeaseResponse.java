// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of leasing the first parcel. {@code result} is never silent success. */
public record ParcelLeaseResponse(String result, String leaseId, long revision, String maze) {

    public ParcelLeaseResponse {
        maze = maze == null ? "" : maze;
    }

    public ParcelLeaseResponse(String result, String leaseId, long revision) {
        this(result, leaseId, revision, "");
    }
}
