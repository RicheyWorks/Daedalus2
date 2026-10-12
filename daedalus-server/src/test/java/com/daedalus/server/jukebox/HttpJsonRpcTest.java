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
        return new HttpJsonRpc("http://127.0.0.1:" + server.getAddress().getPort() + "/");
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
