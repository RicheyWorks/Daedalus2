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
import java.net.http.HttpTimeoutException;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;
import java.util.function.LongSupplier;
import java.util.regex.Pattern;

/**
 * rd-studio over HTTP ({@code DAEDALUS_JUKEBOX_STUDIO_URL}; contract in rd-studio's server/README.md and
 * CHANGES_FOR_FLEX.md). The jukebox must never wait on the studio, so every call is bounded:
 * <ul>
 *   <li>short connect and request timeouts ({@link Tuning}); a timeout is not retried (the studio is slow: give up now);</li>
 *   <li>a refused connection or a 502/503/504 is retried a bounded number of times with jittered backoff;</li>
 *   <li>a {@link CircuitBreaker} trips after consecutive failures, and while open every call answers DOWN instantly;</li>
 *   <li>200 (ready) and 404 (no version) are cached; 202 (rendering) is cached for its {@code Retry-After} so polls
 *       coalesce; failures are cached briefly; identical concurrent requests share one upstream call.</li>
 * </ul>
 * The browser never talks to rd-studio: audio and coats come back through the realm, so the studio stays on localhost.
 * Coat PNGs are validated (PNG signature, IHDR size equals the size asked for, byte cap) and cached per engine version.
 */
public final class HttpStudioArranger implements StudioArranger {

    /**
     * rd-studio r4's audio file name: {@code <src>__<genre>__<studio|plain>__<preset>-v<vinyl>-n<noise>__<engine>.(mp3|flac)}
     * (CHANGES_FOR_FLEX.md §TL;DR 2). Nothing else is ever proxied.
     */
    public static final Pattern AUDIO_KEY = Pattern.compile(
            "(e\\d{5}|t\\d{5})__[a-z]+__(studio|plain)__[a-z]+-v\\d{1,3}-n(off|\\d{2})__[A-Za-z0-9.-]+\\.(mp3|flac)");
    /** The sources rd-studio knows: engine seeds and token ids 0–49999 without leading zeros. Others never leave the realm. */
    static final Pattern STUDIO_SOURCE = Pattern.compile("seed:e\\d{5}|token:(0|[1-9]\\d{0,3}|[1-4]\\d{4})");
    public static final long MAX_AUDIO_BYTES = 32L << 20;
    /** Fallback when /health doesn't list seeds (r4): the engine seeds CHANGES_FOR_FLEX.md names. */
    static final List<String> R4_SEEDS = List.of("e00015", "e00084", "e00165", "e00153", "e00601", "e02014");
    public static final Pattern HASH = Pattern.compile("0x[0-9a-f]{64}");
    static final Pattern JOB_ID = Pattern.compile("[A-Za-z0-9_.:-]{1,80}");
    static final Pattern ETAG = Pattern.compile("(W/)?\"[\\x21\\x23-\\x7e]{1,128}\"");
    static final long HIT_TTL_MS = 10 * 60_000, MISS_TTL_MS = 60_000, DOWN_TTL_MS = 5_000, HEALTH_TTL_MS = 30_000,
            FAILED_QA_TTL_MS = 60 * 60_000;
    static final int MAX_PNG_BYTES = 8 << 20, MAX_JSON_BYTES = 64 << 10, PNG_CACHE_BYTES = 64 << 20;

    /**
     * Timeouts and resilience knobs. {@code sleeper} is the backoff wait (tests pass a recorder).
     */
    public record Tuning(Duration connect, Duration request, Duration stream, int retries, long backoffMs,
                         int breakerFailures, long breakerOpenMs, Sleeper sleeper) {
        public static final Tuning DEFAULT = new Tuning(Duration.ofMillis(800), Duration.ofMillis(1500), Duration.ofSeconds(20),
                2, 60, 3, 20_000, Thread::sleep);
    }

    @FunctionalInterface
    public interface Sleeper { void sleep(long ms) throws InterruptedException; }

