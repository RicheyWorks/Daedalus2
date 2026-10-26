// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * World-space cube. Y is up, matching explore. Negative axes use
 * {@link Math#floorDiv(int, int)} / {@link Math#floorMod(int, int)} so
 * {@code (-1,0,0)} lives in chunk {@code (-1,0,0)} at local {@code (15,0,0)}.
 */
public record BlockCoordinate(int x, int y, int z) {

    public ChunkCoordinate chunk() {
        int size = Chunk.SIZE;
        return new ChunkCoordinate(
                Math.floorDiv(x, size),
                Math.floorDiv(y, size),
                Math.floorDiv(z, size));
    }

    public int localX() {
        return Math.floorMod(x, Chunk.SIZE);
    }

    public int localY() {
        return Math.floorMod(y, Chunk.SIZE);
    }

    public int localZ() {
        return Math.floorMod(z, Chunk.SIZE);
    }

    @Override
    public String toString() {
        return "(" + x + "," + y + "," + z + ")";
    }
}
