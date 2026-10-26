// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * A chunk's cubes for meshing. {@code data} is base64 of {@code 16³ = 4096} bytes, one per cube,
 * at {@code index = x + 16 * (y + 16 * z)} in local coordinates; each byte indexes {@code palette}
 * (which is {@code BlockType} names in ordinal order, so byte 0 is always {@code AIR}).
 * {@code present=false} means the chunk is empty and {@code data} is empty.
 */
public record ChunkBlocksResponse(int x, int y, int z, boolean present, long revision,
                                  List<String> palette, String data) {

    /** Copy on construct: the caller's list cannot change what this record says. */
    public ChunkBlocksResponse {
        palette = palette == null ? List.of() : List.copyOf(palette);
    }
}
