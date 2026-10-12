// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

import static org.assertj.core.api.Assertions.assertThat;

/** Against a fake rd-studio speaking its README's contract. */
class HttpStudioArrangerTest {

    static final String KEY = "e00015__jazz__studio__v6r4-s66d2a493.mp3";
    static final String HASH = "0x19227c7cb7cb2f6f78553007595b21ad35be0258d5f71eb7a467367e6ff19198";
    private HttpServer server;
    private final AtomicInteger arranges = new AtomicInteger();
    private final AtomicLong now = new AtomicLong();
    private HttpStudioArranger studio;

    @BeforeEach
    void start() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", ex -> {
            String q = ex.getRequestURI().toString();
            int status; String body; String type = "application/json";
            if (q.startsWith("/arrange")) {
                arranges.incrementAndGet();
                if (q.contains("seed%3Ae00015") && q.contains("genre=jazz")) {
                    status = 200;
                    body = "{\"url\":\"http://127.0.0.1:8787/audio/" + KEY + "\",\"engine\":\"v6r4-s66d2a493\",\"key\":\"" + KEY + "\",\"note\":\"\"}";
                } else if (q.contains("token%3A")) { status = 404; body = "{\"status\":\"unknown_source\"}"; }
                else { status = 404; body = "{\"status\":\"rendering\"}"; }
            } else if (q.equals("/health")) { status = 200; body = "{\"ok\":true,\"seeds\":[\"e00015\",\"e00084\",\"../x\"]}"; }
            else if (q.equals("/audio/" + KEY)) { status = 200; body = "ID3audio"; type = "audio/mpeg"; }
            else if (q.startsWith("/coat.png?hash=" + HASH)) { status = 200; body = "PNG"; type = "image/png"; }
            else if (q.startsWith("/coat?hash=" + HASH)) { status = 200; body = "{\"kind\":\"spots\"}"; }
            else { status = 404; body = "{}"; }
            byte[] b = body.getBytes(StandardCharsets.UTF_8);
            ex.getResponseHeaders().set("Content-Type", type);
            ex.sendResponseHeaders(status, b.length);
            ex.getResponseBody().write(b);
            ex.close();
        });
        server.start();
        studio = new HttpStudioArranger("http://127.0.0.1:" + server.getAddress().getPort() + "/", now::get);
    }

    @AfterEach
    void stop() { server.stop(0); }

    @Test
    void a200BecomesAnAvailableArrangementServedThroughTheRealm() {
        StudioArranger.Arrangement a = studio.arrange("seed:e00015", "jazz", true);
        assertThat(a.available()).isTrue();
        assertThat(a.url()).isEqualTo("/api/v1/jukebox/studio/audio/" + KEY);    // never the studio's own host
        assertThat(a.note()).contains("jazz").contains("studio");
    }

    @Test
    void a404PlaysTheOriginalAndSaysWhy() {
        StudioArranger.Arrangement token = studio.arrange("token:5", "rock", false);
        assertThat(token.available()).isFalse();
        assertThat(token.url()).isNull();
        assertThat(token.note()).contains("original");
        assertThat(studio.arrange("seed:e00084", "reggae", true).note()).contains("rendering");
    }

    @Test
    void answersAreCachedHitsLongMissesBriefly() {
        studio.arrange("seed:e00015", "jazz", true);
        studio.arrange("seed:e00015", "jazz", true);
        studio.arrange("seed:e00084", "reggae", true);
        studio.arrange("seed:e00084", "reggae", true);
        assertThat(arranges.get()).isEqualTo(2);
        now.addAndGet(HttpStudioArranger.MISS_TTL_MS + 1);
        studio.arrange("seed:e00084", "reggae", true);      // a render may have finished: ask again
        studio.arrange("seed:e00015", "jazz", true);        // a hit stays cached
        assertThat(arranges.get()).isEqualTo(3);
    }

    @Test
    void anUnreachableStudioIsNeverAnError() {
        server.stop(0);
        HttpStudioArranger gone = new HttpStudioArranger("http://127.0.0.1:" + server.getAddress().getPort(), () -> 0);
        assertThat(gone.arrange("seed:e00015", "jazz", true).note()).contains("unreachable");
        assertThat(gone.seeds()).isEmpty();
        assertThat(gone.audio(KEY)).isEmpty();
    }

    @Test
    void seedsAudioAndCoatsAreRelayedOnlyForWellFormedRequests() throws IOException {
        assertThat(studio.seeds()).containsExactly("e00015", "e00084");       // "../x" dropped
        assertThat(new String(studio.audio(KEY).orElseThrow().readAllBytes())).isEqualTo("ID3audio");
        assertThat(studio.audio("../../etc/passwd")).isEmpty();
        assertThat(studio.coatPng(HASH, 512)).isPresent();
        assertThat(studio.coatPng(HASH, 77)).isEmpty();
        assertThat(studio.coatPng("0x12", 512)).isEmpty();
        assertThat(studio.coat(HASH)).contains("{\"kind\":\"spots\"}");
    }
}
