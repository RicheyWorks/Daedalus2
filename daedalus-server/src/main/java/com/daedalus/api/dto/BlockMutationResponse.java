// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Result of place or remove. {@code previous} is what was there; {@code type} is what is there now.
 * Street fields are empty off a stamped plot.
 */
public record BlockMutationResponse(
        int x, int y, int z, String previous, String type, long revision, String result,
        String maze, String lease, String place, String lot, String box) {

    public BlockMutationResponse {
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        box = box == null ? "" : box;
    }

    public BlockMutationResponse(int x, int y, int z, String previous, String type, long revision,
                                 String result, String maze, String lease, String place,
                                 String lot) {
        this(x, y, z, previous, type, revision, result, maze, lease, place, lot, "");
    }

    public BlockMutationResponse(int x, int y, int z, String previous, String type, long revision,
                                 String result, String maze, String lease, String place) {
        this(x, y, z, previous, type, revision, result, maze, lease, place, "", "");
    }

    public BlockMutationResponse(int x, int y, int z, String previous, String type, long revision,
                                 String result, String maze, String lease) {
        this(x, y, z, previous, type, revision, result, maze, lease, "", "", "");
    }

    public BlockMutationResponse(int x, int y, int z, String previous, String type, long revision,
                                 String result, String maze) {
        this(x, y, z, previous, type, revision, result, maze, "", "", "", "");
    }

    public BlockMutationResponse(int x, int y, int z, String previous, String type, long revision,
                                 String result) {
        this(x, y, z, previous, type, revision, result, "", "", "", "", "");
    }

    public BlockMutationResponse(int x, int y, int z, String previous, String type, long revision) {
        this(x, y, z, previous, type, revision, "PLACED", "", "", "", "", "");
    }
}
