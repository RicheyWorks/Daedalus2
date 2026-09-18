// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * Extra grant on the slab under x,y,z, or the first plot when that
 * cell is off a parcel. {@code actorId} is an account key — not a wallet.
 */
public record GrantParcelRequest(
        @NotBlank(message = "actorId is required") String actorId,
        Integer x,
        Integer y,
        Integer z) {
}
