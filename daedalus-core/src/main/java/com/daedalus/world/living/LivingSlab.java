// SPDX-License-Identifier: MIT

package com.daedalus.world.living;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.TileType;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.World;
import com.daedalus.world.auto.WorldOps;
import com.daedalus.world.stamp.StampRequest;

import java.util.Objects;

/**
 * Maze-sourced write-through after a stamp. Living / braid / sealer keep running on
 * the {@link MazeGrid}; this subscriber re-projects dirty cubes only. Inspect is quiet.
 */
public final class LivingSlab {

    private final World world;
    private final MazeGrid maze;
    private final BlockCoordinate origin;
    private final int floorY;
    private final int wallHeight;
    private final ParcelBounds bounds;
    private BlockCoordinate lastWritten;
    private BlockType lastWrittenNow;
    private BlockType lastWrittenPrevious;

    public LivingSlab(World world, StampRequest request, ParcelBounds bounds) {
        this.world = Objects.requireNonNull(world, "World is required");
        Objects.requireNonNull(request, "StampRequest is required");
        this.maze = request.maze();
        this.origin = request.origin();
        this.floorY = request.floorY();
        this.wallHeight = request.wallHeight();
        this.bounds = Objects.requireNonNull(bounds, "ParcelBounds is required");
        if (!world.id().equals(request.worldId())) {
            throw new IllegalArgumentException("Living slab worldId must match the live world");
        }
    }

    public MazeGrid maze() {
        return maze;
    }

    public ParcelBounds bounds() {
        return bounds;
    }

    /** Last cube this sync wrote. Null when the maze was quiet. */
    public BlockCoordinate lastWritten() {
        return lastWritten;
    }

    /** Type after the last write. Null when the maze was quiet. */
    public BlockType lastWrittenNow() {
        return lastWrittenNow;
    }

    /** Type before the last write. Null when the maze was quiet. */
    public BlockType lastWrittenPrevious() {
        return lastWrittenPrevious;
    }

    /**
     * Read a cube. Does not write and does not bump revision.
     */
    public BlockType inspect(BlockCoordinate at) {
        return world.get(at);
    }

    /**
     * Re-project the current maze into the stamped AABB. Only cubes whose desired
     * type changed are placed or removed.
     *
     * @return number of cubes written
     */
    public int sync() {
        TileType[][] tiles = maze.toTileGrid();
        int rows = tiles.length;
        int cols = tiles[0].length;
        int written = 0;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                int x = origin.x() + c;
                int z = origin.z() + r;
                boolean wall = tiles[r][c] == TileType.WALL;
                for (int y = floorY; y <= floorY + wallHeight; y++) {
                    BlockType desired = (!wall && y > floorY) ? BlockType.AIR : BlockType.STONE;
                    written += ensure(new BlockCoordinate(x, y, z), desired);
                }
            }
        }
        written += clearOutsideGrid(rows, cols);
        written += clearOutsideHeight(rows, cols);
        return written;
    }

    /** Drop leftover stone that sits in the AABB but not on this maze. */
    private int clearOutsideGrid(int rows, int cols) {
        int written = 0;
        for (int x = bounds.minX(); x <= bounds.maxX(); x++) {
            for (int z = bounds.minZ(); z <= bounds.maxZ(); z++) {
                int c = x - origin.x();
                int r = z - origin.z();
                if (c >= 0 && c < cols && r >= 0 && r < rows) {
                    continue;
                }
                for (int y = bounds.minY(); y <= bounds.maxY(); y++) {
                    written += ensure(new BlockCoordinate(x, y, z), BlockType.AIR);
                }
            }
        }
        return written;
    }

    /** Drop leftover posts above or below this wallHeight. */
    private int clearOutsideHeight(int rows, int cols) {
        int written = 0;
        int top = floorY + wallHeight;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                int x = origin.x() + c;
                int z = origin.z() + r;
                for (int y = bounds.minY(); y <= bounds.maxY(); y++) {
                    if (y >= floorY && y <= top) {
                        continue;
                    }
                    written += ensure(new BlockCoordinate(x, y, z), BlockType.AIR);
                }
            }
        }
        return written;
    }

    private int ensure(BlockCoordinate at, BlockType desired) {
        if (!bounds.contains(at)) {
            return 0;
        }
        if (!WorldOps.occupantAt(world, at).isEmpty()) {
            return 0;
        }
        BlockType current = world.get(at);
        if (current == desired) {
            return 0;
        }
        if (desired == BlockType.AIR) {
            world.remove(at);
        } else {
            world.place(at, desired);
        }
        lastWritten = at;
        lastWrittenNow = desired;
        lastWrittenPrevious = current;
        return 1;
    }
}
