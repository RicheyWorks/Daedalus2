// SPDX-License-Identifier: MIT

package com.daedalus.server;

import com.daedalus.api.dto.WorldEventFrame;
import com.daedalus.server.service.WorldService;
import com.daedalus.world.BlockType;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.messaging.simp.stomp.StompFrameHandler;
import org.springframework.messaging.simp.stomp.StompHeaders;
import org.springframework.messaging.simp.stomp.StompSession;
import org.springframework.messaging.simp.stomp.StompSessionHandlerAdapter;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.messaging.WebSocketStompClient;
import org.springframework.web.socket.sockjs.client.SockJsClient;
import org.springframework.web.socket.sockjs.client.WebSocketTransport;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.lang.reflect.Type;
import java.util.List;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * World One W1.3 — second observer. The broker already publishes
 * {@code /topic/world/{id}/events}; this proves a second STOMP client sees
 * another actor's place, same JVM, no extra bus.
 *
 * <p>Same subscription race as {@link WebSocketSmokeTest}: the simple broker
 * has no RECEIPT, so place is retried until B's frame arrives. Never
 * {@code Thread.sleep}.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class WorldSecondObserverTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final long TIMEOUT_S = 10;
    private static final String WORLD = "world-zero";
    private static final String TOPIC = "/topic/world/" + WORLD + "/events";
    /** Far from other suite writes that share the test DAEW file. */
    private static final int X = 91;
    private static final int Y = 7;
    private static final int Z = -13;

    @LocalServerPort
    private int port;

    @Autowired
    private WorldService worlds;

    private WebSocketStompClient clientA;
    private WebSocketStompClient clientB;
    private StompSession sessionA;
    private StompSession sessionB;

    @BeforeEach
    void createClients() {
        clientA = newClient();
        clientB = newClient();
    }

    @AfterEach
    void tearDown() {
        disconnect(sessionA);
        disconnect(sessionB);
        if (clientA != null) {
            clientA.stop();
        }
        if (clientB != null) {
            clientB.stop();
        }
    }

    @Test
    void secondObserverSeesThePlaceAndMatchingRevision() throws Exception {
        sessionA = connect(clientA);
        sessionB = connect(clientB);
        BlockingQueue<WorldEventFrame> fromA = subscribe(sessionA);
        BlockingQueue<WorldEventFrame> fromB = subscribe(sessionB);

        WorldEventFrame seen = placeUntilObserver(fromB);
        assertThat(seen).as("observer B must receive BLOCK_PLACED").isNotNull();
        long revision = worlds.inspect(WORLD).revision().value();
        assertThat(seen.worldId()).isEqualTo(WORLD);
        assertThat(seen.kind()).isEqualTo("BLOCK_PLACED");
        assertThat(seen.x()).isEqualTo(X);
        assertThat(seen.y()).isEqualTo(Y);
        assertThat(seen.z()).isEqualTo(Z);
        assertThat(seen.type()).isEqualTo("STONE");
        assertThat(seen.revision()).isEqualTo(revision);
        assertThat(worlds.inspectBlock(WORLD, X, Y, Z)).isEqualTo(BlockType.STONE);

        WorldEventFrame alsoA = matchingPlace(fromA, revision);
        assertThat(alsoA).as("observer A is on the same topic").isNotNull();
        assertThat(alsoA.revision()).isEqualTo(seen.revision());
    }

    private WorldEventFrame placeUntilObserver(BlockingQueue<WorldEventFrame> observer)
            throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(TIMEOUT_S);
        while (System.nanoTime() < deadline) {
            worlds.place(WORLD, X, Y, Z, BlockType.STONE);
            long revision = worlds.inspect(WORLD).revision().value();
            WorldEventFrame match = matchingPlace(observer, revision);
            if (match != null) {
                return match;
            }
        }
        return null;
    }

    private static WorldEventFrame matchingPlace(BlockingQueue<WorldEventFrame> q, long revision)
            throws InterruptedException {
        long slice = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(250);
        while (System.nanoTime() < slice) {
            WorldEventFrame frame = q.poll(50, TimeUnit.MILLISECONDS);
            if (frame != null && "BLOCK_PLACED".equals(frame.kind())
                    && frame.x() == X && frame.y() == Y && frame.z() == Z
                    && frame.revision() == revision) {
                return frame;
            }
        }
        return null;
    }

    private WebSocketStompClient newClient() {
        return new WebSocketStompClient(
                new SockJsClient(List.of(new WebSocketTransport(new StandardWebSocketClient()))));
    }

    private StompSession connect(WebSocketStompClient client) throws Exception {
        return client.connectAsync("http://localhost:" + port + "/ws",
                new StompSessionHandlerAdapter() { }).get(TIMEOUT_S, TimeUnit.SECONDS);
    }

    private BlockingQueue<WorldEventFrame> subscribe(StompSession session) {
        BlockingQueue<WorldEventFrame> received = new ArrayBlockingQueue<>(64);
        session.subscribe(TOPIC, new StompFrameHandler() {
            @Override
            public Type getPayloadType(StompHeaders headers) {
                return byte[].class;
            }

            @Override
            public void handleFrame(StompHeaders headers, Object payload) {
                try {
                    received.offer(MAPPER.readValue((byte[]) payload, WorldEventFrame.class));
                } catch (IOException e) {
                    throw new UncheckedIOException(e);
                }
            }
        });
        return received;
    }

    private static void disconnect(StompSession session) {
        if (session != null && session.isConnected()) {
            session.disconnect();
        }
    }
}
