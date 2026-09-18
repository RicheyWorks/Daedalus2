// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of open or seal. {@code result} is never silent success. */
public record PortalMutationResponse(String id, String state, String result, long revision,
                                     String maze) {

    public PortalMutationResponse {
        maze = maze == null ? "" : maze;
    }

    public PortalMutationResponse(String id, String state, String result, long revision) {
        this(id, state, result, revision, "");
    }
}
