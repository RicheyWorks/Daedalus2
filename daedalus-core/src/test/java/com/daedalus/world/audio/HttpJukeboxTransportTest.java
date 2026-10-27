// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** Real HTTP transport against a loopback stand-in server; no outside network is touched. */
class HttpJukeboxTransportTest {
    private HttpServer server;
    private String base;
    private final CountDownLatch release = new CountDownLatch(1);

    @BeforeEach
    void start() throws IOException {
        server = HttpServer.create(new InetSocketAddress(InetAddress.getLoopbackAddress(), 0), 0);
        server.setExecutor(Executors.newCachedThreadPool());
        server.createContext("/api/v1/jukebox/seeds", ex -> reply(ex, 200, "a.mid\nb.mid".getBytes(StandardCharsets.UTF_8)));
        server.createContext("/ok", ex -> reply(ex, 200, "seeds:3".getBytes(StandardCharsets.UTF_8)));
        server.createContext("/binary", ex -> reply(ex, 200, new byte[] {0, 1, (byte) 0xff, 0x7f}));
        server.createContext("/empty", ex -> {
            ex.sendResponseHeaders(204, -1);
            ex.close();
        });
        server.createContext("/missing", ex -> reply(ex, 404, "no such seed".getBytes(StandardCharsets.UTF_8)));
        server.createContext("/boom", ex -> reply(ex, 500, "oops".getBytes(StandardCharsets.UTF_8)));
        server.createContext("/slow", ex -> {
            try {
                release.await(5, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            reply(ex, 200, new byte[] {1});
        });
        server.start();
        base = "http://127.0.0.1:" + server.getAddress().getPort();
    }

    @AfterEach
    void stop() {
        release.countDown();
        server.stop(0);
    }

    private static void reply(com.sun.net.httpserver.HttpExchange ex, int status, byte[] body) throws IOException {
        ex.sendResponseHeaders(status, body.length);
        try (OutputStream os = ex.getResponseBody()) {
            os.write(body);
        }
    }

    private static HttpJukeboxTransport transport(long ms) {
        return new HttpJukeboxTransport(Duration.ofMillis(ms));
    }

    @Test
    void successReturnsStatusAndExactBytes() throws IOException {
        JukeboxTransport.Response r = transport(2000).get(base + "/ok");
        assertThat(r.status()).isEqualTo(200);
        assertThat(new String(r.body(), StandardCharsets.UTF_8)).isEqualTo("seeds:3");
        assertThat(transport(2000).get(base + "/binary").body()).containsExactly(0, 1, (byte) 0xff, 0x7f);
        assertThat(transport(2000).get(base + "/empty").body()).isEmpty();
    }

    @Test
    void errorStatusesArePassedThroughNotThrown() throws IOException {
        JukeboxTransport.Response missing = transport(2000).get(base + "/missing");
        assertThat(missing.status()).isEqualTo(404);
        assertThat(new String(missing.body(), StandardCharsets.UTF_8)).isEqualTo("no such seed");
        assertThat(transport(2000).get(base + "/boom").status()).isEqualTo(500);
        assertThat(transport(2000).get(base + "/nowhere").status()).isEqualTo(404);
    }

    @Test
    void slowServerTimesOutAsIoException() {
        long t0 = System.nanoTime();
        assertThatThrownBy(() -> transport(200).get(base + "/slow")).isInstanceOf(IOException.class);
        assertThat(Duration.ofNanos(System.nanoTime() - t0)).isLessThan(Duration.ofSeconds(4));
    }

    @Test
    void truncatedBodyIsAnIoExceptionNotAShortResponse() throws Exception {
        try (ServerSocket raw = new ServerSocket(0, 1, InetAddress.getLoopbackAddress())) {
            Thread t = new Thread(() -> {
                try (java.net.Socket sock = raw.accept()) {
                    sock.getInputStream().read(new byte[4096]);
                    OutputStream os = sock.getOutputStream();
                    os.write("HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n0123456789".getBytes(StandardCharsets.US_ASCII));
                    os.flush();
                } catch (IOException ignored) {
                    // the client side is what we test
                }
            });
            t.setDaemon(true);
            t.start();
            assertThatThrownBy(() -> transport(2000).get("http://127.0.0.1:" + raw.getLocalPort() + "/seed.mid"))
                    .isInstanceOf(IOException.class);
        }
    }

    @Test
    void garbageStatusLineIsAnIoException() throws Exception {
        try (ServerSocket raw = new ServerSocket(0, 1, InetAddress.getLoopbackAddress())) {
            Thread t = new Thread(() -> {
                try (java.net.Socket sock = raw.accept()) {
                    sock.getInputStream().read(new byte[4096]);
                    sock.getOutputStream().write("NOT-HTTP garbage\r\n\r\n".getBytes(StandardCharsets.US_ASCII));
                } catch (IOException ignored) {
                    // the client side is what we test
                }
            });
            t.setDaemon(true);
            t.start();
            assertThatThrownBy(() -> transport(2000).get("http://127.0.0.1:" + raw.getLocalPort() + "/x"))
                    .isInstanceOf(IOException.class);
        }
    }

    @Test
    void refusedConnectionIsAnIoException() throws IOException {
        int port;
        try (ServerSocket s = new ServerSocket(0, 1, InetAddress.getLoopbackAddress())) {
            port = s.getLocalPort();
        }
        assertThatThrownBy(() -> transport(1000).get("http://127.0.0.1:" + port + "/ok")).isInstanceOf(IOException.class);
    }

    @Test
    void badUrlIsRejectedBeforeAnyNetwork() {
        assertThatThrownBy(() -> transport(1000).get("not a url")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void interruptedCallerGetsIoExceptionAndKeepsTheFlag() {
        Thread.currentThread().interrupt();
        try {
            assertThatThrownBy(() -> transport(2000).get(base + "/ok")).isInstanceOf(IOException.class);
            assertThat(Thread.currentThread().isInterrupted()).isTrue();
        } finally {
            Thread.interrupted();
        }
    }

    @Test
    void worksBehindTheJukeboxClient() throws IOException {
        JukeboxClient c = new JukeboxClient(base, transport(2000), 0, 3);
        assertThat(c.seeds()).isEqualTo("a.mid\nb.mid");
        assertThat(new JukeboxTransport.Response(200, null).body()).isEmpty();
    }
}
