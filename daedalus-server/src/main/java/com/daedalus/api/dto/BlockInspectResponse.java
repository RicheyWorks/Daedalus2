// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * One cube. {@code present} is false when the cell is AIR (missing chunk or removed).
 */
public record BlockInspectResponse(int x, int y, int z, String type, boolean present) {
}
