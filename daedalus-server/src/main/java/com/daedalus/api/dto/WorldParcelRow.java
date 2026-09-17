// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** One parcel on inspect. {@code placeName} may be empty. */
public record WorldParcelRow(String id, String ownerId, String placeName, long version) {
}
