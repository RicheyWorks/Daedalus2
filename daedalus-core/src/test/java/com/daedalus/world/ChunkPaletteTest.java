// SPDX-License-Identifier: MIT

package com.daedalus.world;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Random;
import org.junit.jupiter.api.Test;

/** Paletted chunk storage (ADR-064 rule 1) behaves exactly like the old dense byte array. */
class ChunkPaletteTest {

    private static final BlockType[] TYPES = BlockType.values();

    @Test
    void anEmptyChunkHoldsNoPerCubeArray() {
        Chunk c = new Chunk();
        assertEquals(0, c.bitsPerBlock());
        assertTrue(c.storageBytes() < 128, "empty chunk costs " + c.storageBytes());
        assertTrue(c.isEmpty());
        assertEquals(BlockType.AIR, c.get(5, 5, 5));
    }

    @Test
    void writesWidenFromUniformToNibblesToBytes() {
        Chunk c = new Chunk();
        c.set(0, 0, 0, TYPES[1]);
        assertEquals(4, c.bitsPerBlock());
        for (int k = 2; k < 16; k++) {
            c.set(k, 0, 0, TYPES[k]);
        }
        assertEquals(4, c.bitsPerBlock(), "16 kinds (AIR + 15) still fit 4 bits");
        c.set(0, 1, 0, TYPES[16]);
        assertEquals(8, c.bitsPerBlock());
        for (int k = 1; k <= 16; k++) {
            assertEquals(TYPES[k], k < 16 ? c.get(k == 1 ? 0 : k, 0, 0) : c.get(0, 1, 0));
        }
    }

    @Test
    void randomEditsMatchADenseModelInEveryForm() {
        Random r = new Random(64);
        for (int round = 0; round < 40; round++) {
            int kinds = 1 + r.nextInt(round < 20 ? 6 : TYPES.length - 1);
            Chunk c = new Chunk();
            byte[] model = new byte[Chunk.VOLUME];
            int occupied = 0;
            for (int n = 0; n < 3000; n++) {
                int x = r.nextInt(16);
                int y = r.nextInt(16);
                int z = r.nextInt(16);
                BlockType t = TYPES[r.nextInt(kinds + 1)];
                int i = x + 16 * (y + 16 * z);
                BlockType prev = c.set(x, y, z, t);
                assertEquals(TYPES[model[i] & 0xff], prev);
                occupied += (model[i] == 0 ? 0 : -1) + (t == BlockType.AIR ? 0 : 1);
                model[i] = (byte) t.ordinal();
            }
            assertArrayEquals(model, c.ordinals(), "round " + round);
            assertEquals(occupied, c.occupied());
            assertEquals(occupied == 0, c.isEmpty());
            Chunk copy = c.copy();
            assertEquals(c, copy);
            assertEquals(c.hashCode(), copy.hashCode());
            assertTrue(copy.bitsPerBlock() <= c.bitsPerBlock(), "copy is never wider");
            Chunk loaded = Chunk.ofPayload(c.payload(), c.revision());
            assertEquals(c, loaded);
            assertEquals(occupied, loaded.occupied());
        }
    }

    @Test
    void copyNarrowsAChunkThatWasWidened() {
        Chunk c = new Chunk();
        for (int k = 1; k < TYPES.length && k < 30; k++) {
            c.set(k % 16, k / 16, 0, TYPES[k]);
        }
        assertEquals(8, c.bitsPerBlock());
        for (int k = 1; k < TYPES.length && k < 30; k++) {
            c.set(k % 16, k / 16, 0, TYPES[1]);
        }
        assertEquals(8, c.bitsPerBlock(), "writes never narrow");
        assertEquals(4, c.copy().bitsPerBlock());
        Chunk solid = new Chunk();
        for (int i = 0; i < Chunk.VOLUME; i++) {
            solid.set(i % 16, (i / 16) % 16, i / 256, TYPES[1]);
        }
        Chunk packed = solid.copy();
        assertEquals(0, packed.bitsPerBlock(), "a solid chunk copies to one value");
        assertEquals(Chunk.VOLUME, packed.occupied());
        assertEquals(TYPES[1], packed.get(15, 15, 15));
    }

    @Test
    void terrainLikeChunksTakeAboutHalf() {
        Chunk c = new Chunk();
        for (int x = 0; x < 16; x++) {
            for (int z = 0; z < 16; z++) {
                int h = 6 + ((x * 7 + z * 3) % 5);
                for (int y = 0; y < h; y++) {
                    c.set(x, y, z, y == h - 1 ? TYPES[2] : y > h - 4 ? TYPES[3] : TYPES[1]);
                }
            }
        }
        long dense = 24 + 16 + Chunk.VOLUME;
        assertEquals(4, c.bitsPerBlock());
        assertTrue(c.storageBytes() * 100 <= dense * 53, c.storageBytes() + " vs " + dense);
    }

    @Test
    void sameKindWriteStillAdvancesTheRevision() {
        Chunk c = new Chunk();
        c.set(1, 1, 1, BlockType.AIR);
        assertEquals(1, c.revision());
        assertEquals(0, c.bitsPerBlock());
    }
}
