// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox.radio;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.URI;
import java.time.Duration;
import java.util.concurrent.Executors;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The relay can't be turned into an SSRF / open proxy, and every stream is bounded. */
class RadioRelayTest {

    private HttpServer server;
    private String base;

    /** Our fake station on loopback is allowed; every other URL (incl. redirect targets) goes through the real guard. */
    private UrlCheck guard() {
        RelayGuard real = new RelayGuard();
        return url -> url.startsWith(base) ? URI.create(url) : real.check(url);
    }

    private RadioRelay relay(RadioRelay.Limits l) { return new RadioRelay(guard(), l); }

    private static RadioRelay.Limits limits(long maxBytes, Duration idle) {
        return new RadioRelay.Limits(4, 2, Duration.ofSeconds(30), maxBytes, idle, Duration.ofSeconds(2));
    }

    @BeforeEach
    void start() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.setExecutor(Executors.newCachedThreadPool());
        server.createContext("/", ex -> {
            String p = ex.getRequestURI().getPath();
            try {
                switch (p) {
                    case "/ok" -> { ex.getResponseHeaders().set("Content-Type", "audio/mpeg"); ex.sendResponseHeaders(200, 0);
                        try (OutputStream o = ex.getResponseBody()) { o.write(new byte[100_000]); } }
                    case "/html" -> { ex.getResponseHeaders().set("Content-Type", "text/html"); ex.sendResponseHeaders(200, 5);
                        ex.getResponseBody().write("<html".getBytes()); }
                    case "/pls" -> { ex.getResponseHeaders().set("Content-Type", "audio/x-scpls"); ex.sendResponseHeaders(200, 0);
                        ex.getResponseBody().write("[playlist]".getBytes()); }
                    case "/metadata" -> redirect(ex, "http://169.254.169.254/latest/meta-data/");
                    case "/private" -> redirect(ex, "http://10.0.0.5:8000/stream");
                    case "/v6" -> redirect(ex, "http://[::1]:8000/");
                    case "/file" -> redirect(ex, "file:///etc/passwd");
                    case "/hop" -> redirect(ex, base + "/ok");
                    case "/loop" -> redirect(ex, base + "/loop");
                    case "/dead" -> ex.sendResponseHeaders(404, -1);
                    case "/stall" -> { ex.getResponseHeaders().set("Content-Type", "audio/ogg"); ex.sendResponseHeaders(200, 0);
                        ex.getResponseBody().write(new byte[10]); ex.getResponseBody().flush(); Thread.sleep(10_000); }
                    default -> ex.sendResponseHeaders(500, -1);
                }
            } catch (InterruptedException | IOException e) {
                // the relay hung up on us (stall / cap tests)
            }
            ex.close();
        });
        server.start();
        base = "http://127.0.0.1:" + server.getAddress().getPort();
    }

    private static void redirect(com.sun.net.httpserver.HttpExchange ex, String to) throws IOException {
        ex.getResponseHeaders().set("Location", to);
        ex.sendResponseHeaders(302, -1);
    }

    @AfterEach
    void stop() { server.stop(0); }

    @Test
    void relaysAudioAndFollowsASafeRedirect() throws Exception {
        RadioRelay r = relay(limits(1 << 20, Duration.ofSeconds(5)));
        RadioRelay.Opened o = r.open(base + "/hop");
        assertThat(o.contentType()).isEqualTo("audio/mpeg");
        assertThat(r.pipe(o.body(), new ByteArrayOutputStream())).isEqualTo(100_000);
    }

    @Test
    void redirectsIntoPrivateSpaceOrOtherSchemesAreRefused() {
        RadioRelay r = relay(limits(1 << 20, Duration.ofSeconds(5)));
        for (String p : new String[]{"/metadata", "/private", "/v6", "/file"})
            assertThatThrownBy(() -> r.open(base + p)).as(p).isInstanceOf(RadioRelay.OffAir.class).hasMessageContaining("refused");
        assertThatThrownBy(() -> r.open(base + "/loop")).hasMessageContaining("too many redirects");
    }

    @Test
    void onlyAudioIsRelayedAndDeadStationsAreOffTheAir() {
        RadioRelay r = relay(limits(1 << 20, Duration.ofSeconds(5)));
        assertThatThrownBy(() -> r.open(base + "/html")).isInstanceOf(RadioRelay.OffAir.class);
        assertThatThrownBy(() -> r.open(base + "/dead")).isInstanceOf(RadioRelay.OffAir.class);
        assertThatThrownBy(() -> r.open("http://127.0.0.1:1/x")).isInstanceOf(RadioRelay.OffAir.class);   // real guard: loopback
    }

    @Test
    void theByteCapEndsTheStream() throws Exception {
        RadioRelay r = relay(limits(1_000, Duration.ofSeconds(5)));
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        assertThat(r.pipe(r.open(base + "/ok").body(), out)).isEqualTo(1_000);
        assertThat(out.size()).isEqualTo(1_000);
    }

    @Test
    void aStalledUpstreamIsCutAfterTheIdleCap() throws Exception {
        RadioRelay r = relay(limits(1 << 20, Duration.ofSeconds(1)));
        long t0 = System.nanoTime();
        long n = r.pipe(r.open(base + "/stall").body(), new ByteArrayOutputStream());
        assertThat(n).isEqualTo(10);
        assertThat((System.nanoTime() - t0) / 1_000_000).isLessThan(4_000);
    }

    @Test
    void concurrencyIsCappedGloballyAndPerListener() {
        RadioRelay r = relay(limits(1, Duration.ofSeconds(1)));     // 4 slots, 2 per listener
        assertThat(r.acquire("a")).isTrue();
        assertThat(r.acquire("a")).isTrue();
        assertThat(r.acquire("a")).isFalse();
        assertThat(r.acquire("b")).isTrue();
        assertThat(r.acquire("c")).isTrue();
        assertThat(r.acquire("d")).isFalse();                       // global cap
        r.release("a");
        assertThat(r.acquire("d")).isTrue();
        assertThat(r.available()).isZero();
    }

    // ------------------------------------------------------------------ the guard on its own

    @Test
    void theGuardRefusesEveryNonPublicAddressFamily() throws Exception {
        String[] refused = {"127.0.0.1", "127.8.9.1", "0.0.0.0", "10.1.2.3", "172.16.0.1", "172.31.255.255", "192.168.1.1",
                "169.254.169.254", "100.64.0.1", "100.127.255.254", "192.0.0.8", "192.0.2.1", "198.18.0.1", "198.51.100.7",
                "203.0.113.9", "224.0.0.1", "240.0.0.1", "255.255.255.255", "::1", "::", "fe80::1", "fc00::1", "fd12:3456::1",
                "fec0::1", "ff02::1", "2001:db8::1", "::ffff:10.0.0.1", "::ffff:127.0.0.1", "::10.0.0.1", "2002:0a00:0001::1",
                "64:ff9b::a9fe:a9fe"};
        for (String a : refused) assertThat(RelayGuard.isPublic(InetAddress.getByName(a))).as(a).isFalse();
        String[] allowed = {"8.8.8.8", "1.1.1.1", "93.184.216.34", "172.32.0.1", "100.128.0.1", "2606:4700:4700::1111",
                "2002:0808:0808::1", "::ffff:8.8.8.8"};
        for (String a : allowed) assertThat(RelayGuard.isPublic(InetAddress.getByName(a))).as(a).isTrue();
    }

    @Test
    void theGuardRefusesBadUrlsAndHostsThatResolvePrivately() throws Exception {
        RelayGuard g = new RelayGuard(h -> switch (h) {
            case "radio.example" -> new InetAddress[]{InetAddress.getByName("93.184.216.34")};
            case "rebind.example" -> new InetAddress[]{InetAddress.getByName("93.184.216.34"), InetAddress.getByName("10.0.0.1")};
            default -> throw new java.net.UnknownHostException(h);
        });
        assertThat(g.check("http://radio.example/stream").getHost()).isEqualTo("radio.example");
        assertThat(g.check("https://radio.example:8443/s").getPort()).isEqualTo(8443);
        String[] bad = {"ftp://radio.example/", "file:///etc/passwd", "gopher://radio.example/", "http://user:pw@radio.example/",
                "http://radio.example:22/", "http://radio.example:25/", "http://localhost/", "http://foo.localhost/",
                "http://metadata.google.internal/", "http://printer.local/", "http://rebind.example/", "http://nowhere.example/",
                "http:///nohost", "not a url", "javascript:alert(1)", "http://127.0.0.1/", "http://[::1]/", "http://2130706433/"};
        for (String u : bad) assertThatThrownBy(() -> g.check(u)).as(u).isInstanceOf(RelayGuard.Refused.class);
    }

    @Test
    void theFakeIpAllowanceIsOptInAndOnlyForDnsNames() throws Exception {
        RelayGuard.Resolver dns = h -> new java.net.InetAddress[]{java.net.InetAddress.getByName(h.equals("radio.example") ? "198.18.0.1" : h)};
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> new RelayGuard(dns).check("http://radio.example/s"))
                .hasMessageContaining("non-public");                                        // default: refused
        RelayGuard fake = new RelayGuard(dns, "198.18.0.0/15");
        org.assertj.core.api.Assertions.assertThat(fake.check("http://radio.example/s").getHost()).isEqualTo("radio.example");
        for (String bad : new String[]{"http://198.18.0.1/s", "http://127.0.0.1/s", "http://169.254.169.254/latest", "http://10.0.0.1/"})
            org.assertj.core.api.Assertions.assertThatThrownBy(() -> fake.check(bad)).as(bad).hasMessageContaining("non-public");
        for (String bad : new String[]{"0.0.0.0/0", "10.0.0.0/4", "fe80::/10", "198.18.0.0", "300.1.1.1/16"})
            org.assertj.core.api.Assertions.assertThatThrownBy(() -> new RelayGuard(dns, bad)).as(bad).isInstanceOf(IllegalArgumentException.class);
    }
}
