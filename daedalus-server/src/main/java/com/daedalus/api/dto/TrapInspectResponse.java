// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Trap inspect — same facts automation reads. */
public record TrapInspectResponse(
        String id, String worldId, int x, int y, int z, String state) {
}
