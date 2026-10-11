// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;

import java.nio.ByteBuffer;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Collections;
import java.util.HexFormat;
import java.util.Map;
import java.util.SortedMap;
import java.util.TreeMap;

/**
 * A generated island before it touches a world: cubes relative to the island origin, plus its
 * {@link IslandTraits}. Immutable. Iterates in {@link IslandGenerator#ORDER}.
 */
public final class IslandPlan {

    private final IslandTraits traits;
    private final SortedMap<BlockCoordinate, BlockType> blocks;

    IslandPlan(IslandTraits traits, TreeMap<BlockCoordinate, BlockType> blocks) {
        this.traits = traits;
        this.blocks = Collections.unmodifiableSortedMap(new TreeMap<>(blocks));
    }

    public IslandTraits traits() {
        return traits;
    }

    /** Cubes relative to the island origin, never AIR. */
    public Map<BlockCoordinate, BlockType> blocks() {
        return blocks;
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
            for (Map.Entry<BlockCoordinate, BlockType> e : blocks.entrySet()) {
                row.clear();
                row.putInt(e.getKey().x()).putInt(e.getKey().y()).putInt(e.getKey().z())
                        .put((byte) e.getValue().ordinal());
                sha.update(row.array());
            }
            return HexFormat.of().formatHex(sha.digest());
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 is required by every JVM", e);
        }
    }
}
