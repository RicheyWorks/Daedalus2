// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import java.util.List;

/**
 * The seam for Prometheus's rd-studio (genre re-arrangement + studio-quality render). rd-studio is an
 * offline Python renderer today with no HTTP API, so the realm ships {@link #STUB}: it always answers
 * "not available" and the jukebox plays the original. See docs/rd-jukebox.md for the contract a real
 * service must meet.
 */
public interface StudioArranger {

    List<String> GENRES = List.of("original", "rock", "jazz", "reggae", "orchestral");

    /** What to play for {@code source} ("seed:&lt;name&gt;" or "token:&lt;id&gt;") in {@code genre}. */
    Arrangement arrange(String source, String genre, boolean studio);

    /** {@code url} is null when unavailable: the client keeps the original. */
    record Arrangement(String source, String genre, boolean studio, boolean available, String url, String note) {}

    StudioArranger STUB = (source, genre, studio) -> new Arrangement(source, genre, studio,
            "original".equals(genre) && !studio, null,
            "original".equals(genre) && !studio ? "the original song"
                    : "rd-studio arrangements are not connected yet: playing the original");
}
