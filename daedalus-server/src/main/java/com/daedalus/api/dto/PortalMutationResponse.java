// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of open or seal. {@code result} is never silent success. */
public record PortalMutationResponse(String id, String state, String result, long revision,
                                     String maze, String lease) {

    public PortalMutationResponse {
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
    }

    public PortalMutationResponse(String id, String state, String result, long revision,
                                  String maze) {
        this(id, state, result, revision, maze, "");
    }

    public PortalMutationResponse(String id, String state, String result, long revision) {
        this(id, state, result, revision, "", "");
    }
}
