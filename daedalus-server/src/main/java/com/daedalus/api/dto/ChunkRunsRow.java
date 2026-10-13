// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * One chunk in a batch: {@code runs} is base64 of (ordinal, length low byte, length high byte) triples in index
 * order {@code x + 16 * (y + 16 * z)}, covering exactly 4,096 cubes.
 */
public record ChunkRunsRow(int x, int y, int z, long revision, int occupied, String runs) {
}
