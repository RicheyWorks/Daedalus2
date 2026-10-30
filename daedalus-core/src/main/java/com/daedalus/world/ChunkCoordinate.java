// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Chunk address — {@code floorDiv} of a block coordinate by {@link Chunk#SIZE}.
 */
public record ChunkCoordinate(int x, int y, int z) {

    public static ChunkCoordinate of(BlockCoordinate block) {
        return block.chunk();
    }

    @Override
    public String toString() {
        return "(" + x + "," + y + "," + z + ")";
    }
}
