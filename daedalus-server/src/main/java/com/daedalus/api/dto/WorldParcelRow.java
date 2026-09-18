// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * One parcel on inspect. {@code placeName}, {@code leaseId},
 * {@code mazeRef}, {@code box}, and {@code acl} may be empty.
 */
public record WorldParcelRow(String id, String ownerId, String placeName, String leaseId,
                             String mazeRef, int minX, int minZ, long version, String box,
                             String acl) {

    public WorldParcelRow {
        box = box == null ? "" : box;
        acl = acl == null ? "" : acl;
    }

    public WorldParcelRow(String id, String ownerId, String placeName, String leaseId,
                          String mazeRef, int minX, int minZ, long version, String box) {
        this(id, ownerId, placeName, leaseId, mazeRef, minX, minZ, version, box, "");
    }

    public WorldParcelRow(String id, String ownerId, String placeName, String leaseId,
                          String mazeRef, int minX, int minZ, long version) {
        this(id, ownerId, placeName, leaseId, mazeRef, minX, minZ, version, "", "");
    }
}
