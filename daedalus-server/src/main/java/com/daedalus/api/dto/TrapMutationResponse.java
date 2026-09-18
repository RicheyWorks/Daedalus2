// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of arm or disarm. {@code result} is never silent success. */
public record TrapMutationResponse(String id, String state, String result, long revision,
                                   String maze) {

    public TrapMutationResponse {
        maze = maze == null ? "" : maze;
    }

    public TrapMutationResponse(String id, String state, String result, long revision) {
        this(id, state, result, revision, "");
    }
}
