// SPDX-License-Identifier: MIT
package com.daedalus.world.ocean;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Chunk;
import com.daedalus.world.ChunkCoordinate;
import com.daedalus.world.World;
import com.daedalus.world.WorldId;
import com.daedalus.world.WorldRevision;
import com.daedalus.world.WorldSnapshot;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.Objects;

/**
 * Version-one seeded Ocean terrain, in Daedalus metres (+Y up).
 * Each requested 16-cube chunk costs bounded work; no whole-realm allocation.
 * Persist the seed/version with the host's realm metadata. Never regenerate over
 * a saved chunk or a mined-to-empty chunk: modified-area tracking belongs to the host.
 */
public final class OceanTerrain {
    public static final int VERSION = 1;
    public static final int SEA_LEVEL = 0;
    public static final int MAX_BATCH_CHUNKS = 64;
    private static final int CELL = 64;

    private OceanTerrain() { }

    /** Floating pier; walking arrival is on its deck, vessels berth beside it. */
    public static BlockCoordinate spawn() { return new BlockCoordinate(0, 2, 0); }
    public static BlockCoordinate boatBerth() { return new BlockCoordinate(0, 1, 8); }
    public static BlockCoordinate submarineBerth() { return new BlockCoordinate(0, -8, 8); }

    /** Smooth, continuous sea floor: depth 24..55 m, including negative coordinates. */
    public static int floorY(long seed, int x, int z) {
        long gx = Math.floorDiv(x, CELL), gz = Math.floorDiv(z, CELL);
        int fx = Math.floorMod(x, CELL), fz = Math.floorMod(z, CELL);
        long a = depth(seed, gx, gz) * (CELL - fx) + depth(seed, gx + 1, gz) * fx;
        long b = depth(seed, gx, gz + 1) * (CELL - fx) + depth(seed, gx + 1, gz + 1) * fx;
        return -(int) ((a * (CELL - fz) + b * fz) / (CELL * CELL));
    }

    public static BlockType block(long seed, int x, int y, int z) {
        // The dock is a floating structure, not a land island; boat lanes stay clear.
        if (y == 1 && x >= -6 && x <= 6 && z >= -3 && z <= 3) return BlockType.WOOD;
        if (y > SEA_LEVEL) return BlockType.AIR;
        int floor = floorY(seed, x, z);
        if (y <= floor - 3) return BlockType.STONE;
        if (y <= floor) return BlockType.SAND;
        return BlockType.WATER;
    }

    /** The chunk address must fit entirely inside signed block coordinates. */
    public static Chunk chunk(long seed, ChunkCoordinate at) {
        Objects.requireNonNull(at, "chunk address");
        int x0 = origin(at.x()), y0 = origin(at.y()), z0 = origin(at.z());
        Chunk result = new Chunk();
        for (int z = 0; z < Chunk.SIZE; z++) {
            for (int x = 0; x < Chunk.SIZE; x++) {
                for (int y = 0; y < Chunk.SIZE; y++) {
                    BlockType type = block(seed, x0 + x, y0 + y, z0 + z);
                    if (type != BlockType.AIR) result.set(x, y, z, type);
                }
            }
        }
        return result.compacted();
    }

    /**
     * A new standalone world image for bootstrap/export. This never mutates an
     * existing world. Caller chooses nearby chunk addresses; duplicates and
     * oversized batches refuse before generation. Empty chunks are omitted.
     */
    public static World newWorld(WorldId id, long seed, Collection<ChunkCoordinate> requested) {
        Objects.requireNonNull(id, "world id");
        Objects.requireNonNull(requested, "requested chunks");
        if (requested.size() > MAX_BATCH_CHUNKS) throw new IllegalArgumentException("Ocean batch exceeds 64 chunks");
        var addresses = new java.util.LinkedHashSet<ChunkCoordinate>();
        for (ChunkCoordinate at : requested) {
            Objects.requireNonNull(at, "chunk address");
            origin(at.x()); origin(at.y()); origin(at.z());
            if (!addresses.add(at)) throw new IllegalArgumentException("Duplicate Ocean chunk");
        }
        var chunks = new LinkedHashMap<ChunkCoordinate, Chunk>();
        for (ChunkCoordinate at : addresses) {
            Chunk generated = chunk(seed, at);
            if (!generated.isEmpty()) chunks.put(at, generated);
        }
        return World.from(new WorldSnapshot(id, new WorldRevision(0), chunks));
    }

    private static int origin(int axis) {
        long first = (long) axis * Chunk.SIZE;
        if (first < Integer.MIN_VALUE || first + Chunk.SIZE - 1 > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("Ocean chunk outside signed block coordinates");
        }
        return (int) first;
    }

    private static int depth(long seed, long x, long z) {
        long h = seed ^ x * 0x9E3779B97F4A7C15L ^ z * 0xD1B54A32D192ED03L;
        h = (h ^ (h >>> 30)) * 0xBF58476D1CE4E5B9L;
        h = (h ^ (h >>> 27)) * 0x94D049BB133111EBL;
        return 24 + (int) ((h ^ (h >>> 31)) & 31);
    }
}
