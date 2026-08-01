// SPDX-License-Identifier: MIT

package com.daedalus.server;

import com.daedalus.model.Point;
import com.daedalus.plugin.events.PlayerMovedEvent;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.messaging.simp.stomp.StompHeaders;
import org.springframework.messaging.simp.stomp.StompFrameHandler;
import org.springframework.messaging.simp.stomp.StompSession;
import org.springframework.messaging.simp.stomp.StompSessionHandlerAdapter;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.web.socket.WebSocketHttpHeaders;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.messaging.WebSocketStompClient;
import org.springframework.web.socket.sockjs.client.SockJsClient;
import org.springframework.web.socket.sockjs.client.WebSocketTransport;

import java.lang.reflect.Type;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * A connected client cannot publish onto a topic it does not own — or any topic.
 *
 * <h3>What this proves that {@code StompSendRejectionTest} cannot</h3>
 *
 * <p>That the interceptor is <b>installed</b>. The unit test drives
 * {@code StompSendRejectionInterceptor} directly and would stay green if
 * {@code WebSocketConfig} never registered it, which is precisely the state the codebase was in
 * until 2026-07-31 — an interceptor chain that authenticated {@code CONNECT} and authorised
 * {@code SUBSCRIBE} while a client {@code SEND} to any {@code /topic} destination went straight
 * to Spring's simple broker and out to every subscriber.
 *
 * <p>Verified against a running server before the fix, with two anonymous clients: the forged
 * frame arrived at the spectator looking exactly like a real move. This test is that experiment,
 * with the expectation inverted.
 *
 * <p>The second assertion is the one that stops this becoming decorative. Asserting only that
 * the sender is refused would pass if the frame were dropped *after* the broker fanned it out;
 * asserting that a genuine server-published event still arrives afterwards proves the refusal
 * is aimed at client input and has not simply broken the channel.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class WebSocketForgerySmokeTest {

    private static final long QUIET_MS = 1500;
    private static final long TIMEOUT_S = 10;

    @LocalServerPort
    private int port;

    @Autowired
    private ApplicationEventPublisher events;

    private WebSocketStompClient spectatorClient;
    private WebSocketStompClient attackerClient;

    @BeforeEach
    void createClients() {
        spectatorClient = newClient();
        attackerClient = newClient();
    }

    private WebSocketStompClient newClient() {
        var client = new WebSocketStompClient(
                new SockJsClient(List.of(new WebSocketTransport(new StandardWebSocketClient()))));
        // Jackson, not String. The server publishes application/json; a
        // StringMessageConverter accepts the frame off the wire and then cannot convert it, so
        // the handler is never called and the symptom is "no frame arrived" — identical to the
        // symptom of a broken broadcast channel, and a good way to spend twenty minutes
        // debugging the wrong layer.
        client.setMessageConverter(
                new org.springframework.messaging.converter.JacksonJsonMessageConverter());
        return client;
    }

    @AfterEach
    void tearDown() {
        spectatorClient.stop();
        attackerClient.stop();
    }

    private StompSession connect(WebSocketStompClient client) throws Exception {
        return client.connectAsync("http://localhost:" + port + "/ws",
                new WebSocketHttpHeaders(), new StompHeaders(),
                new StompSessionHandlerAdapter() { }).get(TIMEOUT_S, TimeUnit.SECONDS);
    }

    @Test
    void aClientCannotForgeAMoveFrameOntoAnotherSessionsTopic() throws Exception {
        UUID sessionId = UUID.randomUUID();
        String topic = "/topic/session/" + sessionId + "/player";

        BlockingQueue<String> seen = new ArrayBlockingQueue<>(8);
        StompSession spectator = connect(spectatorClient);
        spectator.subscribe(topic, new StompFrameHandler() {
            @Override
            public Type getPayloadType(StompHeaders headers) {
                return java.util.Map.class;
            }

            @Override
            public void handleFrame(StompHeaders headers, Object payload) {
                seen.offer(String.valueOf(payload));
            }
        });

        StompSession attacker = connect(attackerClient);
        try {
            // A Map, not a JSON string. Sending the string made this assertion unfalsifiable:
            // Jackson serialises a String as a JSON *string*, which the spectator's Map payload
            // type can never deserialise, so the frame could not arrive whether or not the
            // interceptor existed. The mutation harness caught it — unregistering the
            // interceptor left this test green, which is the whole failure mode it was
            // written to rule out.
            attacker.send(topic, java.util.Map.of("player", "victim", "forged", true));
        } catch (RuntimeException refusedSynchronously) {
            // Either shape is a refusal: the interceptor throws on the inbound channel, and
            // whether that surfaces here or as an async ERROR frame depends on timing. The
            // assertion that matters is below — nothing reached the spectator.
        }

        assertThat(seen.poll(QUIET_MS, TimeUnit.MILLISECONDS))
                .as("a client SEND was relayed to a subscriber — any connected client can forge "
                        + "frames onto any topic, which is what this whole interceptor exists to "
                        + "prevent")
                .isNull();

        // ...and the channel still works. Without this, deleting the WebSocket layer entirely
        // would pass the assertion above.
        StompSession watcher = connect(newClient());
        BlockingQueue<String> real = new ArrayBlockingQueue<>(8);
        watcher.subscribe(topic, new StompFrameHandler() {
            @Override
            public Type getPayloadType(StompHeaders headers) {
                return java.util.Map.class;
            }

            @Override
            public void handleFrame(StompHeaders headers, Object payload) {
                real.offer(String.valueOf(payload));
            }
        });
        Thread.sleep(300);
        // First argument is the event source, not an id. Getting that wrong published to
        // /topic/session/<mazeId>/player and the assertion below failed for a reason that had
        // nothing to do with the interceptor — worth the comment, because a silent
        // wrong-destination is exactly the failure this whole area produces.
        events.publishEvent(new PlayerMovedEvent(this, sessionId, "victim",
                new Point(0, 0), new Point(0, 1)));

        assertThat(real.poll(TIMEOUT_S, TimeUnit.SECONDS))
                .as("the server's own publication must still reach subscribers — refusing client "
                        + "SEND must not close the broadcast channel")
                .isNotNull();
    }
}