    private static final ObjectMapper JSON = new ObjectMapper();
    private final String base;
    private final LongSupplier clock;
    private final Tuning t;
    private final HttpClient http;
    private final CircuitBreaker breaker;
    private final Map<String, Cached> cache = new ConcurrentHashMap<>();
    private final Map<String, CompletableFuture<Arrangement>> inflight = new ConcurrentHashMap<>();
    private final Map<String, byte[]> pngs = Collections.synchronizedMap(new LinkedHashMap<>(16, 0.75f, true));
    private long pngBytes;
    private final Map<String, String> coats = Collections.synchronizedMap(new LinkedHashMap<>(16, 0.75f, true) {
        @Override protected boolean removeEldestEntry(Map.Entry<String, String> e) { return size() > 4096; }
    });
    private volatile Cached health;
    private volatile String lastError = "";
    private volatile long lastLatencyMs = -1;
    private volatile boolean lastOk = true;

    private record Cached(long at, long ttl, Object value) {
        boolean fresh(long now) { return now - at < ttl; }
    }

    /** One relayed upstream body: {@code status} 200 with a body, or 304 (the caller's ETag still matches). */
    public record Upstream(int status, InputStream body, String etag, long length, String contentType, String cacheControl) {}

    public HttpStudioArranger(String base, LongSupplier clock) {
        this(base, clock, Tuning.DEFAULT);
    }

    public HttpStudioArranger(String base, LongSupplier clock, Tuning tuning) {
        URI u = URI.create(base.trim());
        if (!"http".equals(u.getScheme()) && !"https".equals(u.getScheme()) || u.getHost() == null)
            throw new IllegalArgumentException("studio-url must be an http(s) URL");
        this.base = base.trim().replaceAll("/+$", "");
        this.clock = clock;
        this.t = tuning;
        this.http = HttpClient.newBuilder().connectTimeout(tuning.connect()).followRedirects(HttpClient.Redirect.NEVER).build();
        this.breaker = new CircuitBreaker(tuning.breakerFailures(), tuning.breakerOpenMs(), clock);
    }

    // ---------------------------------------------------------------- arrangements

    @Override
    public Arrangement arrange(String source, String genre, boolean studio) {
        return arrange(source, genre, studio, Render.DEFAULT);
    }

    @Override
    public Arrangement arrange(String source, String genre, boolean studio, Render render) {
        if (!STUDIO_SOURCE.matcher(source).matches())       // a file seed or an out-of-range id: rd-studio doesn't know it
            return new Arrangement(source, genre, studio, false, null, "no rd-studio version: playing the original");
        String key = source + "|" + genre + "|" + studio + "|" + render;
        Cached c = cache.get(key);
        if (c != null && c.fresh(clock.getAsLong())) return (Arrangement) c.value();
        if (breaker.state() == CircuitBreaker.State.HALF_OPEN && !ready())
            return down(source, genre, studio, "rd-studio is busy: playing the original");
        if (!breaker.allow()) return down(source, genre, studio, "rd-studio is down: playing the original");
        CompletableFuture<Arrangement> mine = new CompletableFuture<>();
        CompletableFuture<Arrangement> running = inflight.putIfAbsent(key, mine);
        if (running != null) return running.join();       // someone is already asking: share their answer
        try {
            Arrangement a = fetch(source, genre, studio, render);
            long ttl = switch (a.status()) {
                case READY -> HIT_TTL_MS;
                case ORIGINAL -> a.note().contains("quality check") ? FAILED_QA_TTL_MS : HIT_TTL_MS;   // 404/422 are final per engine
                case RENDERING -> a.retryAfterMs();
                case DOWN -> DOWN_TTL_MS;
            };
            if (cache.size() > 2000) cache.clear();
            cache.put(key, new Cached(clock.getAsLong(), ttl, a));
            mine.complete(a);
            return a;
        } catch (RuntimeException e) {
            mine.completeExceptionally(e);
            throw e;
        } finally {
            inflight.remove(key);
        }
    }

