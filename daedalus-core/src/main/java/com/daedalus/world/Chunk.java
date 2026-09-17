// SPDX-License-Identifier: MIT

package com.daedalus.world;

import java.util.Arrays;

/**
 * One {@code 16×16×16} payload. Worlds omit empty chunks; a missing chunk is AIR.
 */
public final class Chunk {

    public static final int SIZE = 16;
    public static final int VOLUME = SIZE * SIZE * SIZE;

    private final byte[] blocks;
    private long revision;

    public Chunk() {
        this.blocks = new byte[VOLUME];
    }

    private Chunk(byte[] blocks, long revision) {
        this.blocks = blocks;
        this.revision = revision;
    }

    public BlockType get(int localX, int localY, int localZ) {
        return BlockType.values()[Byte.toUnsignedInt(blocks[index(localX, localY, localZ)])];
    }

    public BlockType set(int localX, int localY, int localZ, BlockType type) {
        if (type == null) {
            throw new IllegalArgumentException("BlockType is required");
        }
        int i = index(localX, localY, localZ);
        BlockType previous = BlockType.values()[Byte.toUnsignedInt(blocks[i])];
        blocks[i] = (byte) type.ordinal();
        revision++;
        return previous;
    }

    public boolean isEmpty() {
        return occupied() == 0;
    }

    public int occupied() {
        int n = 0;
        for (byte b : blocks) {
            if (b != 0) {
                n++;
            }
        }
        return n;
    }

    public long revision() {
        return revision;
    }

    public Chunk copy() {
        return new Chunk(blocks.clone(), revision);
    }

    /**
     * Dense ordinal payload for a later snapshot. Callers must not mutate the array.
     */
    byte[] payload() {
        return blocks.clone();
    }

    static Chunk ofPayload(byte[] payload, long revision) {
        if (payload == null || payload.length != VOLUME) {
            throw new IllegalArgumentException("Chunk payload must be " + VOLUME + " bytes");
        }
        int kinds = BlockType.values().length;
        for (byte b : payload) {
            int ordinal = Byte.toUnsignedInt(b);
            if (ordinal >= kinds) {
                throw new IllegalArgumentException("Unknown block ordinal " + ordinal);
            }
        }
        return new Chunk(payload.clone(), revision);
    }

    private static int index(int localX, int localY, int localZ) {
        if (localX < 0 || localX >= SIZE || localY < 0 || localY >= SIZE
                || localZ < 0 || localZ >= SIZE) {
            throw new IllegalArgumentException(
                    "Local coordinate out of chunk: (" + localX + "," + localY + "," + localZ + ")");
        }
        return localX + SIZE * (localY + SIZE * localZ);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof Chunk other)) {
            return false;
        }
        return revision == other.revision && Arrays.equals(blocks, other.blocks);
    }

    @Override
    public int hashCode() {
        return 31 * Arrays.hashCode(blocks) + Long.hashCode(revision);
    }
}
