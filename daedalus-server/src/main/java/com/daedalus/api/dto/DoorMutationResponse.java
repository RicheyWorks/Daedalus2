// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of open or close. {@code result} is never silent success. */
public record DoorMutationResponse(String id, String state, String result, long revision,
                                   String maze) {

    public DoorMutationResponse {
        maze = maze == null ? "" : maze;
    }

    public DoorMutationResponse(String id, String state, String result, long revision) {
        this(id, state, result, revision, "");
    }
}
