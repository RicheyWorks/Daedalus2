// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Chunk inspect. A missing chunk is AIR everywhere — {@code present} is false.
 */
public record ChunkInspectResponse(
        int x, int y, int z, boolean present, Long revision, int occupied) {
}
