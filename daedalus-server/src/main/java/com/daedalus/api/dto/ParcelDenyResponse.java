// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of an extra parcel deny. {@code result} is never silent success. */
public record ParcelDenyResponse(String result, String acl, long revision) {

    public ParcelDenyResponse {
        result = result == null ? "" : result;
        acl = acl == null ? "" : acl;
    }
}
