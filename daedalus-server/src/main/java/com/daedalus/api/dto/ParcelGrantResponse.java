// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of an extra parcel grant. {@code result} is never silent success. */
public record ParcelGrantResponse(String result, String acl, long revision) {

    public ParcelGrantResponse {
        result = result == null ? "" : result;
        acl = acl == null ? "" : acl;
    }
}
