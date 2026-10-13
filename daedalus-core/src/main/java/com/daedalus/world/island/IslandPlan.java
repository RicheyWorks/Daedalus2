// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;

import java.nio.ByteBuffer;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.AbstractMap;
import java.util.AbstractSet;
import java.util.Arrays;
import java.util.Collections;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.Map;
import java.util.NoSuchElementException;
import java.util.Set;
import java.util.TreeMap;

/**
 * A generated island before it touches a world: cubes relative to the island origin, plus its
 * {@link IslandTraits}. Immutable. Iterates in {@link IslandGenerator#ORDER}.
 */
public final class IslandPlan {

    /** Each axis is packed into 21 bits with this offset, so a plan may span +/- 1,048,575 cubes per axis. */
    private static final int BIAS = 1 << 20;
    private static final long MASK = (1L << 21) - 1;
    private static final BlockType[] TYPES = BlockType.values();

    private final IslandTraits traits;
    /**
     * The cubes, packed like Minecraft's chunk sections rather than as a map of objects (ADR-062): one long per
     * cube, in ORDER (y, then z, then x, which is the packed numeric order), and one byte for its type. That is
     * 9 bytes per cube instead of about 64 for a TreeMap entry plus its BlockCoordinate (measured: a radius-46
     * land of 225,885 cubes went from 14.5 MB to about 2 MB).
     */
    private final long[] keys;
    private final byte[] types;
    private final Map<BlockCoordinate, BlockType> view;

    IslandPlan(IslandTraits traits, TreeMap<BlockCoordinate, BlockType> blocks) {
        this.traits = traits;
        this.keys = new long[blocks.size()];
        this.types = new byte[blocks.size()];
        int i = 0;
        for (Map.Entry<BlockCoordinate, BlockType> e : blocks.entrySet()) {   // a TreeMap in ORDER: already sorted
            keys[i] = pack(e.getKey());
            types[i] = (byte) e.getValue().ordinal();
            i++;
        }
        for (int k = 1; k < keys.length; k++) {
            if (keys[k - 1] >= keys[k]) {
                throw new IllegalArgumentException("Island cubes must be unique and in ORDER (y, z, x)");
            }
        }
        this.view = new View();
    }

    static long pack(BlockCoordinate c) {
        if (Math.abs((long) c.x()) >= BIAS || Math.abs((long) c.y()) >= BIAS || Math.abs((long) c.z()) >= BIAS) {
            throw new IllegalArgumentException("Island cube out of range: " + c);
        }
        return ((long) (c.y() + BIAS) << 42) | ((long) (c.z() + BIAS) << 21) | (c.x() + BIAS);
    }

    static BlockCoordinate unpack(long k) {
        int x = (int) (k & MASK) - BIAS;
        int z = (int) ((k >>> 21) & MASK) - BIAS;
        int y = (int) ((k >>> 42) & MASK) - BIAS;
        return new BlockCoordinate(x, y, z);
    }

    public IslandTraits traits() {
        return traits;
    }

    /** Cubes relative to the island origin, never AIR, iterated in ORDER. A read-only view over the packed arrays. */
    public Map<BlockCoordinate, BlockType> blocks() {
        return Collections.unmodifiableMap(view);   // already read-only; the wrapper says so to every reader
    }

    /** How many cubes, without building the view's entries. */
    public int size() {
        return keys.length;
    }

    private final class View extends AbstractMap<BlockCoordinate, BlockType> {
        @Override
        public int size() {
            return keys.length;
        }

        @Override
        public boolean containsKey(Object o) {
            return get(o) != null;
        }

        @Override
        public BlockType get(Object o) {
            if (!(o instanceof BlockCoordinate c)) {
                return null;
            }
            if (Math.abs((long) c.x()) >= BIAS || Math.abs((long) c.y()) >= BIAS || Math.abs((long) c.z()) >= BIAS) {
                return null;
            }
            int at = Arrays.binarySearch(keys, pack(c));
            return at < 0 ? null : TYPES[Byte.toUnsignedInt(types[at])];
        }

        @Override
        public Set<Map.Entry<BlockCoordinate, BlockType>> entrySet() {
            return new AbstractSet<>() {
                @Override
                public int size() {
                    return keys.length;
                }

                @Override
                public Iterator<Map.Entry<BlockCoordinate, BlockType>> iterator() {
                    return new Iterator<>() {
                        private int i;

                        @Override
                        public boolean hasNext() {
                            return i < keys.length;
                        }

                        @Override
                        public Map.Entry<BlockCoordinate, BlockType> next() {
                            if (i >= keys.length) {
                                throw new NoSuchElementException();
                            }
                            Map.Entry<BlockCoordinate, BlockType> e = new AbstractMap.SimpleImmutableEntry<>(unpack(keys[i]),
                                    TYPES[Byte.toUnsignedInt(types[i])]);
                            i++;
                            return e;
                        }
                    };
                }
            };
        }
    }

    /**
     * SHA-256 over every cube in order, as {@code (x, y, z, ordinal)}. Two plans with the same
     * digest are the same island — the golden test pins one so a change to the generator that
     * moves a single cube is a visible decision, not drift.
     */
    public String digest() {
        try {
            MessageDigest sha = MessageDigest.getInstance("SHA-256");
            ByteBuffer row = ByteBuffer.allocate(13);
            for (int i = 0; i < keys.length; i++) {
                BlockCoordinate c = unpack(keys[i]);
                row.clear();
                row.putInt(c.x()).putInt(c.y()).putInt(c.z()).put(types[i]);
                sha.update(row.array());
            }
            return HexFormat.of().formatHex(sha.digest());
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 is required by every JVM", e);
        }
    }
}
