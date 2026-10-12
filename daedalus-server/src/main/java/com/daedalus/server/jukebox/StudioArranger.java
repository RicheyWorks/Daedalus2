// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import java.util.List;

/**
 * The seam to Prometheus's rd-studio (genre re-arrangement + studio-quality render). {@link HttpStudioArranger}
 * talks to the live service; {@link #STUB} (no {@code studio-url}) always answers "not available" so the jukebox
 * plays the original.
 */
public interface StudioArranger {

    List<String> GENRES = List.of("original", "rock", "jazz", "reggae", "orchestral");

    /** What to play for {@code source} ("seed:&lt;name&gt;" or "token:&lt;id&gt;") in {@code genre}. */
    Arrangement arrange(String source, String genre, boolean studio);

    /** Engine seeds the studio can render (guest songs with genre support). */
    default List<String> seeds() { return List.of(); }

    /** {@code url} is null when unavailable: the client keeps the original. */
    record Arrangement(String source, String genre, boolean studio, boolean available, String url, String note) {}

    StudioArranger STUB = (source, genre, studio) -> new Arrangement(source, genre, studio, false, null,
            "original".equals(genre) && !studio ? "the original song"
                    : "rd-studio is not connected: playing the original");
}
