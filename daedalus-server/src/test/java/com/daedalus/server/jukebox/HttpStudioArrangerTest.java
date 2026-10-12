// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.zip.CRC32;

import static org.assertj.core.api.Assertions.assertThat;

/** Against a fake rd-studio speaking its contract, with faults injected per test (down, slow, garbage, 5xx, 202). */
class HttpStudioArrangerTest {

    static final String STEM = "e00015__jazz__studio__neutral-v0-noff__v6r4-s680199b4";
    static final String KEY = STEM + ".mp3";
    static final String HASH = "0x19227c7cb7cb2f6f78553007595b21ad35be0258d5f71eb7a467367e6ff19198";
    static final HttpStudioArranger.Tuning FAST = new HttpStudioArranger.Tuning(Duration.ofMillis(300), Duration.ofMillis(400),
            Duration.ofSeconds(5), 2, 40, 3, 10_000, ms -> {});

    enum Mode { NORMAL, SLOW, GARBAGE, HTML, FLAKY_503, ALWAYS_503, RENDERING, BAD_PNG, WRONG_SIZE_PNG, HUGE_PNG, GARBAGE_COAT,
        FAILED_QA, FLAKY_502, BUSY }

    private HttpServer server;
    private volatile Mode mode = Mode.NORMAL;
    private final AtomicInteger arranges = new AtomicInteger(), coatHits = new AtomicInteger(), flaky = new AtomicInteger();
    private final AtomicLong now = new AtomicLong();
    private final List<Long> sleeps = Collections.synchronizedList(new ArrayList<>());
    private volatile int arrangeDelayMs;
    private volatile String lastArrange = "";
    private volatile int readyStatus = 200;
    private final AtomicInteger readyHits = new AtomicInteger();
    private HttpStudioArranger studio;

