// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of open or close. {@code result} is never silent success. */
public record DoorMutationResponse(String id, String state, String result, long revision,
                                   String maze, String lease, String place, String lot,
                                   String box) {

    public DoorMutationResponse {
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        box = box == null ? "" : box;
    }

    public DoorMutationResponse(String id, String state, String result, long revision,
                                String maze, String lease, String place, String lot) {
        this(id, state, result, revision, maze, lease, place, lot, "");
    }

    public DoorMutationResponse(String id, String state, String result, long revision,
                                String maze, String lease, String place) {
        this(id, state, result, revision, maze, lease, place, "", "");
    }

    public DoorMutationResponse(String id, String state, String result, long revision,
                                String maze, String lease) {
        this(id, state, result, revision, maze, lease, "", "", "");
    }

    public DoorMutationResponse(String id, String state, String result, long revision,
                                String maze) {
        this(id, state, result, revision, maze, "", "", "", "");
    }

    public DoorMutationResponse(String id, String state, String result, long revision) {
        this(id, state, result, revision, "", "", "", "", "");
    }
}
