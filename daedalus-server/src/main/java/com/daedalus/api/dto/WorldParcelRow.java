// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * One parcel on inspect. {@code placeName}, {@code leaseId},
 * {@code mazeRef}, and {@code box} may be empty.
 */
public record WorldParcelRow(String id, String ownerId, String placeName, String leaseId,
                             String mazeRef, int minX, int minZ, long version, String box) {

    public WorldParcelRow {
        box = box == null ? "" : box;
    }

    public WorldParcelRow(String id, String ownerId, String placeName, String leaseId,
                          String mazeRef, int minX, int minZ, long version) {
        this(id, ownerId, placeName, leaseId, mazeRef, minX, minZ, version, "");
    }
}
