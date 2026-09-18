// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of talk or hush. {@code result} is never silent success. */
public record NpcMutationResponse(String id, String state, String result, long revision,
                                  String maze, String lease, String place, String lot,
                                  String box) {

    public NpcMutationResponse {
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        box = box == null ? "" : box;
    }

    public NpcMutationResponse(String id, String state, String result, long revision,
                               String maze, String lease, String place, String lot) {
        this(id, state, result, revision, maze, lease, place, lot, "");
    }

    public NpcMutationResponse(String id, String state, String result, long revision,
                               String maze, String lease, String place) {
        this(id, state, result, revision, maze, lease, place, "", "");
    }

    public NpcMutationResponse(String id, String state, String result, long revision,
                               String maze, String lease) {
        this(id, state, result, revision, maze, lease, "", "", "");
    }

    public NpcMutationResponse(String id, String state, String result, long revision,
                               String maze) {
        this(id, state, result, revision, maze, "", "", "", "");
    }

    public NpcMutationResponse(String id, String state, String result, long revision) {
        this(id, state, result, revision, "", "", "", "", "");
    }
}
