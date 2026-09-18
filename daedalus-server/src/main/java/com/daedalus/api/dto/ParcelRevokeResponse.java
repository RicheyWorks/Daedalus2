// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of dropping an extra parcel grant. {@code result} is never silent success. */
public record ParcelRevokeResponse(String result, String acl, long revision) {

    public ParcelRevokeResponse {
        result = result == null ? "" : result;
        acl = acl == null ? "" : acl;
    }
}
