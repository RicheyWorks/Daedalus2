// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.Size;

/**
 * Claim, abandon, or set a builder on an island (ADR-026). In prod the caller is the signed-in
 * user and {@code actorId} is ignored; on an open dev server {@code actorId} names the caller.
 * {@code builder} and {@code allow} are only read by the builders route.
 */
public record IslandClaimRequest(
        @Size(max = 64, message = "actorId is at most 64 characters") String actorId,
        @Size(max = 64, message = "builder is at most 64 characters") String builder,
        Boolean allow) {
}
