// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * Hang a frame (ADR-035). {@code x, y, z} is the wall cube at its lowest corner, and {@code facing} is the
 * side of the wall it hangs on. The frame is {@code w} wide and {@code h} high, 1 to 6 cubes each.
 * {@code seed} (0 to 999,999,999) picks the maze art it shows. Signed in, the server knows who you are; on an open server,
 * {@code actorId} names you.
 */
public record HangArtRequest(
        @NotNull Integer x, @NotNull Integer y, @NotNull Integer z,
        @NotNull @Pattern(regexp = "NORTH|SOUTH|EAST|WEST", message = "facing is NORTH, SOUTH, EAST or WEST") String facing,
        @NotNull @Min(1) @Max(6) Integer w,
        @NotNull @Min(1) @Max(6) Integer h,
        @NotNull @Min(0) @Max(999_999_999) Long seed,
        @Size(max = 60, message = "title is at most 60 characters") String title,
        @Size(max = 64, message = "actorId is at most 64 characters") String actorId) {
}
