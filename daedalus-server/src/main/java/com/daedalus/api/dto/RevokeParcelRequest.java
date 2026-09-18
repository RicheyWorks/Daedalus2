// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * Drop an extra grant on the slab under x,y,z, or the first plot when
 * that cell is off a parcel. {@code actorId} is an account key — not a
 * wallet.
 */
public record RevokeParcelRequest(
        @NotBlank(message = "actorId is required") String actorId,
        Integer x,
        Integer y,
        Integer z,
        String verb) {

    public RevokeParcelRequest(String actorId, Integer x, Integer y, Integer z) {
        this(actorId, x, y, z, null);
    }
}
