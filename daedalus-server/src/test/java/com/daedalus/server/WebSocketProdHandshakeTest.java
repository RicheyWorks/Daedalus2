// SPDX-License-Identifier: MIT

package com.daedalus.server;

import com.daedalus.server.security.JwtTokenService;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.messaging.simp.stomp.StompHeaders;
import org.springframework.messaging.simp.stomp.StompSession;
import org.springframework.messaging.simp.stomp.StompSessionHandlerAdapter;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.client.RestTestClient;
import org.springframework.web.socket.WebSocketHttpHeaders;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.messaging.WebSocketStompClient;
import org.springframework.web.socket.sockjs.client.SockJsClient;
import org.springframework.web.socket.sockjs.client.WebSocketTransport;

import java.util.List;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The composition the signed-in web UI needs in prod: a browser can open SockJS
 * without an HTTP bearer header, and STOMP {@code CONNECT} is still the gate.
 *
 * <p>Closing {@code /ws/**} looked like defence in depth and made the page we ship
 * unable to attach a principal — {@code new SockJS("/ws")} cannot set
 * {@code Authorization}. Opening the handshake without keeping {@code CONNECT}
 * required would be the other half of the same bug.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "daedalus.security.jwt.secret=prod-ws-handshake-secret-32-bytes!!",
        "daedalus.security.admin.password-bcrypt="
                + "$2a$10$7EqJtq98hPqEX7fNZaFWoOhi5B0h6C1JcqIcnLmVjKobXAB9Zwmqu",
        "daedalus.redis.enabled=false",
        "daedalus.plugins.scan-on-startup=false",
})
@ActiveProfiles("prod")
class WebSocketProdHandshakeTest {

    private static final long TIMEOUT_S = 10;

    @LocalServerPort
    private int port;

    @Autowired
    private JwtTokenService tokenService;

    private WebSocketStompClient client;
    private StompSession session;

    @BeforeEach
    void createClient() {
        client = new WebSocketStompClient(
                new SockJsClient(List.of(new WebSocketTransport(new StandardWebSocketClient()))));
    }

    @AfterEach
    void tearDown() {
        if (session != null && session.isConnected()) {
            session.disconnect();
        }
        client.stop();
    }

    private String wsUrl() {
        return "http://localhost:" + port + "/ws";
    }

    @Test
    void sockJsInfoIsPublicSoABrowserCanUpgrade() {
        RestTestClient http = RestTestClient.bindToServer()
                .baseUrl("http://localhost:" + port).build();
        byte[] body = http.get().uri("/ws/info").exchange()
                .expectStatus().isOk()
                .expectBody().returnResult().getResponseBody();
        assertThat(body).isNotNull();
        assertThat(new String(body)).contains("websocket");
    }

    @Test
    void connectWithoutATokenIsStillRefused() {
        assertThatThrownBy(() -> client.connectAsync(wsUrl(), new StompSessionHandlerAdapter() { })
                        .get(TIMEOUT_S, TimeUnit.SECONDS))
                .as("prod CONNECT without a bearer token must not yield a session")
                .isInstanceOf(Exception.class);
    }

    @Test
    void connectWithAValidTokenSucceedsAfterAPublicHandshake() throws Exception {
        StompHeaders connectHeaders = new StompHeaders();
        connectHeaders.add("Authorization", "Bearer " + tokenService.issue("operator").token());
        session = client.connectAsync(wsUrl(), (WebSocketHttpHeaders) null, connectHeaders,
                new StompSessionHandlerAdapter() { }).get(TIMEOUT_S, TimeUnit.SECONDS);
        assertThat(session.isConnected()).isTrue();
    }
}
