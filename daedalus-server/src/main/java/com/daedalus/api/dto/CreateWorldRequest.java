// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

/**
 * Mount a new world (ADR-030). {@code id} is 3-32 lowercase letters, digits and dashes; {@code style}
 * is a world style (only ready ones are accepted); {@code seed} grows its terrain.
 */
public record CreateWorldRequest(
        @NotBlank(message = "id is required") String id,
        @NotBlank(message = "style is required") String style,
        @NotNull(message = "seed is required") Long seed,
        @NotBlank(message = "title is required") String title) {
}
