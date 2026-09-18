// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Result of place or remove. {@code previous} is what was there; {@code type} is what is there now.
 */
public record BlockMutationResponse(
        int x, int y, int z, String previous, String type, long revision, String result) {

    public BlockMutationResponse(int x, int y, int z, String previous, String type, long revision) {
        this(x, y, z, previous, type, revision, "PLACED");
    }
}
