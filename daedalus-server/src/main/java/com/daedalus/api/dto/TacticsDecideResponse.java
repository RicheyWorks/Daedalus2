// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * The answer: {@code result} is APPLY (a new DTO 1 spec for {@code UDaedalusTactics::ApplyOrders}), REPEAT (the
 * spec already decided for this tick, safe to apply again) or STALE (an older tick; {@code spec} is empty).
 */
public record TacticsDecideResponse(String result, String spec, String why, int squads) {
}
