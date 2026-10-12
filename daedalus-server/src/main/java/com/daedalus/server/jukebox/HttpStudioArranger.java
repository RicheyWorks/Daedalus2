// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.LongSupplier;
import java.util.regex.Pattern;

/**
 * rd-studio over HTTP ({@code DAEDALUS_JUKEBOX_STUDIO_URL}, contract in rd-studio's server/README.md):
 * {@code GET /arrange} → 200 {url, engine, key, note} or 404 (still rendering / unknown source → play the original).
 * The browser never talks to rd-studio: audio and coats come back through the realm
 * ({@code /api/v1/jukebox/studio/audio/{key}}, {@code /api/v1/jukebox/coat.png}), so the studio can stay on localhost.
 */
public final class HttpStudioArranger implements StudioArranger {

    /** rd-studio's own audio key shape: {@code <seed>__<genre>__<studio|plain>__<engine>.mp3}. */
    public static final Pattern AUDIO_KEY = Pattern.compile("[a-z0-9_-]+__[a-z]+__(studio|plain)__[A-Za-z0-9.-]+\\.mp3");
    public static final Pattern HASH = Pattern.compile("0x[0-9a-f]{64}");
    static final long HIT_TTL_MS = 10 * 60_000, MISS_TTL_MS = 15_000;

    private static final ObjectMapper JSON = new ObjectMapper();
    private final String base;
    private final LongSupplier clock;
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
    private final Map<String, Cached> cache = new ConcurrentHashMap<>();
    private volatile Cached seeds;

    private record Cached(long at, long ttl, Object value) {
        boolean fresh(long now) { return now - at < ttl; }
    }

    public HttpStudioArranger(String base, LongSupplier clock) {
        this.base = base.endsWith("/") ? base.substring(0, base.length() - 1) : base;
        this.clock = clock;
    }

    @Override
    public Arrangement arrange(String source, String genre, boolean studio) {
        String key = source + "|" + genre + "|" + studio;
        long now = clock.getAsLong();
        Cached c = cache.get(key);
        if (c != null && c.fresh(now)) return (Arrangement) c.value();
        Arrangement a;
        try {
            HttpResponse<String> res = get("/arrange?source=" + enc(source) + "&genre=" + enc(genre) + "&studio=" + studio);
            JsonNode body = JSON.readTree(res.body().isEmpty() ? "{}" : res.body());
            String audioKey = body.path("key").asText("");
            if (res.statusCode() == 200 && AUDIO_KEY.matcher(audioKey).matches()) {
                String note = body.path("note").asText("");
                a = new Arrangement(source, genre, studio, true, "/api/v1/jukebox/studio/audio/" + audioKey,
                        note.isEmpty() ? "rd-studio · " + genre + (studio ? " · studio" : "") + " · " + body.path("engine").asText("") : note);
            } else if (res.statusCode() == 404) {
                a = new Arrangement(source, genre, studio, false, null, "rendering".equals(body.path("status").asText())
                        ? "rd-studio is still rendering this one: playing the original" : "no rd-studio version yet: playing the original");
            } else {
                a = new Arrangement(source, genre, studio, false, null, "rd-studio answered " + res.statusCode() + ": playing the original");
            }
        } catch (IOException | RuntimeException e) {
            a = new Arrangement(source, genre, studio, false, null, "rd-studio is unreachable: playing the original");
        }
        if (cache.size() > 1000) cache.clear();
        cache.put(key, new Cached(now, a.available() ? HIT_TTL_MS : MISS_TTL_MS, a));
        return a;
    }

    @Override
    @SuppressWarnings("unchecked")
    public List<String> seeds() {
        long now = clock.getAsLong();
        Cached c = seeds;
        if (c != null && c.fresh(now)) return (List<String>) c.value();
        List<String> out = new ArrayList<>();
        try {
            HttpResponse<String> res = get("/health");
            if (res.statusCode() == 200) {
                for (JsonNode s : JSON.readTree(res.body()).path("seeds")) {
                    if (s.asText().matches("[a-z0-9][a-z0-9_-]{0,63}")) out.add(s.asText());
                }
            }
        } catch (IOException | RuntimeException e) {
            // unreachable studio: no engine seeds, guest songs still play
        }
        seeds = new Cached(now, out.isEmpty() ? MISS_TTL_MS : HIT_TTL_MS, List.copyOf(out));
        return (List<String>) seeds.value();
    }

    /** An rd-studio MP3 by its key (whole file; rd-studio has no Range support). */
    public Optional<InputStream> audio(String key) {
        return AUDIO_KEY.matcher(key).matches() ? stream("/audio/" + key) : Optional.empty();
    }

    /** The token's real coat: seamless PNG ({@code size} 256/512/1024) for its 32-byte hash. */
    public Optional<InputStream> coatPng(String hash, int size) {
        if (!HASH.matcher(hash).matches() || !(size == 256 || size == 512 || size == 1024)) return Optional.empty();
        return stream("/coat.png?hash=" + hash + "&size=" + size);
    }

    /** The coat genome JSON ({traits, genome, kind}) for a hash, as text. */
    public Optional<String> coat(String hash) {
        if (!HASH.matcher(hash).matches()) return Optional.empty();
        try {
            HttpResponse<String> res = get("/coat?hash=" + hash);
            return res.statusCode() == 200 ? Optional.of(res.body()) : Optional.empty();
        } catch (IOException | RuntimeException e) {
            return Optional.empty();
        }
    }

    private Optional<InputStream> stream(String path) {
        try {
            HttpResponse<InputStream> res = http.send(HttpRequest.newBuilder(URI.create(base + path))
                    .timeout(Duration.ofSeconds(60)).GET().build(), HttpResponse.BodyHandlers.ofInputStream());
            if (res.statusCode() == 200) return Optional.of(res.body());
            res.body().close();
            return Optional.empty();
        } catch (IOException e) {
            return Optional.empty();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return Optional.empty();
        }
    }

    private HttpResponse<String> get(String path) throws IOException {
        try {
            return http.send(HttpRequest.newBuilder(URI.create(base + path)).timeout(Duration.ofSeconds(5)).GET().build(),
                    HttpResponse.BodyHandlers.ofString());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("interrupted", e);
        }
    }

    private static String enc(String s) {
        return URLEncoder.encode(s, StandardCharsets.UTF_8);
    }
}
