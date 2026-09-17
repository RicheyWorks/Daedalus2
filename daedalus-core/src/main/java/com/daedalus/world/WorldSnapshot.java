// SPDX-License-Identifier: MIT

package com.daedalus.world;

import java.util.Map;
import java.util.Objects;

/**
 * Immutable world image. {@link WorldStore} writes this; a process restart
 * rebuilds a {@link World} from it. Not a maze cache entry.
 */
public record WorldSnapshot(
        WorldId id,
        WorldRevision revision,
        Map<ChunkCoordinate, Chunk> chunks,
        Door door) {

    public WorldSnapshot {
        Objects.requireNonNull(id, "WorldId is required");
        Objects.requireNonNull(revision, "WorldRevision is required");
        Objects.requireNonNull(chunks, "chunks are required");
        chunks = Map.copyOf(chunks);
    }

    public WorldSnapshot(WorldId id, WorldRevision revision, Map<ChunkCoordinate, Chunk> chunks) {
        this(id, revision, chunks, null);
    }
}
