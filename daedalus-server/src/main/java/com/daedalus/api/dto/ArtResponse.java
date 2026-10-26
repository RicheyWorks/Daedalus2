// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Outcome of hanging or taking down a frame (ADR-035). The result is one of HUNG, TAKEN_DOWN,
 * NOT_A_GALLERY, BAD_ACTOR, NOT_YOURS, NO_WALL, OVERLAP, FULL or NO_SUCH_ART. {@code art} is the frame
 * concerned, when there is one.
 */
public record ArtResponse(String result, ArtRow art) {
}
