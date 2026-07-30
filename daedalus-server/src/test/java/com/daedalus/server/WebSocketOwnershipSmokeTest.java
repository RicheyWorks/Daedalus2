// SPDX-License-Identifier: MIT

package com.daedalus.server;

import com.daedalus.api.dto.MoveFrame;
import com.daedalus.model.GameSession;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.PlayerMovedEvent;
import com.daedalus.server.security.JwtTokenService;
import com.daedalus.server.service.GameSessionService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.messaging.simp.stomp.StompFrameHandler;
import org.springframework.messaging.simp.stomp.StompHeaders;
import org.springframework.messaging.simp.stomp.StompSession;
import org.springframework.messaging.simp.stomp.StompSessionHandlerAdapter;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.web.socket.WebSocketHttpHeaders;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.messaging.WebSocketStompClient;
import org.springframework.web.socket.sockjs.client.SockJsClient;
import org.springframework.web.socket.sockjs.client.WebSocketTransport;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.lang.reflect.Type;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * End-to-end proof of the session-ownership STOMP rule (BACKLOG: per-destination
 * authorization), on the harness {@code WebSocketSmokeTest} established.
 *
 * <p>The unit test ({@code StompSubscriptionAuthorizationInterceptorTest}) pins every branch of
 * the decision; this class proves the two things a unit test cannot: the interceptor is
 * actually installed in the inbound channel, and its refusal reaches a real client as a STOMP
 * ERROR frame rather than vanishing server-side. One positive path (the owner receives frames)
 * guards against the failure mode where the rule is installed but refuses everyone.
 *
 * <p>Same async discipline as {@code WebSocketSmokeTest}: no receipts exist on the simple
 * broker, so the positive tests republish their idempotent event until the first frame
 * arrives; refusals are awaited via an ERROR-frame latch ({@code StompSessionHandler#handleFrame
 * receives ERROR frames after CONNECTED}). Never {@code Thread.sleep}.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class WebSocketOwnershipSmokeTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final long TIMEOUT_S = 10;

    @LocalServerPort
    private int port;

    @Autowired
    private ApplicationEventPublisher events;

    @Autowired
    private JwtTokenService tokenService;

    @Autowired
    private GameSessionService sessions;

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
            try {
                session.disconnect();
            } catch (org.springframework.messaging.MessageDeliveryException race) {
                // The refused-subscription tests provoke a server-side ERROR + close;
                // isConnected() can answer true while the socket is already CLOSING, and
                // DISCONNECT then fails. That close IS the behavior under test — a torn
                // teardown must not fail the test that just passed.
            }
        }
        client.stop();
    }

    private String wsUrl() {
        return "http://localhost:" + port + "/ws";
    }

    /** Handler that latches any post-CONNECT ERROR frame the broker sends us. */
    private static final class ErrorFrameLatch extends StompSessionHandlerAdapter {
        private final CountDownLatch errored = new CountDownLatch(1);

        @Override
        public void handleFrame(StompHeaders headers, Object payload) {
            errored.countDown();
        }
    }

    private StompSession connectAs(String subject, ErrorFrameLatch handler) throws Exception {
        StompHeaders connectHeaders = new StompHeaders();
        if (subject != null) {
            connectHeaders.add("Authorization", "Bearer " + tokenService.issue(subject).token());
        }
        session = client.connectAsync(wsUrl(), (WebSocketHttpHeaders) null, connectHeaders,
                handler).get(TIMEOUT_S, TimeUnit.SECONDS);
        return session;
    }

    private BlockingQueue<MoveFrame> subscribeToPlayerTopic(StompSession s, GameSession game) {
        BlockingQueue<MoveFrame> received = new ArrayBlockingQueue<>(64);
        s.subscribe("/topic/session/" + game.id() + "/player", new StompFrameHandler() {
            @Override
            public Type getPayloadType(StompHeaders headers) {
                return byte[].class;
            }

            @Override
            public void handleFrame(StompHeaders headers, Object payload) {
                try {
                    received.offer(MAPPER.readValue((byte[]) payload, MoveFrame.class));
                } catch (IOException e) {
                    throw new UncheckedIOException(e);
                }
            }
        });
        return received;
    }

    /** See WebSocketSmokeTest: no SUBSCRIBE handshake on the simple broker, so republish. */
    private MoveFrame publishUntilReceived(BlockingQueue<MoveFrame> received, PlayerMovedEvent event)
            throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(TIMEOUT_S);
        while (System.nanoTime() < deadline) {
            events.publishEvent(event);
            MoveFrame frame = received.poll(250, TimeUnit.MILLISECONDS);
            if (frame != null) {
                return frame;
            }
        }
        return null;
    }

    @Test
    void theOwnerReceivesTheirSessionsFrames() throws Exception {
        GameSession game = sessions.open(UUID.randomUUID(), "Alice", new Point(0, 0), "alice");
        StompSession s = connectAs("alice", new ErrorFrameLatch());
        BlockingQueue<MoveFrame> received = subscribeToPlayerTopic(s, game);

        MoveFrame frame = publishUntilReceived(received,
                new PlayerMovedEvent(this, game.id(), new Point(0, 0), new Point(1, 0)));

        assertThat(frame).isNotNull();
        assertThat(frame.sessionId()).isEqualTo(game.id());
    }

    @Test
    void anotherSubjectsSubscriptionIsRefusedWithAStompError() throws Exception {
        GameSession game = sessions.open(UUID.randomUUID(), "Alice", new Point(0, 0), "alice");
        ErrorFrameLatch mallory = new ErrorFrameLatch();
        StompSession s = connectAs("mallory", mallory);
        subscribeToPlayerTopic(s, game);

        assertThat(mallory.errored.await(TIMEOUT_S, TimeUnit.SECONDS))
                .as("a valid but non-owner token must be refused with a STOMP ERROR")
                .isTrue();
    }

    @Test
    void anAnonymousConnectionIsRefusedOnAnOwnedSessionsTopic() throws Exception {
        // Advisory profile: connecting without credentials is allowed — but an owned session's
        // feed still is not theirs. This is the pair to the interceptor's forged-token rule:
        // permissive about who may connect, strict about whose frames you may watch.
        GameSession game = sessions.open(UUID.randomUUID(), "Alice", new Point(0, 0), "alice");
        ErrorFrameLatch anon = new ErrorFrameLatch();
        StompSession s = connectAs(null, anon);
        subscribeToPlayerTopic(s, game);

        assertThat(anon.errored.await(TIMEOUT_S, TimeUnit.SECONDS))
                .as("an anonymous connection must be refused on an owned session's topic")
                .isTrue();
    }

    @Test
    void unownedSessionsRemainOpenToAnonymousSubscribers() throws Exception {
        // The dev/desktop posture must keep working: a session opened without credentials has
        // no access claim, so an anonymous subscriber still gets its frames.
        GameSession game = sessions.open(UUID.randomUUID(), "anon", new Point(0, 0));
        StompSession s = connectAs(null, new ErrorFrameLatch());
        BlockingQueue<MoveFrame> received = subscribeToPlayerTopic(s, game);

        MoveFrame frame = publishUntilReceived(received,
                new PlayerMovedEvent(this, game.id(), new Point(0, 0), new Point(1, 0)));

        assertThat(frame).isNotNull();
        assertThat(frame.sessionId()).isEqualTo(game.id());
    }
}
