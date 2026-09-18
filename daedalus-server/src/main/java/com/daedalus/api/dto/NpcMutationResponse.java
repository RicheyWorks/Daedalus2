// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of talk or hush. {@code result} is never silent success. */
public record NpcMutationResponse(String id, String state, String result, long revision,
                                  String maze, String lease) {

    public NpcMutationResponse {
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
    }

    public NpcMutationResponse(String id, String state, String result, long revision,
                               String maze) {
        this(id, state, result, revision, maze, "");
    }

    public NpcMutationResponse(String id, String state, String result, long revision) {
        this(id, state, result, revision, "", "");
    }
}