    private Arrangement fetch(String source, String genre, boolean studio, Render r) {
        HttpResponse<String> res;
        String q = "/arrange?source=" + enc(source) + "&genre=" + enc(genre) + "&studio=" + studio;
        if (!r.isDefault()) q += "&format=" + r.format() + "&preset=" + r.preset() + "&vinyl=" + r.vinyl() + "&noise=" + enc(r.noise());
        try {
            res = send(q);
        } catch (HttpTimeoutException e) {
            return down(source, genre, studio, "rd-studio is slow: playing the original");
        } catch (IOException e) {
            return down(source, genre, studio, "rd-studio is unreachable: playing the original");
        }
        JsonNode body;
        try {
            body = res.body().isBlank() ? JSON.createObjectNode() : JSON.readTree(res.body());
        } catch (IOException e) {
            body = null;
        }
        int code = res.statusCode();
        if (code == 200 && body != null) {
            String file = audioFile(body);
            if (file != null) {
                ok();
                String note = clip(body.path("note").asText(""));
                return new Arrangement(source, genre, studio, true, "/api/v1/jukebox/studio/audio/" + file,
                        note.isEmpty() ? "rd-studio · " + genre + (studio ? " · studio" : "") + label(r) : note);
            }
        }
        if (code == 202) {                     // r4: not rendered yet, queued once (coalesced): play the original, retry later
            ok();
            String job = body == null ? "" : firstText(body, "job", "jobId", "id");
            String header = res.headers().firstValue("Retry-After").orElse(body == null ? "" : body.path("retry_after").asText(""));
            return new Arrangement(source, genre, studio, false, null, "rd-studio is rendering this one: playing the original",
                    Status.RENDERING, JOB_ID.matcher(job).matches() ? job : null, retryAfter(header));
        }
        if (code == 404) {                     // r4: only "unknown source"
            ok();
            return new Arrangement(source, genre, studio, false, null, source.startsWith("token:")
                    ? "no rd-studio version of this token yet: playing its own player"
                    : "rd-studio doesn't know this song: playing the original");
        }
        if (code == 422) {                     // the render failed QA and will never be served for this engine: don't retry
            ok();
            return new Arrangement(source, genre, studio, false, null, "that rd-studio render didn't pass its quality check: playing the original");
        }
        if (code == 400) {
            ok();     // the studio is fine; it just doesn't take this request
            return new Arrangement(source, genre, studio, false, null, "rd-studio can't arrange this one: playing the original");
        }
        if (code == 503) {                     // queue full or draining: back off for Retry-After with the breaker open
            long wait = retryAfter(res.headers().firstValue("Retry-After").orElse("30"));
            lastOk = false;
            lastError = "busy (503): queue full or draining";
            breaker.trip(wait);
            return new Arrangement(source, genre, studio, false, null, "rd-studio is busy: playing the original",
                    Status.DOWN, null, wait);
        }
        fail(code == 200 ? "garbage 200 from /arrange" : "HTTP " + code);
        return down(source, genre, studio, code == 200 ? "rd-studio answered garbage: playing the original"
                : "rd-studio answered " + code + ": playing the original");
    }

    /** The proxied file name from a 200: r4's {@code key} plus the extension of its {@code url}; null unless it matches. */
    static String audioFile(JsonNode body) {
        String key = body.path("key").asText("");
        String url = body.path("url").asText("");
        String file = key.endsWith(".mp3") || key.endsWith(".flac") ? key
                : key + (url.endsWith(".flac") ? ".flac" : url.endsWith(".mp3") ? ".mp3" : "");
        return AUDIO_KEY.matcher(file).matches() ? file : null;
    }

    private static String label(Render r) {
        StringBuilder b = new StringBuilder();
        if (!r.preset().equals("neutral")) b.append(" · ").append(r.preset());
        if (r.vinyl() > 0) b.append(" · vinyl ").append(r.vinyl());
        if (!r.noise().equals("off")) b.append(" · surface ").append(r.noise()).append(" dB");
        if (r.format().equals("flac")) b.append(" · FLAC 24-bit");
        return b.toString();
    }

    private Arrangement down(String source, String genre, boolean studio, String note) {
        return new Arrangement(source, genre, studio, false, null, note, Status.DOWN, null, null);
    }

    /** Retry-After as delta seconds (or an HTTP date, treated as the default), clamped to 0.25..30 s. */
    static long retryAfter(String header) {
        try {
            double s = Double.parseDouble(header.trim());
            if (Double.isFinite(s)) return Math.max(250, Math.min(30_000, Math.round(s * 1000)));
        } catch (NumberFormatException e) {
            // an HTTP-date or junk: fall through
        }
        return 2_000;
    }

