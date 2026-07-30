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
import org.springframework.messaging.simp.stomp.StompCommand;
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
import java.util.ArrayList;
import java.util.Collections;
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
 * actually installed in the inbound channel, and its refusal reaches a real client rather than
 * vanishing server-side. One positive path (the owner receives frames)
 * guards against the failure mode where the rule is installed but refuses everyone.
 *
 * <p>Same async discipline as {@code WebSocketSmokeTest}: no receipts exist on the simple
 * broker, so the positive tests republish their idempotent event until the first frame arrives.
 * Refusals are awaited via {@link ErrorFrameLatch}, which trips on any of the ways the client
 * can observe one — see its Javadoc for why waiting on the ERROR frame alone was flaky — and are
 * then confirmed by the stronger property that no frame ever reaches the refused subscriber.
 * Never {@code Thread.sleep}.
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

    /**
     * Latches the refusal of a subscription, however the client learns of it.
     *
     * <p><b>Why "however".</b> The server refuses by sending a STOMP ERROR frame and then
     * closing the socket, and those two are racing: the earlier version of this test awaited the
     * ERROR frame alone and failed roughly one run in three with
     * {@code ConnectionLostException: Connection closed} — the close had overtaken the frame.
     * That is not a flaky server, it is a test asserting on one of two legitimate outcomes. Both
     * mean refused; only one is polite about it. So this latch trips on the ERROR frame, on a
     * conversion failure while reading it, or on the transport dying, and records which happened
     * so a failure says what was observed instead of {@code expected true but was false}.
     *
     * <p>Accepting a bare close would weaken the assertion on its own, so the refusal tests pair
     * it with a stronger one: the refused subscriber must receive <em>no frames</em> while the
     * owner's events are being published. Removing the interceptor breaks both — the subscription
     * would be accepted, the socket would stay open, and the frames would arrive.
     */
    private static final class ErrorFrameLatch extends StompSessionHandlerAdapter {
        private final CountDownLatch errored = new CountDownLatch(1);
        private final List<String> observed = Collections.synchronizedList(new ArrayList<>());

        @Override
        public void handleFrame(StompHeaders headers, Object payload) {
            observed.add("ERROR frame: " + headers.getFirst("message"));
            errored.countDown();
        }

        @Override
        public void handleException(StompSession s, StompCommand command, StompHeaders headers,
                                    byte[] payload, Throwable ex) {
            observed.add("handleException on " + command + ": " + ex);
            errored.countDown();
        }

        @Override
        public void handleTransportError(StompSession s, Throwable ex) {
            observed.add("transport error: " + ex);
            errored.countDown();
        }

        String diagnosis() {
            return observed.isEmpty() ? "nothing at all was observed" : observed.toString();
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

    /**
     * Publish the owner's move repeatedly and report that the refused subscriber saw none of it.
     * The positive tests need up to {@code TIMEOUT_S} of republishing to catch a frame, so this
     * is the same broker being hammered the same way — with the queue required to stay empty.
     */
    private boolean nothingLeaksTo(BlockingQueue<MoveFrame> received, GameSession game)
            throws InterruptedException {
        PlayerMovedEvent move =
                new PlayerMovedEvent(this, game.id(), new Point(0, 0), new Point(1, 0));
        for (int i = 0; i < 8; i++) {
            events.publishEvent(move);
            if (received.poll(125, TimeUnit.MILLISECONDS) != null) {
                return false;
            }
        }
        return true;
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
        BlockingQueue<MoveFrame> received = subscribeToPlayerTopic(s, game);

        assertThat(mallory.errored.await(TIMEOUT_S, TimeUnit.SECONDS))
                .as("a valid but non-owner token must be refused; observed: %s",
                        mallory.diagnosis())
                .isTrue();
        assertThat(nothingLeaksTo(received, game))
                .as("Mallory was refused but still received a frame from Alice's session")
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
        BlockingQueue<MoveFrame> received = subscribeToPlayerTopic(s, game);

        assertThat(anon.errored.await(TIMEOUT_S, TimeUnit.SECONDS))
                .as("an anonymous connection must be refused on an owned session's topic; "
                        + "observed: %s", anon.diagnosis())
                .isTrue();
        assertThat(nothingLeaksTo(received, game))
                .as("the anonymous subscriber was refused but still received a frame")
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
