// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Result of place or remove. {@code previous} is what was there; {@code type} is what is there now.
 * {@code maze} is empty off a stamped plot.
 */
public record BlockMutationResponse(
        int x, int y, int z, String previous, String type, long revision, String result,
        String maze) {

    public BlockMutationResponse {
        maze = maze == null ? "" : maze;
    }

    public BlockMutationResponse(int x, int y, int z, String previous, String type, long revision,
                                 String result) {
        this(x, y, z, previous, type, revision, result, "");
    }

    public BlockMutationResponse(int x, int y, int z, String previous, String type, long revision) {
        this(x, y, z, previous, type, revision, "PLACED", "");
    }
}