    // ---------------------------------------------------------------- seeds + health

    @Override
    @SuppressWarnings("unchecked")
    public List<String> seeds() {
        return (List<String>) healthInfo().getOrDefault("seeds", List.of());
    }

    @Override
    public Map<String, Object> health() {
        Map<String, Object> h = healthInfo();
        CircuitBreaker.State b = breaker.state();
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("state", b == CircuitBreaker.State.OPEN ? "DOWN"
                : b == CircuitBreaker.State.HALF_OPEN || !lastOk || !(boolean) h.getOrDefault("ok", false) ? "DEGRADED" : "UP");
        out.put("breaker", b.name());
        out.put("engine", h.getOrDefault("engine", ""));
        if (h.containsKey("p95Ms")) out.put("p95Ms", h.get("p95Ms"));
        if (h.containsKey("queue")) out.put("queue", h.get("queue"));
        if (Boolean.TRUE.equals(h.get("draining"))) out.put("state", "DEGRADED");
        out.put("lastLatencyMs", lastLatencyMs);
        out.put("lastError", lastError);
        return out;
    }

    /** /health (liveness: engine, coat_engine, queue, draining, seeds when listed) + /metrics (p95, queue), cached. */
    private Map<String, Object> healthInfo() {
        long now = clock.getAsLong();
        Cached c = health;
        if (c != null && c.fresh(now)) return cast(c.value());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("ok", false);
        if (breaker.state() != CircuitBreaker.State.OPEN) {
            try {
                HttpResponse<String> res = send("/health");
                JsonNode body = JSON.readTree(res.body());
                if (res.statusCode() == 200 && body.isObject()) {
                    List<String> seeds = new ArrayList<>();
                    for (JsonNode s : body.path("seeds")) if (s.asText().matches("e\\d{5}") && seeds.size() < 200) seeds.add(s.asText());
                    out.put("ok", body.path("ok").asBoolean(true) && !body.path("draining").asBoolean(false));
                    out.put("seeds", List.copyOf(seeds.isEmpty() ? R4_SEEDS : seeds));
                    out.put("engine", safe(body.path("engine").asText("")));
                    out.put("coatEngine", safe(body.path("coat_engine").asText("")));
                    out.put("queue", body.path("queue").asInt(0));
                    out.put("draining", body.path("draining").asBoolean(false));
                    metrics(out);
                } else {
                    fail("health HTTP " + res.statusCode());
                }
            } catch (IOException | RuntimeException e) {
                fail("health: " + e.getClass().getSimpleName());
            }
        }
        health = new Cached(now, (boolean) out.get("ok") ? HEALTH_TTL_MS : DOWN_TTL_MS, out);
        return out;
    }

    /** Best-effort read of rd-studio's Prometheus text: request latency p95 and queue depth. */
    private void metrics(Map<String, Object> out) {
        try {
            HttpResponse<String> res = send("/metrics");
            if (res.statusCode() != 200 || res.body().length() > 256 * 1024) return;
            for (String line : res.body().split("\n")) {
                if (line.startsWith("rd_studio_latency_ms{q=\"0.95\"}")) out.put("p95Ms", Double.parseDouble(line.substring(line.lastIndexOf(' ') + 1)));
                if (line.startsWith("rd_studio_queue_depth ")) out.put("queue", (int) Double.parseDouble(line.substring(22).trim()));
            }
        } catch (IOException | RuntimeException e) {
            // metrics are optional
        }
    }

    /** /ready: 200 → take work; 503 (queue full / draining) → keep the breaker open for its Retry-After. */
    boolean ready() {
        try {
            HttpResponse<String> res = send("/ready");
            if (res.statusCode() == 200) { ok(); return true; }
            if (res.statusCode() == 404) return true;       // a pre-r4 studio without /ready: let the request decide
            breaker.trip(retryAfter(res.headers().firstValue("Retry-After").orElse("10")));
            lastOk = false;
            lastError = "not ready (" + res.statusCode() + "): queue full or draining";
            return false;
        } catch (IOException e) {
            fail("ready: " + e.getClass().getSimpleName());
            return false;
        }
    }

