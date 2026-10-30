// SPDX-License-Identifier: MIT

package com.daedalus.server;

import com.daedalus.api.dto.GeneratedFrame;
import com.daedalus.api.dto.MoveFrame;
import com.daedalus.api.dto.MutationFrame;
import com.daedalus.api.dto.PluginFailedFrame;
import com.daedalus.api.dto.SolvedFrame;
import com.daedalus.api.dto.TrafficFrame;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeMetadata;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.MazeGeneratedEvent;
import com.daedalus.plugin.events.MazeMutatedEvent;
import com.daedalus.plugin.events.MazeSolvedEvent;
import com.daedalus.plugin.events.PlayerMovedEvent;
import com.daedalus.plugin.events.PluginFailedEvent;
import com.daedalus.plugin.events.TrafficPulseEvent;
import com.daedalus.server.security.JwtTokenService;
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
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * End-to-end WebSocket/STOMP smoke test — the realtime counterpart of {@link ApplicationSmokeTest}.
 *
 * <h3>Why this exists</h3>
 *
 * <p>Before this test, nothing in the repo constructed a {@code WebSocketStompClient}:
 * {@code WebSocketConfig} was referenced by zero tests, so the endpoint path ({@code /ws} +
 * SockJS), the broker prefixes, and the registration of {@code StompAuthChannelInterceptor}
 * into the inbound channel were all unverified wiring.
 * {@code StompAuthChannelInterceptorTest} proves the interceptor's CONNECT handling in
 * isolation, but only a real connection can prove the interceptor is <em>installed</em>. A
 * starter/framework bump could break the entire realtime path while every slice test stayed
 * green — the same shape as the springdoc incident that motivated the HTTP smoke test.
 *
 * <p>Each frame test publishes the internal Spring {@code ApplicationEvent} rather than calling
 * the controller method, so it exercises the whole chain:
 * event → {@code MazeWebSocketController} bridge → broker → wire → client.
 *
 * <h3>Async caveats</h3>
 *
 * <p>The simple broker processes SUBSCRIBE asynchronously and — unlike a relay to a real
 * broker — never sends RECEIPT frames, so there is no handshake that confirms a subscription
 * is live. Publishing a single event immediately after subscribing would therefore race.
 * Instead each test republishes its (idempotent, synthetic) event in a bounded loop until the
 * first frame arrives, and frames are received through a {@link BlockingQueue} with a timeout.
 * Never {@code Thread.sleep}.
 *
 * <p>The client deliberately receives raw {@code byte[]} payloads and parses JSON with the same
 * Jackson {@code ObjectMapper} the HTTP smoke test uses, rather than registering a STOMP
 * message converter — that keeps the test independent of which converter generation
 * (Jackson 2 vs 3) the framework wires on the server side.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class WebSocketSmokeTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final long TIMEOUT_S = 10;

    @LocalServerPort
    private int port;

    @Autowired
    private ApplicationEventPublisher events;

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

    /** Connects without credentials — allowed because the test profile is non-prod (advisory auth). */
    private StompSession connect() throws Exception {
        session = client.connectAsync(wsUrl(), new StompSessionHandlerAdapter() { })
                .get(TIMEOUT_S, TimeUnit.SECONDS);
        return session;
    }

    private <T> BlockingQueue<T> subscribe(StompSession s, String destination, Class<T> frameType) {
        BlockingQueue<T> received = new ArrayBlockingQueue<>(64);
        s.subscribe(destination, new StompFrameHandler() {
            @Override
            public Type getPayloadType(StompHeaders headers) {
                return byte[].class;
            }

            @Override
            public void handleFrame(StompHeaders headers, Object payload) {
                try {
                    received.offer(MAPPER.readValue((byte[]) payload, frameType));
                } catch (IOException e) {
                    throw new UncheckedIOException(e);
                }
            }
        });
        return received;
    }

    /**
     * Republishes the event until the first frame arrives (see the class javadoc: the simple
     * broker offers no way to know when a SUBSCRIBE has taken effect). Returns {@code null} on
     * timeout so the caller's {@code isNotNull()} assertion produces the failure.
     */
    private <T> T publishUntilReceived(BlockingQueue<T> received, Runnable publish)
            throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(TIMEOUT_S);
        while (System.nanoTime() < deadline) {
            publish.run();
            T frame = received.poll(250, TimeUnit.MILLISECONDS);
            if (frame != null) {
                return frame;
            }
        }
        return null;
    }

    // ------------------------------------------------------------------
    // Connectivity + auth posture
    // ------------------------------------------------------------------

    @Test
    void aClientCanConnectWithoutCredentialsInTheTestProfile() throws Exception {
        StompSession s = connect();
        assertThat(s.isConnected()).isTrue();
    }

    @Test
    void aValidTokenIssuedByTheServerIsAcceptedAtConnect() throws Exception {
        StompHeaders connectHeaders = new StompHeaders();
        connectHeaders.add("Authorization", "Bearer " + tokenService.issue("smoke-test").token());

        session = client.connectAsync(wsUrl(), (WebSocketHttpHeaders) null, connectHeaders,
                new StompSessionHandlerAdapter() { }).get(TIMEOUT_S, TimeUnit.SECONDS);
        assertThat(session.isConnected()).isTrue();
    }

    /**
     * Proves {@code StompAuthChannelInterceptor} is actually installed in the inbound channel —
     * the unit test can't. Even in the advisory (non-required) mode the test profile runs in, a
     * token that is present but forged must be rejected: "unauthenticated" and "lying about who
     * you are" are different, and only the first is waved through.
     */
    @Test
    void aForgedTokenIsRejectedAtConnectEvenThoughAuthIsOptional() {
        StompHeaders connectHeaders = new StompHeaders();
        connectHeaders.add("Authorization", "Bearer this.is.not-a-real-jwt");

        assertThatThrownBy(() -> client.connectAsync(wsUrl(), (WebSocketHttpHeaders) null, connectHeaders,
                        new StompSessionHandlerAdapter() { }).get(TIMEOUT_S, TimeUnit.SECONDS))
                .as("CONNECT with a forged bearer token must not yield a session")
                .isInstanceOf(Exception.class);
    }

    // ------------------------------------------------------------------
    // One broker frame round-trips per topic family
    // ------------------------------------------------------------------

    @Test
    void aGeneratedEventReachesTheMazeStateTopic() throws Exception {
        StompSession s = connect();
        MazeMetadata meta = MazeMetadata.of(5, 7, 42L, "recursive-backtracker",
                new Point(0, 0), new Point(4, 6));
        BlockingQueue<GeneratedFrame> received =
                subscribe(s, "/topic/maze/" + meta.id() + "/state", GeneratedFrame.class);

        MazeStats stats = new MazeStats();
        stats.finish(true);
        MazeGeneratedEvent event = new MazeGeneratedEvent(this, meta, new MazeGrid(5, 7), stats);

        GeneratedFrame frame = publishUntilReceived(received, () -> events.publishEvent(event));
        assertThat(frame).isNotNull();
        assertThat(frame.mazeId()).isEqualTo(meta.id());
        assertThat(frame.rows()).isEqualTo(5);
        assertThat(frame.cols()).isEqualTo(7);
        assertThat(frame.generatorId()).isEqualTo("recursive-backtracker");
    }

    @Test
    void aMutatedEventReachesTheMazeStateTopic() throws Exception {
        StompSession s = connect();
        UUID mazeId = UUID.randomUUID();
        BlockingQueue<MutationFrame> received =
                subscribe(s, "/topic/maze/" + mazeId + "/state", MutationFrame.class);

        MazeMutatedEvent event = new MazeMutatedEvent(this, mazeId, 4, 3, 1, 12, false,
                new MazeGrid(5, 5));

        MutationFrame frame = publishUntilReceived(received, () -> events.publishEvent(event));
        assertThat(frame).isNotNull();
        assertThat(frame.mazeId()).isEqualTo(mazeId);
        assertThat(frame.tick()).isEqualTo(4);
        assertThat(frame.wallsOpened()).isEqualTo(3);
        assertThat(frame.wallsClosed()).isEqualTo(1);
        assertThat(frame.deadEndsRemaining()).isEqualTo(12);
        assertThat(frame.settled()).isFalse();
    }

    @Test
    void aTrafficPulseReachesTheMazeStateTopic() throws Exception {
        StompSession s = connect();
        UUID mazeId = UUID.randomUUID();
        BlockingQueue<TrafficFrame> received =
                subscribe(s, "/topic/maze/" + mazeId + "/state", TrafficFrame.class);

        TrafficPulseEvent event = new TrafficPulseEvent(this, mazeId, 7, 42.5, false,
                new MazeGrid(3, 3));

        TrafficFrame frame = publishUntilReceived(received, () -> events.publishEvent(event));
        assertThat(frame).isNotNull();
        assertThat(frame.mazeId()).isEqualTo(mazeId);
        assertThat(frame.congestedCells()).isEqualTo(7);
        assertThat(frame.peakCost()).isEqualTo(42.5);
        assertThat(frame.settled()).isFalse();
    }

    @Test
    void aSolvedEventReachesTheMazeSolverTopic() throws Exception {
        StompSession s = connect();
        UUID mazeId = UUID.randomUUID();
        BlockingQueue<SolvedFrame> received =
                subscribe(s, "/topic/maze/" + mazeId + "/solver", SolvedFrame.class);

        MazeStats stats = new MazeStats();
        stats.finish(true);
        MazeSolvedEvent event = new MazeSolvedEvent(this, mazeId, "bfs",
                List.of(new Point(0, 0), new Point(0, 1), new Point(1, 1)), stats);

        SolvedFrame frame = publishUntilReceived(received, () -> events.publishEvent(event));
        assertThat(frame).isNotNull();
        assertThat(frame.mazeId()).isEqualTo(mazeId);
        assertThat(frame.solverId()).isEqualTo("bfs");
        assertThat(frame.pathLength()).isEqualTo(3);
        assertThat(frame.success()).isTrue();
    }

    @Test
    void aPlayerMovedEventReachesTheSessionPlayerTopic() throws Exception {
        StompSession s = connect();
        UUID sessionId = UUID.randomUUID();
        BlockingQueue<MoveFrame> received =
                subscribe(s, "/topic/session/" + sessionId + "/player", MoveFrame.class);

        PlayerMovedEvent event =
                new PlayerMovedEvent(this, sessionId, new Point(0, 0), new Point(1, 0));

        MoveFrame frame = publishUntilReceived(received, () -> events.publishEvent(event));
        assertThat(frame).isNotNull();
        assertThat(frame.sessionId()).isEqualTo(sessionId);
        assertThat(frame.from()).isEqualTo(new Point(0, 0));
        assertThat(frame.to()).isEqualTo(new Point(1, 0));
    }

    @Test
    void aPluginFailedEventReachesThePluginFailuresTopic() throws Exception {
        StompSession s = connect();
        BlockingQueue<PluginFailedFrame> received =
                subscribe(s, "/topic/plugins/failures", PluginFailedFrame.class);

        PluginFailedEvent event = new PluginFailedEvent(this, "smoke-test-plugin", "1.0.0",
                PluginFailedEvent.Phase.START, new IllegalStateException("deliberate smoke-test failure"));

        PluginFailedFrame frame = publishUntilReceived(received, () -> events.publishEvent(event));
        assertThat(frame).isNotNull();
        assertThat(frame.pluginId()).isEqualTo("smoke-test-plugin");
        assertThat(frame.phase()).isEqualTo("START");
        assertThat(frame.errorClass()).isEqualTo(IllegalStateException.class.getName());
        assertThat(frame.errorMessage()).isEqualTo("deliberate smoke-test failure");
    }
}
