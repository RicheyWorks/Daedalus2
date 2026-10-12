// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class HttpJsonRpcTest {

    private HttpServer server;
    private final Deque<Object[]> answers = new ArrayDeque<>();   // {status, body}
    private String lastBody;

    private HttpJsonRpc start() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", ex -> {
            lastBody = new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            Object[] a = answers.isEmpty() ? new Object[]{500, "{}"} : answers.poll();
            byte[] b = ((String) a[1]).getBytes(StandardCharsets.UTF_8);
            ex.sendResponseHeaders((int) a[0], b.length);
            ex.getResponseBody().write(b);
            ex.close();
        });
        server.start();
        return new HttpJsonRpc("http://127.0.0.1:" + server.getAddress().getPort() + "/", 1, sleeps::add);
    }

    private final List<Long> sleeps = new java.util.ArrayList<>();

    private static HttpServer serve(int status, String body, String retryAfter, java.util.concurrent.atomic.AtomicInteger hits) throws IOException {
        HttpServer s = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        s.createContext("/", ex -> {
            hits.incrementAndGet();
            ex.getRequestBody().readAllBytes();
            if (retryAfter != null) ex.getResponseHeaders().set("Retry-After", retryAfter);
            byte[] b = body.getBytes(StandardCharsets.UTF_8);
            ex.sendResponseHeaders(status, b.length);
            ex.getResponseBody().write(b);
            ex.close();
        });
        s.start();
        return s;
    }

    @Test
    void aRateLimitedEndpointFailsOverToTheNextAndHonorsRetryAfter() throws IOException {
        var limitedHits = new java.util.concurrent.atomic.AtomicInteger();
        var okHits = new java.util.concurrent.atomic.AtomicInteger();
        HttpServer limited = serve(429, "{}", "2", limitedHits);
        HttpServer ok = serve(200, "{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":\"0x10\"}", null, okHits);
        try {
            HttpJsonRpc rpc = new HttpJsonRpc("http://127.0.0.1:" + limited.getAddress().getPort() + ", http://127.0.0.1:"
                    + ok.getAddress().getPort(), 1, sleeps::add);
            assertThat(rpc.call("eth_blockNumber").asText()).isEqualTo("0x10");
            assertThat(sleeps).containsExactly(2000L);            // Retry-After: 2 beat the 1 ms backoff
            assertThat(rpc.call("eth_blockNumber").asText()).isEqualTo("0x10");
            assertThat(limitedHits.get()).isEqualTo(1);            // failover is sticky
            assertThat(okHits.get()).isEqualTo(2);
        } finally {
            limited.stop(0);
            ok.stop(0);
        }
    }

    @Test
    void aDeadEndpointFailsOverAndEveryEndpointDownGivesUpAfterABoundedNumberOfAttempts() throws IOException {
        var hits = new java.util.concurrent.atomic.AtomicInteger();
        HttpServer ok = serve(200, "{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":[]}", null, hits);
        try {
            HttpJsonRpc rpc = new HttpJsonRpc("http://127.0.0.1:1/,http://127.0.0.1:" + ok.getAddress().getPort(), 1, sleeps::add);
            assertThat(rpc.call("eth_getLogs").isArray()).isTrue();
        } finally {
            ok.stop(0);
        }
        HttpJsonRpc dead = new HttpJsonRpc("http://127.0.0.1:1/,http://127.0.0.1:2/", 1, sleeps::add);
        sleeps.clear();
        assertThatThrownBy(() -> dead.call("eth_blockNumber")).hasMessageContaining("after 7 attempts");
        assertThat(sleeps).hasSize(7);
        assertThat(sleeps).allSatisfy(ms -> assertThat(ms).isBetween(0L, 10_000L));
    }

    @Test
    void aTooWideLogRangeIsReportedSoTheIndexerCanSplitIt() throws IOException {
        HttpJsonRpc rpc = start();
        answers.add(new Object[]{200, "{\"jsonrpc\":\"2.0\",\"id\":1,\"error\":{\"code\":-32600,\"message\":\"block range is too wide\"}}"});
        assertThatThrownBy(() -> rpc.call("eth_getLogs", java.util.Map.of())).isInstanceOf(JsonRpc.RpcRangeException.class);
        answers.add(new Object[]{400, "bad"});
        assertThatThrownBy(() -> rpc.call("eth_blockNumber")).hasMessageContaining("HTTP 400");
    }

    @Test
    void onlyHttpEndpointsAreAccepted() {
        assertThatThrownBy(() -> new HttpJsonRpc("file:///etc/passwd")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new HttpJsonRpc(" , ")).isInstanceOf(IllegalArgumentException.class);
    }

    @AfterEach
    void stop() { if (server != null) server.stop(0); }

    @Test
    void sendsOneReadOnlyBatchAndMapsResultsByIdWithRevertsAsNull() throws IOException {
        HttpJsonRpc rpc = start();
        answers.add(new Object[]{200, "[{\"id\":1,\"error\":{\"code\":3,\"message\":\"execution reverted\"}},{\"id\":0,\"result\":\"0x01\"}]"});
        assertThat(rpc.ethCallBatch("0xabc", List.of("0x11", "0x22"))).containsExactly("0x01", null);
        assertThat(lastBody).contains("\"method\":\"eth_call\"").contains("\"to\":\"0xabc\"").contains("latest")
                .doesNotContain("eth_send");
    }

    @Test
    void retriesARateLimitThenSucceeds() throws IOException {
        HttpJsonRpc rpc = start();
        answers.add(new Object[]{429, "{\"error\":{\"code\":429}}"});
        answers.add(new Object[]{200, "[{\"id\":0,\"result\":\"0x02\"}]"});
        assertThat(rpc.ethCallBatch("0xabc", List.of("0x11"))).containsExactly("0x02");
    }

    @Test
    void aNodeErrorInsideTheBatchFailsInsteadOfReadingAsNoOwner() throws IOException {
        HttpJsonRpc rpc = start();
        answers.add(new Object[]{200, "[{\"id\":0,\"error\":{\"code\":-32005,\"message\":\"limit exceeded\"}}]"});
        assertThatThrownBy(() -> rpc.ethCallBatch("0xabc", List.of("0x11"))).isInstanceOf(IllegalStateException.class);
        answers.add(new Object[]{200, "{\"jsonrpc\":\"2.0\",\"error\":{\"code\":429}}"});
        assertThatThrownBy(() -> rpc.ethCallBatch("0xabc", List.of("0x11"))).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void anEmptyBatchMakesNoRequest() {
        assertThat(new HttpJsonRpc("http://127.0.0.1:1/").ethCallBatch("0xabc", List.of())).isEmpty();
    }
}
