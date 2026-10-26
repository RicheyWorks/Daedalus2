// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * Every non-empty chunk's cubes in one response, run-length encoded (ADR-064): a renderer loads a world with one
 * request instead of one per chunk, and a mostly-air or solid chunk costs a few bytes instead of 4,096.
 * {@code palette} is BlockType names in ordinal order, as for {@link ChunkBlocksResponse}.
 */
public record WorldBlocksResponse(String worldId, long revision, int chunkSize, List<String> palette,
                                  List<ChunkRunsRow> chunks) {

    public WorldBlocksResponse {
        palette = palette == null ? List.of() : List.copyOf(palette);
        chunks = chunks == null ? List.of() : List.copyOf(chunks);
    }
}
