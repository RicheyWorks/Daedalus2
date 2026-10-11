// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Outcome of raising an island. {@code result} is {@code RAISED} or {@code LANE_FULL} — never a
 * silent success. On {@code LANE_FULL} {@code island} is null and nothing changed.
 */
public record IslandRaiseResponse(String result, long revision, IslandRow island) {
}
