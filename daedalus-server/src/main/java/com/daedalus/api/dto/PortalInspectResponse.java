// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Portal inspect — same facts automation reads. */
public record PortalInspectResponse(
        String id, String worldId, int x, int y, int z, String state) {
}
