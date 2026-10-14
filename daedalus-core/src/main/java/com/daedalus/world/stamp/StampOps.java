// SPDX-License-Identifier: MIT

package com.daedalus.world.stamp;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.TileType;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Parcel;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.World;
import com.daedalus.world.auto.WorldOps;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * Core maze→voxel projection. Not a plugin. Walkable tiles become a floor cube;
 * walls become posts from {@code floorY} through {@code floorY + wallHeight}.
 */
public final class StampOps {

    /** One empty cube between plots — not a merge. */
    public static final int STREET = 1;
    /** Cap on +X walks when every probe overlaps. */
    public static final int NEXT_TRIES = 32;

    private StampOps() {
    }

    public static ParcelBounds boundsOf(BlockCoordinate origin, MazeGrid maze, int wallHeight) {
        return boundsOf(origin, maze, wallHeight, 1);
    }

    public static ParcelBounds boundsOf(BlockCoordinate origin, MazeGrid maze, int wallHeight, int tileScale) {
        Objects.requireNonNull(origin, "Stamp origin is required");
        Objects.requireNonNull(maze, "MazeGrid is required");
        if (wallHeight < 1) {
            throw new IllegalArgumentException("wallHeight must be at least 1");
        }
        if (tileScale < 1 || tileScale > 4) throw new IllegalArgumentException("tileScale must be 1..4");
        TileType[][] tiles = maze.toTileGrid();
        int rows = tiles.length;
        int cols = tiles[0].length;
        return new ParcelBounds(
                origin.x(),
                origin.y(),
                origin.z(),
                Math.addExact(origin.x(), Math.multiplyExact(cols, tileScale) - 1),
                Math.addExact(origin.y(), wallHeight),
                Math.addExact(origin.z(), Math.multiplyExact(rows, tileScale) - 1));
    }

    /**
     * First +X origin whose AABB misses every parcel. Explicit
     * {@link #apply} at a colliding address still refuses.
     */
    public static BlockCoordinate nextOrigin(World world, MazeGrid maze, BlockCoordinate prefer,
                                             int wallHeight) {
        Objects.requireNonNull(world, "World is required");
        MazeGrid slab = maze == null ? new MazeGrid(1, 1) : maze;
        BlockCoordinate at = prefer == null ? new BlockCoordinate(0, 0, 0) : prefer;
        for (int i = 0; i < NEXT_TRIES; i++) {
            ParcelBounds box = boundsOf(at, slab, wallHeight);
            boolean hits = false;
            for (Parcel parcel : world.parcels()) {
                if (parcel.bounds().overlaps(box)) {
                    hits = true;
                    break;
                }
            }
            if (!hits) {
                return at;
            }
            int width = box.maxX() - box.minX() + 1;
            at = new BlockCoordinate(at.x() + width + STREET, at.y(), at.z());
        }
        return at;
    }

    public static StampResult apply(World world, StampRequest request) {
        Objects.requireNonNull(world, "World is required");
        Objects.requireNonNull(request, "StampRequest is required");
        if (!world.id().equals(request.worldId())) {
            throw new IllegalArgumentException("Stamp worldId must match the live world");
        }
        TileType[][] tiles = request.maze().toTileGrid();
        int rows = tiles.length;
        int cols = tiles[0].length;
        BlockCoordinate origin = request.origin();
        int floorY = request.floorY();
        int wallHeight = request.wallHeight();
        int scale = request.tileScale();
        ParcelBounds bounds = boundsOf(origin, request.maze(), wallHeight, scale);
        List<BlockCoordinate> positions = new ArrayList<>();
        List<BlockType> types = new ArrayList<>();
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                for (int dz = 0; dz < scale; dz++) {
                    for (int dx = 0; dx < scale; dx++) {
                        int x = origin.x() + c * scale + dx;
                        int z = origin.z() + r * scale + dz;
                        if (tiles[r][c] == TileType.WALL) {
                            for (int y = floorY; y <= floorY + wallHeight; y++) {
                                remember(world, positions, types, x, y, z);
                            }
                        } else remember(world, positions, types, x, floorY, z);
                    }
                }
            }
        }
        return world.applyStamp(bounds, Parcel.SYSTEM_OWNER, positions, types);
    }

    /** Door / trap / portal / NPC cubes stay occupancy, not maze stone. */
    private static void remember(World world, List<BlockCoordinate> positions,
            List<BlockType> types, int x, int y, int z) {
        BlockCoordinate at = new BlockCoordinate(x, y, z);
        if (!WorldOps.occupantAt(world, at).isEmpty()) {
            return;
        }
        positions.add(at);
        types.add(BlockType.STONE);
    }
}
