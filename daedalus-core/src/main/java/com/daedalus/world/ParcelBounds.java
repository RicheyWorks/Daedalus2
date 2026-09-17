// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Inclusive block AABB. Overlap is any shared cube, not merely touching faces.
 */
public record ParcelBounds(int minX, int minY, int minZ, int maxX, int maxY, int maxZ) {

    public ParcelBounds {
        if (minX > maxX || minY > maxY || minZ > maxZ) {
            throw new IllegalArgumentException("ParcelBounds min cannot exceed max");
        }
    }

    public boolean overlaps(ParcelBounds other) {
        if (other == null) {
            throw new IllegalArgumentException("ParcelBounds is required");
        }
        return minX <= other.maxX && maxX >= other.minX
                && minY <= other.maxY && maxY >= other.minY
                && minZ <= other.maxZ && maxZ >= other.minZ;
    }
}
