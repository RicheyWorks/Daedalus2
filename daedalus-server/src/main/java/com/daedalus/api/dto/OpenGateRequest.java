// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.NotBlank;

/** Open a pair of sky gates between this world and {@code toWorld} (ADR-031). */
public record OpenGateRequest(@NotBlank(message = "toWorld is required") String toWorld) {
}
