// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.song;

/** A guest's verse: one melodic step (-5..+6 semitones, never 0) heard in their favourite record. */
public record Verse(String guestId, String fromRecord, int step) {
}