    @BeforeEach
    void start() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.setExecutor(Executors.newCachedThreadPool());
        server.createContext("/", this::handle);
        server.start();
        studio = studio(FAST);
    }

    private HttpStudioArranger studio(HttpStudioArranger.Tuning t) {
        HttpStudioArranger.Tuning withSleeps = new HttpStudioArranger.Tuning(t.connect(), t.request(), t.stream(), t.retries(),
                t.backoffMs(), t.breakerFailures(), t.breakerOpenMs(), sleeps::add);
        return new HttpStudioArranger("http://127.0.0.1:" + server.getAddress().getPort() + "/", now::get, withSleeps);
    }

    private void handle(HttpExchange ex) throws IOException {
        String q = ex.getRequestURI().toString();
        int status = 404;
        byte[] body = "{}".getBytes();
        String type = "application/json";
        try {
            if (q.startsWith("/arrange")) {
                arranges.incrementAndGet();
                lastArrange = q;
                if (arrangeDelayMs > 0) Thread.sleep(arrangeDelayMs);
                switch (mode) {
                    case SLOW -> { Thread.sleep(1500); status = 200; body = ready(); }
                    case GARBAGE -> { status = 200; body = "{\"url\":\"x\",\"key\":\"../../etc/passwd\"}".getBytes(); }
                    case HTML -> { status = 200; body = "<html>oops</html>".getBytes(); type = "text/html"; }
                    case FLAKY_503, FLAKY_502 -> {
                        if (flaky.incrementAndGet() <= 2) status = mode == Mode.FLAKY_503 ? 503 : 502;
                        else { status = 200; body = ready(); }
                    }
                    case ALWAYS_503 -> status = 502;
                    case BUSY -> { status = 503; ex.getResponseHeaders().set("Retry-After", "30"); body = "{\"error\":\"queue full\"}".getBytes(); }
                    case FAILED_QA -> { status = 422; body = "{\"status\":\"failed_qa\"}".getBytes(); }
                    case RENDERING -> {
                        status = 202;
                        body = "{\"job\":\"job-42\",\"status\":\"queued\"}".getBytes();
                        ex.getResponseHeaders().set("Retry-After", "3");
                    }
                    default -> {
                        if (q.contains("seed%3Ae00015") && q.contains("genre=jazz") && q.contains("format=flac")) {
                            status = 200;
                            body = ("{\"url\":\"http://127.0.0.1:8797/audio/e00015__jazz__studio__harman-v50-noff__v6r4-s680199b4.flac\","
                                    + "\"key\":\"e00015__jazz__studio__harman-v50-noff__v6r4-s680199b4\",\"note\":\"\"}").getBytes();
                        } else if (q.contains("seed%3Ae00015") && q.contains("genre=jazz")) { status = 200; body = ready(); }
                        else if (q.contains("token%3A1&")) {
                            status = 202; ex.getResponseHeaders().set("Retry-After", "30");
                            body = "{\"status\":\"queued\",\"job\":\"6b8ed8d1f32f4ec2\",\"retry_after\":30}".getBytes();
                        } else status = 404;
                    }
                }
            } else if (q.equals("/health")) {
                status = 200;
                body = "{\"ok\":true,\"engine\":\"v6r4-s680199b4\",\"coat_engine\":\"cc8445587\",\"queue\":1,\"workers\":2,\"draining\":false}".getBytes();
            } else if (q.equals("/voices")) {
                status = 200;
                body = "{\"schema_version\":\"rd-voice/1\",\"count\":1,\"voices\":[{\"name\":\"Celesta\",\"adsr\":{\"a\":0.002}}]}".getBytes();
            } else if (q.startsWith("/note?")) {
                lastArrange = q;
                status = 200;
                body = ("{\"url\":\"http://127.0.0.1:8797/audio/notes/n0123456789abcdef01234567-v6r4-s60798b99.mp3\","
                        + "\"etag\":\"\\\"e\\\"\",\"note\":{\"voice\":\"Celesta\",\"midi\":60}}").getBytes();
            } else if (q.equals("/audio/notes/n0123456789abcdef01234567-v6r4-s60798b99.mp3")) {
                status = 200; type = "audio/mpeg"; body = "ID3note".getBytes();
            } else if (q.equals("/ready")) {
                readyHits.incrementAndGet();
                status = readyStatus;
                if (status == 503) ex.getResponseHeaders().set("Retry-After", "10");
                body = (status == 200 ? "{\"ready\":true}" : "{\"ready\":false}").getBytes();
            } else if (q.equals("/metrics")) {
                status = 200; type = "text/plain";
                body = "rd_studio_queue_depth 3\nrd_studio_latency_ms{q=\"0.5\"} 1.2\nrd_studio_latency_ms{q=\"0.95\"} 23.5\n".getBytes();
            } else if (q.equals("/audio/" + KEY)) {
                String inm = ex.getRequestHeaders().getFirst("If-None-Match");
                ex.getResponseHeaders().set("ETag", "\"sha-abc\"");
                ex.getResponseHeaders().set("Cache-Control", "public, max-age=31536000, immutable");
                if ("\"sha-abc\"".equals(inm)) { status = 304; body = new byte[0]; }
                else { status = 200; body = "ID3audio".getBytes(); type = "audio/mpeg"; }
            } else if (q.startsWith("/coat.png?hash=" + HASH)) {
                coatHits.incrementAndGet();
                status = 200;
                type = "image/png";
                body = switch (mode) {
                    case BAD_PNG -> "GIF89a not a png at all, padded to be long enough".getBytes();
                    case WRONG_SIZE_PNG -> png(256);
                    case HUGE_PNG -> new byte[HttpStudioArranger.MAX_PNG_BYTES + 10];
                    default -> png(Integer.parseInt(q.replaceAll(".*size=", "")));
                };
            } else if (q.startsWith("/coat?hash=" + HASH)) {
                status = 200;
                body = (mode == Mode.GARBAGE_COAT ? "[1,2" : "{\"kind\":\"spots\"}").getBytes();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        ex.getResponseHeaders().set("Content-Type", type);
        try {
            ex.sendResponseHeaders(status, status == 304 ? -1 : body.length);
            if (status != 304) ex.getResponseBody().write(body);
        } catch (IOException e) {
            // the client gave up (timeout tests)
        }
        ex.close();
    }

    private static byte[] ready() {      // r4: "key" has no extension; the url does
        return ("{\"url\":\"http://127.0.0.1:8797/audio/" + KEY + "\",\"engine\":\"v6r4-s680199b4\",\"key\":\"" + STEM + "\",\"note\":\"\"}")
                .getBytes(StandardCharsets.UTF_8);
    }

    /** A minimal valid PNG header: signature + IHDR (size × size), CRC included. */
    static byte[] png(int size) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        out.writeBytes(new byte[]{(byte) 0x89, 'P', 'N', 'G', 13, 10, 26, 10});
        ByteBuffer ihdr = ByteBuffer.allocate(17).put("IHDR".getBytes()).putInt(size).putInt(size).put((byte) 8).put((byte) 6)
                .put((byte) 0).put((byte) 0).put((byte) 0);
        CRC32 crc = new CRC32();
        crc.update(ihdr.array());
        out.writeBytes(ByteBuffer.allocate(4).putInt(13).array());
        out.writeBytes(ihdr.array());
        out.writeBytes(ByteBuffer.allocate(4).putInt((int) crc.getValue()).array());
        return out.toByteArray();
    }

    @AfterEach
    void stop() { server.stop(0); }

    // ------------------------------------------------------------------ happy path + contract

    @Test
    void a200BecomesAReadyArrangementServedThroughTheRealm() {
        StudioArranger.Arrangement a = studio.arrange("seed:e00015", "jazz", true);
        assertThat(a.available()).isTrue();
        assertThat(a.status()).isEqualTo(StudioArranger.Status.READY);
        assertThat(a.url()).isEqualTo("/api/v1/jukebox/studio/audio/" + KEY);    // never the studio's own host
        assertThat(a.note()).contains("jazz").contains("studio");
    }

    @Test
    void a404PlaysTheOriginalAndSaysWhy() {
        StudioArranger.Arrangement token = studio.arrange("token:7", "rock", false);
        assertThat(token.available()).isFalse();
        assertThat(token.status()).isEqualTo(StudioArranger.Status.ORIGINAL);
        assertThat(token.url()).isNull();
        assertThat(token.note()).contains("token");
        assertThat(studio.arrange("seed:e00084", "reggae", true).note()).contains("doesn't know");
    }

    @Test
    void a202IsRenderingWithItsJobAndRetryAfterAndIsPolledUntilReady() {
        mode = Mode.RENDERING;
        StudioArranger.Arrangement a = studio.arrange("seed:e00084", "rock", true);
        assertThat(a.status()).isEqualTo(StudioArranger.Status.RENDERING);
        assertThat(a.jobId()).isEqualTo("job-42");
        assertThat(a.retryAfterMs()).isEqualTo(3000);
        assertThat(a.url()).isNull();
        studio.arrange("seed:e00084", "rock", true);                 // a poll inside Retry-After is coalesced
        assertThat(arranges.get()).isEqualTo(1);
        mode = Mode.NORMAL;                                            // the render finished
        now.addAndGet(3001);
        assertThat(studio.arrange("seed:e00084", "rock", true).status()).isEqualTo(StudioArranger.Status.ORIGINAL);
        assertThat(arranges.get()).isEqualTo(2);
    }

    @Test
    void retryAfterIsClampedAndTolerant() {
        assertThat(HttpStudioArranger.retryAfter("0")).isEqualTo(250);
        assertThat(HttpStudioArranger.retryAfter("1.5")).isEqualTo(1500);
        assertThat(HttpStudioArranger.retryAfter("99999")).isEqualTo(30_000);
        assertThat(HttpStudioArranger.retryAfter("Wed, 21 Oct 2026 07:28:00 GMT")).isEqualTo(2000);
        assertThat(HttpStudioArranger.retryAfter("NaN")).isEqualTo(2000);
        assertThat(HttpStudioArranger.retryAfter("")).isEqualTo(2000);
    }

    @Test
    void readyAndUnknownAreCachedUntilTheirTtl() {
        studio.arrange("seed:e00015", "jazz", true);
        studio.arrange("seed:e00015", "jazz", true);
        studio.arrange("seed:e00084", "reggae", true);
        studio.arrange("seed:e00084", "reggae", true);
        assertThat(arranges.get()).isEqualTo(2);
        now.addAndGet(HttpStudioArranger.HIT_TTL_MS + 1);    // r4: 404 = unknown source, as final as a hit
        studio.arrange("seed:e00084", "reggae", true);
        studio.arrange("seed:e00015", "jazz", true);
        assertThat(arranges.get()).isEqualTo(4);
    }

    @Test
    void identicalConcurrentRequestsShareOneUpstreamCall() throws Exception {
        arrangeDelayMs = 150;
        ExecutorService pool = Executors.newFixedThreadPool(16);
        CountDownLatch go = new CountDownLatch(1);
        List<Future<StudioArranger.Arrangement>> all = new ArrayList<>();
        for (int i = 0; i < 16; i++) all.add(pool.submit(() -> { go.await(); return studio.arrange("seed:e00015", "jazz", true); }));
        go.countDown();
        for (Future<StudioArranger.Arrangement> f : all) assertThat(f.get().available()).isTrue();
        pool.shutdown();
        assertThat(arranges.get()).isEqualTo(1);
    }

    // ------------------------------------------------------------------ faults

    @Test
    void aSlowStudioFallsBackFastAndIsNotRetried() {
        mode = Mode.SLOW;
        long t0 = System.nanoTime();
        StudioArranger.Arrangement a = studio.arrange("seed:e00015", "jazz", true);
        long ms = (System.nanoTime() - t0) / 1_000_000;
        assertThat(a.status()).isEqualTo(StudioArranger.Status.DOWN);
        assertThat(a.note()).contains("slow").contains("original");
        assertThat(ms).isLessThan(1200);
        assertThat(arranges.get()).isEqualTo(1);
    }

    @Test
    void garbageAnswersAreDownAndTripTheBreakerWhichThenAnswersInstantly() {
        mode = Mode.GARBAGE;
        for (int i = 0; i < 3; i++) {
            StudioArranger.Arrangement a = studio.arrange("seed:e0001" + i, "jazz", true);
            assertThat(a.status()).isEqualTo(StudioArranger.Status.DOWN);
            assertThat(a.note()).contains("garbage");
            assertThat(a.url()).isNull();                         // a bad key is never turned into a URL
        }
        assertThat(studio.breaker().state()).isEqualTo(CircuitBreaker.State.OPEN);
        int before = arranges.get();
        long t0 = System.nanoTime();
        assertThat(studio.arrange("seed:e00099", "rock", false).note()).contains("down");
        assertThat((System.nanoTime() - t0) / 1_000_000).isLessThan(50);
        assertThat(arranges.get()).isEqualTo(before);             // nothing went out
        assertThat(studio.health().get("state")).isEqualTo("DOWN");

        mode = Mode.NORMAL;                                        // the studio recovers
        now.addAndGet(10_001);
        assertThat(studio.breaker().state()).isEqualTo(CircuitBreaker.State.HALF_OPEN);
        assertThat(studio.arrange("seed:e00015", "jazz", true).available()).isTrue();   // the probe
        assertThat(studio.breaker().state()).isEqualTo(CircuitBreaker.State.CLOSED);
    }

    @Test
    void htmlInsteadOfJsonIsGarbageNotACrash() {
        mode = Mode.HTML;
        assertThat(studio.arrange("seed:e00015", "jazz", true).status()).isEqualTo(StudioArranger.Status.DOWN);
    }

    @Test
    void transient502sAreRetriedWithBoundedJitteredBackoff() {
        mode = Mode.FLAKY_502;
        assertThat(studio.arrange("seed:e00015", "jazz", true).available()).isTrue();
        assertThat(arranges.get()).isEqualTo(3);
        assertThat(sleeps).hasSize(2);
        assertThat(sleeps.get(0)).isBetween(20L, 60L);             // 40 ms ± 50 %
        assertThat(sleeps.get(1)).isBetween(40L, 120L);            // 80 ms ± 50 %
    }

    @Test
    void persistent502sGiveUpAfterTheRetryBudget() {
        mode = Mode.ALWAYS_503;
        StudioArranger.Arrangement a = studio.arrange("seed:e00015", "jazz", true);
        assertThat(a.status()).isEqualTo(StudioArranger.Status.DOWN);
        assertThat(a.note()).contains("502");
        assertThat(arranges.get()).isEqualTo(3);                   // 1 + 2 retries, then stop
    }

    @Test
    void anUnreachableStudioIsDownNeverAnErrorAndNeverHangs() {
        server.stop(0);
        long t0 = System.nanoTime();
        HttpStudioArranger gone = studio(FAST);
        assertThat(gone.arrange("seed:e00015", "jazz", true).note()).contains("unreachable");
        assertThat(gone.seeds()).isEmpty();
        assertThat(gone.audio(KEY, null)).isEmpty();
        assertThat(gone.coatPng(HASH, 512)).isEmpty();
        assertThat(gone.coat(HASH)).isEmpty();
        assertThat(gone.health().get("state")).isIn("DOWN", "DEGRADED");
        assertThat((System.nanoTime() - t0) / 1_000_000).isLessThan(3000);
    }

    // ------------------------------------------------------------------ audio + coats

    @Test
    void seedsAndAudioAreRelayedOnlyForWellFormedRequestsWithETags() throws IOException {
        assertThat(studio.seeds()).containsExactly("e00015", "e00084", "e00165", "e00153", "e00601", "e02014");  // r4 /health lists none
        HttpStudioArranger.Upstream up = studio.audio(KEY, null).orElseThrow();
        assertThat(new String(up.body().readAllBytes())).isEqualTo("ID3audio");
        assertThat(up.etag()).isEqualTo("\"sha-abc\"");
        assertThat(up.contentType()).isEqualTo("audio/mpeg");
        assertThat(up.cacheControl()).contains("immutable");
        assertThat(studio.audio(KEY, "\"sha-abc\"").orElseThrow().status()).isEqualTo(304);
        assertThat(studio.audio("../../etc/passwd", null)).isEmpty();
        assertThat(studio.audio(KEY + "\r\nX: y", null)).isEmpty();
    }

    @Test
    void coatPngsAreValidatedAndCached() {
        assertThat(studio.coatPng(HASH, 512)).hasValueSatisfying(b -> assertThat(HttpStudioArranger.isPng(b, 512)).isTrue());
        assertThat(studio.coatPng(HASH, 512)).isPresent();
        assertThat(coatHits.get()).isEqualTo(1);                   // cached per engine + hash + size
        assertThat(studio.coatPng(HASH, 77)).isEmpty();
        assertThat(studio.coatPng("0x12", 512)).isEmpty();
        assertThat(studio.coatPng(HASH.toUpperCase(), 512)).isEmpty();
    }

    @Test
    void badCoatImagesFallBackToTheGeneratedCoat() {
        mode = Mode.BAD_PNG;
        assertThat(studio.coatPng(HASH, 512)).isEmpty();
        mode = Mode.WRONG_SIZE_PNG;
        assertThat(studio.coatPng(HASH, 1024)).isEmpty();
        mode = Mode.HUGE_PNG;
        assertThat(studio.coatPng(HASH, 256)).isEmpty();
        mode = Mode.GARBAGE_COAT;
        assertThat(studio.coat(HASH)).isEmpty();
        mode = Mode.NORMAL;
        assertThat(studio.coat(HASH)).contains("{\"kind\":\"spots\"}");
    }

    @Test
    void theStudioUrlMustBeHttp() {
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> new HttpStudioArranger("file:///etc", () -> 0))
                .isInstanceOf(IllegalArgumentException.class);
    }

    // ------------------------------------------------------------------ rd-studio r4 (CHANGES_FOR_FLEX.md)

    @Test
    void r4TokenOneIsQueuedWithItsJobAndRetryAfter() {
        StudioArranger.Arrangement a = studio.arrange("token:1", "original", false);
        assertThat(a.status()).isEqualTo(StudioArranger.Status.RENDERING);
        assertThat(a.jobId()).isEqualTo("6b8ed8d1f32f4ec2");
        assertThat(a.retryAfterMs()).isEqualTo(30_000);
    }

    @Test
    void r4RenderOptionsAreSentAndAFlacRenderIsProxiedUnderTheNewKeyShape() {
        StudioArranger.Arrangement a = studio.arrange("seed:e00015", "jazz", true, new StudioArranger.Render("flac", "harman", 57, "off"));
        assertThat(lastArrange).contains("format=flac").contains("preset=harman").contains("vinyl=50").contains("noise=off");
        assertThat(a.url()).isEqualTo("/api/v1/jukebox/studio/audio/e00015__jazz__studio__harman-v50-noff__v6r4-s680199b4.flac");
        studio.arrange("seed:e00015", "jazz", true);
        assertThat(lastArrange).doesNotContain("format=");                          // defaults keep the plain query
    }

    @Test
    void r4RenderOptionsAreValidated() {
        assertThat(new StudioArranger.Render(null, null, 0, null)).isEqualTo(StudioArranger.Render.DEFAULT);
        assertThat(new StudioArranger.Render("FLAC", "Warm", 99, "-45").vinyl()).isEqualTo(90);
        for (Object[] bad : new Object[][]{{"wav", "neutral", 0, "off"}, {"mp3", "loud", 0, "off"}, {"mp3", "neutral", 101, "off"},
                {"mp3", "neutral", -1, "off"}, {"mp3", "neutral", 0, "-20"}, {"mp3", "neutral", 0, "-61"}, {"mp3", "neutral", 0, "on"}})
            org.assertj.core.api.Assertions.assertThatThrownBy(() -> new StudioArranger.Render((String) bad[0], (String) bad[1], (int) bad[2], (String) bad[3]))
                    .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void r4AudioKeyPatternMatchesTheNewShapeOnly() {
        for (String ok : new String[]{KEY, "t00001__original__plain__neutral-v0-noff__v6r4-s680199b4.mp3",
                "e00015__jazz__studio__harman-v50-n45__v6r4-s680199b4.flac"})
            assertThat(HttpStudioArranger.AUDIO_KEY.matcher(ok).matches()).as(ok).isTrue();
        for (String bad : new String[]{"e00015__jazz__studio__v6r4-s66d2a493.mp3", "x00015__jazz__studio__neutral-v0-noff__v.mp3",
                "e00015__jazz__studio__neutral-v0-noff__v6r4.wav", "../e00015__jazz__studio__neutral-v0-noff__v.mp3",
                "e00015__jazz__studio__neutral-v0-noff__v/../../x.mp3"})
            assertThat(HttpStudioArranger.AUDIO_KEY.matcher(bad).matches()).as(bad).isFalse();
    }

    @Test
    void r4FileSeedsAndOutOfRangeTokensNeverReachTheStudio() {
        assertThat(studio.arrange("seed:alpine", "jazz", false).status()).isEqualTo(StudioArranger.Status.ORIGINAL);
        assertThat(studio.arrange("token:50000", "jazz", false).status()).isEqualTo(StudioArranger.Status.ORIGINAL);
        assertThat(studio.arrange("token:01", "jazz", false).status()).isEqualTo(StudioArranger.Status.ORIGINAL);
        assertThat(arranges.get()).isZero();
    }

    @Test
    void r4AFailedQaRenderIsFinalAndNotRetried() {
        mode = Mode.FAILED_QA;
        StudioArranger.Arrangement a = studio.arrange("seed:e00015", "rock", true);
        assertThat(a.status()).isEqualTo(StudioArranger.Status.ORIGINAL);
        assertThat(a.note()).contains("quality check");
        now.addAndGet(HttpStudioArranger.HIT_TTL_MS + 1);
        studio.arrange("seed:e00015", "rock", true);
        assertThat(arranges.get()).isEqualTo(1);
        assertThat(studio.breaker().state()).isEqualTo(CircuitBreaker.State.CLOSED);
    }

    @Test
    void r4A503BacksOffForItsRetryAfterWithTheBreakerOpenThenProbesReady() {
        mode = Mode.BUSY;
        StudioArranger.Arrangement a = studio.arrange("seed:e00015", "jazz", true);
        assertThat(a.status()).isEqualTo(StudioArranger.Status.DOWN);
        assertThat(a.note()).contains("busy");
        assertThat(arranges.get()).isEqualTo(1);                      // 503 is never retried
        assertThat(studio.breaker().state()).isEqualTo(CircuitBreaker.State.OPEN);
        assertThat(studio.arrange("seed:e00084", "rock", true).note()).contains("down");
        assertThat(arranges.get()).isEqualTo(1);
        now.addAndGet(30_001);                                        // Retry-After passed: half open → probe /ready
        readyStatus = 503;
        assertThat(studio.arrange("seed:e00084", "rock", true).note()).contains("busy");
        assertThat(readyHits.get()).isEqualTo(1);
        assertThat(arranges.get()).isEqualTo(1);                      // still busy: no /arrange sent
        now.addAndGet(10_001);
        readyStatus = 200;
        mode = Mode.NORMAL;
        assertThat(studio.arrange("seed:e00015", "jazz", true).available()).isTrue();
        assertThat(studio.breaker().state()).isEqualTo(CircuitBreaker.State.CLOSED);
    }

    @Test
    void r4HealthCarriesEngineCoatEngineQueueAndP95FromMetrics() {
        java.util.Map<String, Object> h = studio.health();
        assertThat(h.get("state")).isEqualTo("UP");
        assertThat(h.get("engine")).isEqualTo("v6r4-s680199b4");
        assertThat(h.get("p95Ms")).isEqualTo(23.5);
        assertThat(h.get("queue")).isEqualTo(3);
    }

    // ------------------------------------------------------------------ r4 Keys tab (rd-voice/1)

    @Test
    void keysVoicesAreRelayedAndCached() {
        assertThat(studio.voices()).get().asString().contains("rd-voice/1").contains("Celesta");
        assertThat(studio.voices()).isPresent();
    }

    @Test
    void keysNoteIsValidatedSentAndItsFileProxiedSameOrigin() throws Exception {
        java.util.Map<String, String> q = new java.util.LinkedHashMap<>();
        q.put("voice", "Celesta"); q.put("midi", "60"); q.put("a", "0.01"); q.put("format", "mp3");
        java.util.Map<String, Object> n = studio.note(q).orElseThrow();
        assertThat(n.get("url")).isEqualTo("/api/v1/jukebox/studio/audio/notes/n0123456789abcdef01234567-v6r4-s60798b99.mp3");
        assertThat(lastArrange).contains("voice=Celesta").contains("midi=60").contains("a=0.01");
        HttpStudioArranger.Upstream up = studio.audio("notes/n0123456789abcdef01234567-v6r4-s60798b99.mp3", null).orElseThrow();
        assertThat(new String(up.body().readAllBytes())).isEqualTo("ID3note");
        assertThat(studio.audio("notes/../../etc/passwd", null)).isEmpty();
        assertThat(studio.audio("notes/n0123.mp3", null)).isEmpty();
    }

    @Test
    void keysNoteParamsOutsideTheSchemaAreRefusedBeforeTheStudio() {
        String[][] bad = {{"midi", "60"}, {"voice", "Celesta"}, {"voice", "Celesta", "midi", "20"}, {"voice", "Celesta", "midi", "60.5"},
                {"voice", "Celesta", "midi", "60", "vel", "2"}, {"voice", "Celesta", "midi", "60", "a", "9"}, {"voice", "<x>", "midi", "60"},
                {"voice", "Celesta", "midi", "60", "format", "wav"}, {"voice", "Celesta", "midi", "60", "gain", "9"},
                {"voice", "Celesta", "midi", "1e3"}, {"voice", "Celesta", "midi", "60", "rr", "16"}};
        int before = arranges.get();
        for (String[] b : bad) {
            java.util.Map<String, String> q = new java.util.LinkedHashMap<>();
            for (int i = 0; i < b.length; i += 2) q.put(b[i], b[i + 1]);
            org.assertj.core.api.Assertions.assertThatThrownBy(() -> HttpStudioArranger.validateNote(q)).as(String.join(",", b))
                    .isInstanceOf(IllegalArgumentException.class);
        }
        assertThat(arranges.get()).isEqualTo(before);
    }
}
