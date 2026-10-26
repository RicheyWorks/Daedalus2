// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * Every non-empty chunk in a world, so a renderer can fetch exactly what exists. Ordered by
 * (y, z, x) of the chunk coordinate. {@code revision} is the world revision at the moment of the
 * listing; compare it to {@code WorldEventFrame.revision} to know whether a refetch is needed.
 */
public record WorldChunksResponse(String worldId, long revision, int chunkSize, List<ChunkRow> chunks) {

    /** Copy on construct: the caller's list cannot change what this record says. */
    public WorldChunksResponse {
        chunks = chunks == null ? List.of() : List.copyOf(chunks);
    }
}
