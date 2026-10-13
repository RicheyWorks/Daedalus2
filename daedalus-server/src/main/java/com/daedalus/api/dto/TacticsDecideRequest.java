// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/**
 * One squad's state from Unreal (ADR-060 transport): {@code roster} is DTR 1 text from
 * {@code UDaedalusTactics::TakeRoster}, {@code events} is DTE 1 text from {@code TakeEvents} (may be empty).
 * Sizes cap a 256-unit roster and a 512-event batch with room to spare.
 */
public record TacticsDecideRequest(@NotNull @Size(max = 65_536) String roster, @Size(max = 131_072) String events) {
}
