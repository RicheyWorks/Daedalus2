// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Result of place or remove. {@code previous} is what was there; {@code type} is what is there now.
 * {@code maze} and {@code lease} are empty off a stamped or rented plot.
 */
public record BlockMutationResponse(
        int x, int y, int z, String previous, String type, long revision, String result,
        String maze, String lease) {

    public BlockMutationResponse {
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
    }

    public BlockMutationResponse(int x, int y, int z, String previous, String type, long revision,
                                 String result, String maze) {
        this(x, y, z, previous, type, revision, result, maze, "");
    }

    public BlockMutationResponse(int x, int y, int z, String previous, String type, long revision,
                                 String result) {
        this(x, y, z, previous, type, revision, result, "", "");
    }

    public BlockMutationResponse(int x, int y, int z, String previous, String type, long revision) {
        this(x, y, z, previous, type, revision, "PLACED", "", "");
    }
}
