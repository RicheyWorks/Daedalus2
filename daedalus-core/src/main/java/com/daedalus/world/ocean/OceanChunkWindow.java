// SPDX-License-Identifier: MIT
package com.daedalus.world.ocean;

import com.daedalus.world.*;
import java.io.IOException;
import java.nio.file.Path;
import java.util.*;

/**
 * Bounded write-through Ocean cache. Owns its store's writer lock. Disk operations
 * are synchronous: hosts schedule warmup off the game thread, with their own tickets.
 * Only edits through this instance are permitted while it owns the directory.
 */
public final class OceanChunkWindow implements AutoCloseable {
    private final int capacity;
    private final OceanChunkStore store;
    private final LinkedHashMap<ChunkCoordinate, Chunk> resident = new LinkedHashMap<>(16, .75f, true);
    private boolean closed;

    public OceanChunkWindow(Path directory, long seed, int capacity) throws IOException {
        if (capacity < 1 || capacity > 4096) throw new IllegalArgumentException("Ocean capacity must be 1..4096");
        this.capacity = capacity;
        store = new OceanChunkStore(directory, seed);
    }

    public synchronized BlockType get(BlockCoordinate at) throws IOException {
        requireOpen();Objects.requireNonNull(at, "block address");
        return cached(at.chunk()).get(at.localX(), at.localY(), at.localZ());
    }

    /** Caller can mesh/mutate the returned snapshot without changing authoritative terrain. */
    public synchronized Chunk snapshot(ChunkCoordinate at) throws IOException {
        requireOpen();return cached(at).copy();
    }

    /** Disk publication succeeds before the new cache value is visible. */
    public synchronized BlockType set(BlockCoordinate at, BlockType type) throws IOException {
        requireOpen();Objects.requireNonNull(at, "block address");Objects.requireNonNull(type, "block type");
        Chunk original = cached(at.chunk());
        BlockType previous = original.get(at.localX(), at.localY(), at.localZ());
        if (previous == type) return previous;
        Chunk next = original.copy();
        next.set(at.localX(), at.localY(), at.localZ(), type);
        store.save(at.chunk(), next);
        resident.put(at.chunk(), next);
        return previous;
    }

    /**
     * Touch the nearest capacity-sized subset of a bounded chunk box. New loads
     * are capped at budget (0..64); cache hits do not consume that budget.
     * Ties sort by x/y/z. Returns newly loaded chunks, not generated-only chunks.
     */
    public synchronized int warmAround(BlockCoordinate centre, int horizontalRadius,
                                       int verticalRadius, int budget) throws IOException {
        requireOpen();Objects.requireNonNull(centre, "centre");
        if (horizontalRadius < 0 || horizontalRadius > 8 || verticalRadius < 0 || verticalRadius > 4
                || budget < 0 || budget > 64) throw new IllegalArgumentException("Ocean warmup bounds exceeded");
        ChunkCoordinate home = centre.chunk();
        List<ChunkCoordinate> candidates = new ArrayList<>();
        for (int x = -horizontalRadius; x <= horizontalRadius; x++) {
            for (int y = -verticalRadius; y <= verticalRadius; y++) {
                for (int z = -horizontalRadius; z <= horizontalRadius; z++) {
                    long cx = (long) home.x() + x, cy = (long) home.y() + y, cz = (long) home.z() + z;
                    if (validAxis(cx) && validAxis(cy) && validAxis(cz)) {
                        candidates.add(new ChunkCoordinate((int) cx, (int) cy, (int) cz));
                    }
                }
            }
        }
        candidates.sort(Comparator.<ChunkCoordinate>comparingLong(at -> distance(at, home))
                .thenComparingInt(ChunkCoordinate::x).thenComparingInt(ChunkCoordinate::y).thenComparingInt(ChunkCoordinate::z));
        int loaded = 0;
        for (int i = 0; i < Math.min(capacity, candidates.size()); i++) {
            ChunkCoordinate at = candidates.get(i);
            if (resident.containsKey(at)) resident.get(at);
            else if (loaded < budget) { cached(at);loaded++; }
        }
        return loaded;
    }

    public synchronized int residentCount() { return resident.size(); }

    /** Every cached edit is already saved, so eviction requires no dirty queue. */
    public synchronized void evictAll() throws IOException { requireOpen();resident.clear(); }

    private Chunk cached(ChunkCoordinate at) throws IOException {
        Objects.requireNonNull(at, "chunk address");
        Chunk value = resident.get(at);
        if (value != null) return value;
        Chunk loaded = store.loadOrGenerate(at); // Failed I/O leaves the cache unchanged.
        if (resident.size() == capacity) resident.remove(resident.keySet().iterator().next());
        resident.put(at, loaded);
        return loaded;
    }

    private static boolean validAxis(long axis) {
        return axis >= Integer.MIN_VALUE / Chunk.SIZE && axis <= Integer.MAX_VALUE / Chunk.SIZE;
    }

    private static long distance(ChunkCoordinate a, ChunkCoordinate b) {
        long x = (long) a.x() - b.x(), y = (long) a.y() - b.y(), z = (long) a.z() - b.z();
        return x*x + y*y + z*z;
    }

    private void requireOpen() throws IOException { if (closed) throw new IOException("Ocean window is closed"); }

    @Override public synchronized void close() throws IOException {
        if (closed) return;
        closed = true;resident.clear();store.close();
    }
}
