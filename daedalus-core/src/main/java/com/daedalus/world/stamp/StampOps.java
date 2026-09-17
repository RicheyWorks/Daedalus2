// SPDX-License-Identifier: MIT

package com.daedalus.world.stamp;

import com.daedalus.model.TileType;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Parcel;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.World;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * Core maze→voxel projection. Not a plugin. Walkable tiles become a floor cube;
 * walls become posts from {@code floorY} through {@code floorY + wallHeight}.
 */
public final class StampOps {

    private StampOps() {
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
        ParcelBounds bounds = new ParcelBounds(
                origin.x(),
                floorY,
                origin.z(),
                origin.x() + cols - 1,
                floorY + wallHeight,
                origin.z() + rows - 1);
        List<BlockCoordinate> positions = new ArrayList<>();
        List<BlockType> types = new ArrayList<>();
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                int x = origin.x() + c;
                int z = origin.z() + r;
                if (tiles[r][c] == TileType.WALL) {
                    for (int y = floorY; y <= floorY + wallHeight; y++) {
                        positions.add(new BlockCoordinate(x, y, z));
                        types.add(BlockType.STONE);
                    }
                } else {
                    positions.add(new BlockCoordinate(x, floorY, z));
                    types.add(BlockType.STONE);
                }
            }
        }
        return world.applyStamp(bounds, Parcel.SYSTEM_OWNER, positions, types);
    }
}
