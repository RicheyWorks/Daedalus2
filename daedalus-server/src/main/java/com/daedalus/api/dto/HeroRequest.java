// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * A hero's report (ADR-037). {@code foe} is the foe beaten (BLIGHT_SLIME, SHARDBACK, DUST_WISP or
 * STONE_KNIGHT), and {@code stat} the level to raise (ATTACK, MAGIC or LIFE). Signed in, the server knows who
 * you are; on an open server, {@code actorId} names you.
 */
public record HeroRequest(
        @Pattern(regexp = "BLIGHT_SLIME|SHARDBACK|DUST_WISP|STONE_KNIGHT", message = "unknown foe") String foe,
        @Pattern(regexp = "ATTACK|MAGIC|LIFE", message = "stat is ATTACK, MAGIC or LIFE") String stat,
        @Size(max = 64, message = "actorId is at most 64 characters") String actorId) {
}
