// SPDX-License-Identifier: MIT

package com.daedalus.server.security;

import com.daedalus.model.GameSession;
import com.daedalus.model.Point;
import com.daedalus.server.security.StompAuthChannelInterceptor.JwtPrincipal;
import com.daedalus.server.security.StompAuthChannelInterceptor.StompAuthenticationException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.MessageBuilder;

import java.security.Principal;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;

/**
 * Unit contract for the per-destination SUBSCRIBE rule. The integration side —
 * that the interceptor is actually installed and its refusal reaches a real client as a STOMP
 * ERROR — is {@code WebSocketSmokeTest}'s job; here every branch of the decision is pinned in
 * isolation, in the style of {@code StompAuthChannelInterceptorTest}.
 */
class StompSubscriptionAuthorizationInterceptorTest {

    private final Map<UUID, GameSession> store = new HashMap<>();
    private final MessageChannel channel = mock(MessageChannel.class);
    private StompSubscriptionAuthorizationInterceptor interceptor;

    private GameSession ownedByAlice;
    private GameSession unowned;

    @BeforeEach
    void setUp() {
        interceptor = new StompSubscriptionAuthorizationInterceptor(store::get);
        ownedByAlice = new GameSession(UUID.randomUUID(), "Alice", new Point(0, 0), "alice");
        unowned = new GameSession(UUID.randomUUID(), "anon", new Point(0, 0));
        store.put(ownedByAlice.id(), ownedByAlice);
        store.put(unowned.id(), unowned);
    }

    private Message<byte[]> frame(StompCommand command, String destination, Principal user) {
        StompHeaderAccessor accessor = StompHeaderAccessor.create(command);
        if (destination != null) {
            accessor.setDestination(destination);
        }
        if (user != null) {
            accessor.setUser(user);
        }
        return MessageBuilder.createMessage(new byte[0], accessor.getMessageHeaders());
    }

    private static String playerTopic(GameSession session) {
        return "/topic/session/" + session.id() + "/player";
    }

    // --- the rule ---

    @Test
    void ownerMaySubscribeToTheirOwnSessionTopic() {
        Message<byte[]> subscribe =
                frame(StompCommand.SUBSCRIBE, playerTopic(ownedByAlice), new JwtPrincipal("alice"));
        assertThat(interceptor.preSend(subscribe, channel)).isSameAs(subscribe);
    }

    @Test
    void anotherAuthenticatedSubjectIsRefused() {
        Message<byte[]> subscribe =
                frame(StompCommand.SUBSCRIBE, playerTopic(ownedByAlice), new JwtPrincipal("mallory"));
        assertThatThrownBy(() -> interceptor.preSend(subscribe, channel))
                .isInstanceOf(StompAuthenticationException.class);
    }

    @Test
    void aSubjectThatJoinedWithATokenMaySubscribe() {
        ownedByAlice.join("Bob", new Point(0, 0), "bob");
        Message<byte[]> subscribe =
                frame(StompCommand.SUBSCRIBE, playerTopic(ownedByAlice), new JwtPrincipal("bob"));
        assertThat(interceptor.preSend(subscribe, channel)).isSameAs(subscribe);
    }

    @Test
    void joiningWithoutASubjectDoesNotOpenTheOwnedFeed() {
        ownedByAlice.join("Bob", new Point(0, 0));
        Message<byte[]> subscribe =
                frame(StompCommand.SUBSCRIBE, playerTopic(ownedByAlice), new JwtPrincipal("bob"));
        assertThatThrownBy(() -> interceptor.preSend(subscribe, channel))
                .isInstanceOf(StompAuthenticationException.class);
    }

    @Test
    void anAnonymousConnectionIsRefusedOnAnOwnedSessionTopic() {
        // No principal at all — the advisory profile allows connecting without one, but an
        // owned session's feed is still not theirs to watch.
        Message<byte[]> subscribe = frame(StompCommand.SUBSCRIBE, playerTopic(ownedByAlice), null);
        assertThatThrownBy(() -> interceptor.preSend(subscribe, channel))
                .isInstanceOf(StompAuthenticationException.class);
    }

    // --- what deliberately stays open ---

    @Test
    void unownedSessionsHaveNoAccessClaimToEnforce() {
        Message<byte[]> subscribe = frame(StompCommand.SUBSCRIBE, playerTopic(unowned), null);
        assertThat(interceptor.preSend(subscribe, channel)).isSameAs(subscribe);
    }

    @Test
    void unknownSessionIdsAreNotAnExistenceOracle() {
        String ghost = "/topic/session/" + UUID.randomUUID() + "/player";
        Message<byte[]> subscribe = frame(StompCommand.SUBSCRIBE, ghost, new JwtPrincipal("mallory"));
        assertThat(interceptor.preSend(subscribe, channel)).isSameAs(subscribe);
    }

    @Test
    void sharedTopicsAreOutOfScope() {
        for (String destination : new String[] {
                "/topic/maze/" + UUID.randomUUID() + "/state",
                "/topic/maze/" + UUID.randomUUID() + "/solver",
                "/topic/plugins/failures"}) {
            Message<byte[]> subscribe =
                    frame(StompCommand.SUBSCRIBE, destination, new JwtPrincipal("mallory"));
            assertThat(interceptor.preSend(subscribe, channel)).isSameAs(subscribe);
        }
    }

    // --- frames the rule must not touch ---

    @Test
    void nonSubscribeFramesPassThroughUntouched() {
        // Even a SEND aimed at the owned topic: enforcement is at subscription time, matching
        // the CONNECT-only stance documented in StompAuthChannelInterceptor.
        Message<byte[]> send =
                frame(StompCommand.SEND, playerTopic(ownedByAlice), new JwtPrincipal("mallory"));
        assertThat(interceptor.preSend(send, channel)).isSameAs(send);
        Message<byte[]> connect = frame(StompCommand.CONNECT, null, null);
        assertThat(interceptor.preSend(connect, channel)).isSameAs(connect);
    }

    @Test
    void subscribeWithoutADestinationPassesThrough() {
        // Malformed, but not this interceptor's problem — the broker rejects it downstream.
        Message<byte[]> subscribe = frame(StompCommand.SUBSCRIBE, null, null);
        assertThat(interceptor.preSend(subscribe, channel)).isSameAs(subscribe);
    }
}
