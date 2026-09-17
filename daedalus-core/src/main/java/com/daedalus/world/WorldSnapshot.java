// SPDX-License-Identifier: MIT

package com.daedalus.world;

import java.util.List;
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
        Door door,
        Trap trap,
        Portal portal,
        Npc npc,
        List<Parcel> parcels) {

    public WorldSnapshot {
        Objects.requireNonNull(id, "WorldId is required");
        Objects.requireNonNull(revision, "WorldRevision is required");
        Objects.requireNonNull(chunks, "chunks are required");
        chunks = Map.copyOf(chunks);
        parcels = parcels == null ? List.of() : List.copyOf(parcels);
    }

    public WorldSnapshot(WorldId id, WorldRevision revision, Map<ChunkCoordinate, Chunk> chunks) {
        this(id, revision, chunks, null, null, null, null, List.of());
    }

    public WorldSnapshot(WorldId id, WorldRevision revision, Map<ChunkCoordinate, Chunk> chunks, Door door) {
        this(id, revision, chunks, door, null, null, null, List.of());
    }
}
