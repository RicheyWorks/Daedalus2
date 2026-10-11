// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/**
 * Place a cube. Coordinates may be negative. {@code type} is a {@code BlockType} name;
 * {@code AIR} is remove.
 */
public record PlaceBlockRequest(
        @NotNull(message = "x is required") Integer x,
        @NotNull(message = "y is required") Integer y,
        @NotNull(message = "z is required") Integer z,
        @NotBlank(message = "type is required")
        @Size(max = 16, message = "type must be at most 16 chars")
        String type,
        String actorId) {

    public PlaceBlockRequest(Integer x, Integer y, Integer z, String type) {
        this(x, y, z, type, null);
    }
}
