// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of open or close. {@code result} is never silent success. */
public record DoorMutationResponse(String id, String state, String result, long revision,
                                   String maze, String lease, String place) {

    public DoorMutationResponse {
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
        place = place == null ? "" : place;
    }

    public DoorMutationResponse(String id, String state, String result, long revision,
                                String maze, String lease) {
        this(id, state, result, revision, maze, lease, "");
    }

    public DoorMutationResponse(String id, String state, String result, long revision,
                                String maze) {
        this(id, state, result, revision, maze, "", "");
    }

    public DoorMutationResponse(String id, String state, String result, long revision) {
        this(id, state, result, revision, "", "", "");
    }
}
