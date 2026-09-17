// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Door inspect — same facts automation reads. */
public record DoorInspectResponse(
        String id, String worldId, int x, int y, int z, String state) {
}
