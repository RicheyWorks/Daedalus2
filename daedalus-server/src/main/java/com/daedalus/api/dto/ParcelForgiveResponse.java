// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of dropping an extra parcel denial. {@code result} is never silent success. */
public record ParcelForgiveResponse(String result, String acl, long revision) {

    public ParcelForgiveResponse {
        result = result == null ? "" : result;
        acl = acl == null ? "" : acl;
    }
}
