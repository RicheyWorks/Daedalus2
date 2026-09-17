// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** One parcel on inspect. {@code placeName}, {@code leaseId}, and {@code mazeRef} may be empty. */
public record WorldParcelRow(String id, String ownerId, String placeName, String leaseId,
                             String mazeRef, long version) {
}
