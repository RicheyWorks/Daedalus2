// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of arm or disarm. {@code result} is never silent success. */
public record TrapMutationResponse(String id, String state, String result, long revision,
                                   String maze, String lease, String place, String lot) {

    public TrapMutationResponse {
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
    }

    public TrapMutationResponse(String id, String state, String result, long revision,
                                String maze, String lease, String place) {
        this(id, state, result, revision, maze, lease, place, "");
    }

    public TrapMutationResponse(String id, String state, String result, long revision,
                                String maze, String lease) {
        this(id, state, result, revision, maze, lease, "", "");
    }

    public TrapMutationResponse(String id, String state, String result, long revision,
                                String maze) {
        this(id, state, result, revision, maze, "", "", "");
    }

    public TrapMutationResponse(String id, String state, String result, long revision) {
        this(id, state, result, revision, "", "", "", "");
    }
}
