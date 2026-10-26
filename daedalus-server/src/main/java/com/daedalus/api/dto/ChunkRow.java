// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** One non-empty 16³ chunk: chunk coordinates, its local revision and how many cubes it holds. */
public record ChunkRow(int x, int y, int z, long revision, int occupied) {
}