    private static String safe(String v) { return v.matches("[A-Za-z0-9.-]{1,40}") ? v : ""; }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> cast(Object o) { return (Map<String, Object>) o; }

    // ---------------------------------------------------------------- audio + coats

    /** An rd-studio MP3 by its key (whole file; rd-studio has no Range support). Honors the studio's content-hash ETag. */
    public Optional<Upstream> audio(String key, String ifNoneMatch) {
        if (key == null || !AUDIO_KEY.matcher(key).matches() || !breaker.allow()) return Optional.empty();
        try {
            HttpRequest.Builder req = HttpRequest.newBuilder(URI.create(base + "/audio/" + key)).timeout(t.stream()).GET();
            if (ifNoneMatch != null && ETAG.matcher(ifNoneMatch.trim()).matches()) req.header("If-None-Match", ifNoneMatch.trim());
            HttpResponse<InputStream> res = http.send(req.build(), HttpResponse.BodyHandlers.ofInputStream());
            String etag = res.headers().firstValue("ETag").filter(e -> ETAG.matcher(e).matches()).orElse(null);
            String type = res.headers().firstValue("Content-Type").orElse("audio/mpeg").toLowerCase();
            if (res.statusCode() == 304) {
                res.body().close();
                ok();
                return Optional.of(new Upstream(304, InputStream.nullInputStream(), etag, 0, null, cacheControl(res)));
            }
            long length = res.headers().firstValueAsLong("Content-Length").orElse(-1);
            if (res.statusCode() == 200 && type.startsWith("audio/") && length <= MAX_AUDIO_BYTES) {
                ok();
                String ct = key.endsWith(".flac") ? "audio/flac" : "audio/mpeg";
                return Optional.of(new Upstream(200, res.body(), etag, length, ct, cacheControl(res)));
            }
            res.body().close();
            if (res.statusCode() >= 500) fail("audio HTTP " + res.statusCode());
            return Optional.empty();
        } catch (IOException e) {
            fail("audio: " + e.getClass().getSimpleName());
            return Optional.empty();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return Optional.empty();
        }
    }

    /**
     * The token's real coat: a seamless PNG ({@code size} 256/512/1024) for its 32-byte hash, validated (PNG, IHDR is
     * size × size, under {@link #MAX_PNG_BYTES}) and cached per engine version (coats are deterministic per hash + engine).
     * Empty on anything else: the client then grows its own coat.
     */
    public Optional<byte[]> coatPng(String hash, int size) {
        if (hash == null || !HASH.matcher(hash).matches() || !(size == 256 || size == 512 || size == 1024)) return Optional.empty();
        // r4: byte-identical per (hash, size, coat engine): cached forever under that key (bounded by bytes)
        String key = healthInfo().getOrDefault("coatEngine", healthInfo().getOrDefault("engine", "")) + "|" + hash + "|" + size;
        byte[] hit = pngs.get(key);
        if (hit != null) return Optional.of(hit);
        Optional<byte[]> got = bytes("/coat.png?hash=" + hash + "&size=" + size, MAX_PNG_BYTES)
                .filter(b -> isPng(b, size));
        got.ifPresent(b -> {
            synchronized (pngs) {
                pngs.put(key, b);
                pngBytes += b.length;
                var it = pngs.entrySet().iterator();
                while (pngBytes > PNG_CACHE_BYTES && it.hasNext()) { pngBytes -= it.next().getValue().length; it.remove(); }
            }
        });
        return got;
    }

    /** The coat genome JSON ({traits, genome, kind}) for a hash: must be a JSON object under 64 KB. Cached. */
    public Optional<String> coat(String hash) {
        if (hash == null || !HASH.matcher(hash).matches()) return Optional.empty();
        String hit = coats.get(hash);
        if (hit != null) return Optional.of(hit);
        Optional<String> got = bytes("/coat?hash=" + hash, MAX_JSON_BYTES).map(b -> new String(b, StandardCharsets.UTF_8))
                .filter(HttpStudioArranger::isJsonObject);
        got.ifPresent(j -> coats.put(hash, j));
        return got;
    }

