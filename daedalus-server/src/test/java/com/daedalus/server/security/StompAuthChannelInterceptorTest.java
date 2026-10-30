// SPDX-License-Identifier: MIT

package com.daedalus.server.security;

import com.daedalus.server.config.JwtAuthProperties;
import org.junit.jupiter.api.Test;
import org.springframework.messaging.Message;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.MessageBuilder;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * STOMP {@code CONNECT} authentication.
 *
 * <p>Exercised at the interceptor rather than over a real socket: the rules being asserted are
 * about frame headers and token validity, and a full handshake would test SockJS transport
 * negotiation instead of the thing that can actually be got wrong.
 */
class StompAuthChannelInterceptorTest {

    private static final String SECRET = "dev-only-secret-change-me-please-32bytes!";

    private static JwtTokenService tokenService() {
        return new JwtTokenService(new JwtAuthProperties(SECRET, "daedalus-test", 60));
    }

    private static StompAuthChannelInterceptor interceptor(boolean required) {
        return new StompAuthChannelInterceptor(tokenService().decoder(), required);
    }

    private static Message<byte[]> connectFrame(String authorizationHeader) {
        StompHeaderAccessor accessor = StompHeaderAccessor.create(StompCommand.CONNECT);
        if (authorizationHeader != null) {
            accessor.setNativeHeader("Authorization", authorizationHeader);
        }
        accessor.setLeaveMutable(true);
        return MessageBuilder.createMessage(new byte[0], accessor.getMessageHeaders());
    }

    private static Message<byte[]> frame(StompCommand command) {
        StompHeaderAccessor accessor = StompHeaderAccessor.create(command);
        accessor.setLeaveMutable(true);
        return MessageBuilder.createMessage(new byte[0], accessor.getMessageHeaders());
    }

    @Test
    void aValidTokenEstablishesThePrincipalFromTheJwtSubject() {
        String token = tokenService().issue("alice").token();
        Message<?> result = interceptor(true).preSend(connectFrame("Bearer " + token), null);

        StompHeaderAccessor accessor =
                StompHeaderAccessor.wrap(result);
        assertThat(accessor.getUser())
                .as("CONNECT must leave an authenticated principal on the session")
                .isNotNull();
        assertThat(accessor.getUser().getName()).isEqualTo("alice");
    }

    @Test
    void whenRequiredAnUnauthenticatedConnectIsRefused() {
        assertThatThrownBy(() -> interceptor(true).preSend(connectFrame(null), null))
                .isInstanceOf(StompAuthChannelInterceptor.StompAuthenticationException.class)
                .hasMessageContaining("requires a bearer token");
    }

    @Test
    void whenNotRequiredAnUnauthenticatedConnectPassesWithoutAPrincipal() {
        // Dev and the embedded desktop build connect without minting a token, matching how
        // SecurityConfig already treats the HTTP surface outside prod.
        Message<?> result = interceptor(false).preSend(connectFrame(null), null);

        assertThat(result).isNotNull();
        assertThat(StompHeaderAccessor.wrap(result).getUser()).isNull();
    }

    @Test
    void aForgedTokenIsRejectedEvenWhenAuthenticationIsOptional() {
        // The distinction that matters: "no credentials" and "bad credentials" are not the
        // same, and only the first is something a permissive profile should wave through.
        // Signed with a different secret, so the signature will not verify.
        JwtTokenService attacker = new JwtTokenService(
                new JwtAuthProperties("a-completely-different-secret-32bytes!!", "evil", 60));
        String forged = attacker.issue("admin").token();

        for (boolean required : new boolean[] {true, false}) {
            assertThatThrownBy(() -> interceptor(required)
                    .preSend(connectFrame("Bearer " + forged), null))
                    .as("required=%s", required)
                    .isInstanceOf(StompAuthChannelInterceptor.StompAuthenticationException.class)
                    .hasMessageContaining("invalid token");
        }
    }

    @Test
    void garbageAndMalformedAuthorizationHeadersAreHandled() {
        StompAuthChannelInterceptor subject = interceptor(true);

        // Not a Bearer scheme at all — treated as absent, so the "required" rule applies.
        assertThatThrownBy(() -> subject.preSend(connectFrame("Basic dXNlcjpwYXNz"), null))
                .isInstanceOf(StompAuthChannelInterceptor.StompAuthenticationException.class)
                .hasMessageContaining("requires a bearer token");

        // Bearer scheme with nothing after it — also absent, not invalid.
        assertThatThrownBy(() -> subject.preSend(connectFrame("Bearer    "), null))
                .isInstanceOf(StompAuthChannelInterceptor.StompAuthenticationException.class)
                .hasMessageContaining("requires a bearer token");

        // Bearer scheme with a non-JWT payload — present but unverifiable.
        assertThatThrownBy(() -> subject.preSend(connectFrame("Bearer not-a-jwt"), null))
                .isInstanceOf(StompAuthChannelInterceptor.StompAuthenticationException.class)
                .hasMessageContaining("invalid token");
    }

    @Test
    void nonConnectFramesPassThroughUntouched() {
        // The principal is established once at CONNECT and carried on the session; re-parsing
        // the token per SEND would cost thousands of verifications for no extra guarantee.
        StompAuthChannelInterceptor subject = interceptor(true);

        for (StompCommand command : new StompCommand[] {
                StompCommand.SEND, StompCommand.SUBSCRIBE, StompCommand.DISCONNECT}) {
            Message<byte[]> message = frame(command);
            assertThatCode(() -> subject.preSend(message, null))
                    .as("%s must not be rejected for lacking a token", command)
                    .doesNotThrowAnyException();
        }
    }
}
