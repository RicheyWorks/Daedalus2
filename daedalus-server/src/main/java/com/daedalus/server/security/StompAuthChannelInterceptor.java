// SPDX-License-Identifier: MIT

package com.daedalus.server.security;

import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.ChannelInterceptor;
import org.springframework.messaging.support.MessageHeaderAccessor;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtException;

import java.security.Principal;
import java.util.List;

/**
 * Authenticates the STOMP {@code CONNECT} frame and attaches the resulting {@link Principal} to
 * the session.
 *
 * <h3>What this closes, and what it does not</h3>
 *
 * <p>Before this, HTTP-level security guarded the {@code /ws/**} upgrade in the {@code prod}
 * profile, but nothing inspected STOMP frames — so the messaging layer had <b>no notion of who
 * was connected</b>. Two consequences: a deployment that exposed the endpoint without the HTTP
 * rule (a misconfigured profile, or a proxy terminating the upgrade) had no second line of
 * defence, and there was no principal on which any per-destination rule could ever be built.
 *
 * <p>What it does <em>not</em> close is horizontal access between authenticated users. The
 * broker's destinations — {@code /topic/maze/&#123;id&#125;/state},
 * {@code /topic/session/&#123;id&#125;/player} — are not scoped to an owner, and nothing in the
 * domain records which subject owns a session, so "may this principal subscribe here?" is not a
 * question the server can currently answer. Authenticating {@code CONNECT} is the prerequisite
 * for that work, not a substitute for it; see BACKLOG.md.
 *
 * <h3>Why {@code CONNECT} only</h3>
 *
 * <p>STOMP sessions are long-lived and the principal is established once, at {@code CONNECT},
 * then carried on the session for every later frame — so re-validating on {@code SEND} would
 * re-parse the same token thousands of times for no additional guarantee. The token's
 * expiry therefore bounds the <em>connection</em>, not each frame; a connection outliving its
 * token is the known trade-off of session-scoped auth, and disconnecting on expiry is a
 * separate feature.
 */
public class StompAuthChannelInterceptor implements ChannelInterceptor {

    private static final String AUTHORIZATION = "Authorization";
    private static final String BEARER = "Bearer ";

    private final JwtDecoder decoder;
    private final boolean required;

    /**
     * @param decoder  verifies the bearer token; share the one that issues them so signing and
     *                 verification cannot drift
     * @param required when {@code true} an unauthenticated {@code CONNECT} is rejected. Prod
     *                 sets this; dev and the desktop build leave it {@code false} so a local
     *                 client can connect without minting a token, matching how
     *                 {@code SecurityConfig} already treats the HTTP surface.
     */
    public StompAuthChannelInterceptor(JwtDecoder decoder, boolean required) {
        this.decoder = decoder;
        this.required = required;
    }

    @Override
    public Message<?> preSend(Message<?> message, MessageChannel channel) {
        StompHeaderAccessor accessor =
                MessageHeaderAccessor.getAccessor(message, StompHeaderAccessor.class);
        if (accessor == null || !StompCommand.CONNECT.equals(accessor.getCommand())) {
            return message;
        }

        String token = bearerToken(accessor);
        if (token == null) {
            if (required) {
                throw new StompAuthenticationException("STOMP CONNECT requires a bearer token");
            }
            return message;
        }

        Jwt jwt;
        try {
            jwt = decoder.decode(token);
        } catch (JwtException e) {
            // Always reject a token that is present but bad, even when auth is optional —
            // "unauthenticated" and "lying about who you are" are different, and only the
            // first is something a permissive profile should wave through.
            throw new StompAuthenticationException("STOMP CONNECT carried an invalid token");
        }

        accessor.setUser(new JwtPrincipal(jwt.getSubject()));
        return message;
    }

    /** Reads {@code Authorization: Bearer <token>} from the CONNECT frame's native headers. */
    private static String bearerToken(StompHeaderAccessor accessor) {
        List<String> values = accessor.getNativeHeader(AUTHORIZATION);
        if (values == null || values.isEmpty()) {
            return null;
        }
        String raw = values.get(0);
        if (raw == null || !raw.startsWith(BEARER)) {
            return null;
        }
        String token = raw.substring(BEARER.length()).trim();
        return token.isEmpty() ? null : token;
    }

    /** The authenticated STOMP user — its {@code name} is the JWT subject. */
    public record JwtPrincipal(String name) implements Principal {
        @Override
        public String getName() {
            return name;
        }
    }

    /** Raised to refuse a {@code CONNECT}; the broker turns this into a STOMP {@code ERROR}. */
    public static class StompAuthenticationException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        public StompAuthenticationException(String message) {
            super(message);
        }
    }
}