    /** PNG signature, then an IHDR chunk whose width and height are both {@code size}. */
    static boolean isPng(byte[] b, int size) {
        byte[] sig = {(byte) 0x89, 'P', 'N', 'G', 13, 10, 26, 10};
        if (b == null || b.length < 33) return false;
        for (int i = 0; i < 8; i++) if (b[i] != sig[i]) return false;
        ByteBuffer bb = ByteBuffer.wrap(b);
        return bb.getInt(8) == 13 && b[12] == 'I' && b[13] == 'H' && b[14] == 'D' && b[15] == 'R'
                && bb.getInt(16) == size && bb.getInt(20) == size;
    }

    private static boolean isJsonObject(String s) {
        try {
            return JSON.readTree(s).isObject();
        } catch (IOException e) {
            return false;
        }
    }

    private Optional<byte[]> bytes(String path, int cap) {
        if (!breaker.allow()) return Optional.empty();
        try {
            HttpResponse<InputStream> res = http.send(HttpRequest.newBuilder(URI.create(base + path)).timeout(t.stream()).GET().build(),
                    HttpResponse.BodyHandlers.ofInputStream());
            try (InputStream in = res.body()) {
                if (res.statusCode() != 200) {
                    if (res.statusCode() >= 500) fail(path + " HTTP " + res.statusCode()); else ok();
                    return Optional.empty();
                }
                byte[] b = in.readNBytes(cap + 1);
                if (b.length > cap) { fail(path + " too large"); return Optional.empty(); }
                ok();
                return Optional.of(b);
            }
        } catch (IOException e) {
            fail(path + ": " + e.getClass().getSimpleName());
            return Optional.empty();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return Optional.empty();
        }
    }

    /** The studio's Cache-Control when it is the immutable form r4 sends; otherwise our own default. */
    private static String cacheControl(HttpResponse<?> res) {
        String cc = res.headers().firstValue("Cache-Control").orElse("");
        return cc.matches("[a-z0-9=, -]{1,100}") ? cc : "public, max-age=31536000, immutable";
    }

    // ---------------------------------------------------------------- transport

    /** One bounded GET with jittered retries for refused connections and 502/504 (never for timeouts or a 503 back-off). */
    private HttpResponse<String> send(String path) throws IOException {
        HttpRequest req = HttpRequest.newBuilder(URI.create(base + path)).timeout(t.request()).GET().build();
        IOException last = null;
        for (int attempt = 0; attempt <= t.retries(); attempt++) {
            if (attempt > 0) backoff(attempt);
            long start = System.nanoTime();
            try {
                HttpResponse<String> res = http.send(req, HttpResponse.BodyHandlers.ofString());
                lastLatencyMs = (System.nanoTime() - start) / 1_000_000;
                int c = res.statusCode();
                if ((c == 502 || c == 504) && attempt < t.retries()) continue;   // 503 = "back off": never hammered
                return res;
            } catch (HttpTimeoutException e) {
                lastLatencyMs = (System.nanoTime() - start) / 1_000_000;
                fail("timeout after " + lastLatencyMs + " ms");
                throw e;
            } catch (IOException e) {
                last = e;
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IOException("interrupted", e);
            }
        }
        fail("unreachable: " + (last == null ? "?" : last.getClass().getSimpleName()));
        throw last == null ? new IOException("no answer") : last;
    }

    private void backoff(int attempt) throws IOException {
        long base = t.backoffMs() << (attempt - 1);
        long jittered = base / 2 + ThreadLocalRandom.current().nextLong(base + 1);   // 0.5x .. 1.5x
        try {
            t.sleeper().sleep(jittered);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("interrupted", e);
        }
    }

    private void ok() {
        lastOk = true;
        breaker.success();
    }

    private void fail(String why) {
        lastOk = false;
        lastError = clip(why);
        breaker.failure();
    }

    CircuitBreaker breaker() { return breaker; }

    private static String firstText(JsonNode n, String... names) {
        for (String k : names) if (n.hasNonNull(k)) return n.get(k).asText("");
        return "";
    }

    private static String clip(String s) {
        return s.length() > 160 ? s.substring(0, 160) : s;
    }

    private static String enc(String s) {
        return URLEncoder.encode(s, StandardCharsets.UTF_8);
    }
}
