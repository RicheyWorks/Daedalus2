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

    /** The same, with rd-studio r4's render options (headphone preset, vinyl, surface noise, format). */
    default Arrangement arrange(String source, String genre, boolean studio, Render render) {
        return arrange(source, genre, studio);
    }

    /** Headphone presets rd-studio r4 renders with (CHANGES_FOR_FLEX.md). */
    List<String> PRESETS = List.of("neutral", "harman", "crossfeed", "warm", "bass");

    /**
     * rd-studio r4 render options: {@code format} mp3 | flac (24-bit/48 kHz), headphone {@code preset}, {@code vinyl}
     * 0–100 (snapped down to 10s, as the studio does), surface {@code noise} "off" (default) or -60..-30 dBFS.
     */
    record Render(String format, String preset, int vinyl, String noise) {
        public static final Render DEFAULT = new Render("mp3", "neutral", 0, "off");

        public Render {
            format = format == null || format.isBlank() ? "mp3" : format.toLowerCase();
            if (!format.equals("mp3") && !format.equals("flac")) throw new IllegalArgumentException("format is mp3 or flac");
            preset = preset == null || preset.isBlank() ? "neutral" : preset.toLowerCase();
            if (!PRESETS.contains(preset)) throw new IllegalArgumentException("preset is one of " + PRESETS);
            if (vinyl < 0 || vinyl > 100) throw new IllegalArgumentException("vinyl is 0..100");
            vinyl = vinyl / 10 * 10;
            noise = noise == null || noise.isBlank() ? "off" : noise.toLowerCase();
            if (!noise.equals("off")) {
                int db;
                try { db = Integer.parseInt(noise); } catch (NumberFormatException e) { throw new IllegalArgumentException("noise is off or -60..-30"); }
                if (db < -60 || db > -30) throw new IllegalArgumentException("noise is off or -60..-30");
                noise = String.valueOf(db);
            }
        }

        boolean isDefault() { return equals(DEFAULT); }
    }

    /** Engine seeds the studio can render (guest songs with genre support). */
    default List<String> seeds() { return List.of(); }

    /** What the studio is doing for a request: the client plays {@code url} only when READY. */
    enum Status { READY, ORIGINAL, RENDERING, DOWN }

    /**
     * {@code url} is null unless {@code status} is READY: the client keeps the original. RENDERING carries the studio's
     * {@code jobId} and how long to wait before asking again ({@code retryAfterMs}); DOWN means the studio is unreachable,
     * slow or answering garbage, and the client should not poll it.
     */
    record Arrangement(String source, String genre, boolean studio, boolean available, String url, String note,
                       Status status, String jobId, Long retryAfterMs) {
        public Arrangement(String source, String genre, boolean studio, boolean available, String url, String note) {
            this(source, genre, studio, available, url, note, available ? Status.READY : Status.ORIGINAL, null, null);
        }
    }

    /** A one-glance health view for the UI: UP, DEGRADED (breaker half open / recent errors), DOWN, or OFF. */
    default java.util.Map<String, Object> health() { return java.util.Map.of("state", "OFF"); }

    StudioArranger STUB = (source, genre, studio) -> new Arrangement(source, genre, studio, false, null,
            "original".equals(genre) && !studio ? "the original song"
                    : "rd-studio is not connected: playing the original");
}
