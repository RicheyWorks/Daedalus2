// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Read-back after a drive. Inspect: does not bump revision.
 */
public record WorldObserveResponse(String worldId, long revision, int x, int y, int z,
                                   String blockType, String doorState) {
}
