// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** NPC inspect — same facts automation reads. */
public record NpcInspectResponse(
        String id, String worldId, int x, int y, int z, String state) {
}
