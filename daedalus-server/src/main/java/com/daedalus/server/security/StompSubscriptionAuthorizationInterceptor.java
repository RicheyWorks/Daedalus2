// SPDX-License-Identifier: MIT

package com.daedalus.server.security;

import com.daedalus.model.GameSession;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.ChannelInterceptor;
import org.springframework.messaging.support.MessageHeaderAccessor;

import java.security.Principal;
import java.util.UUID;
import java.util.function.Function;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Per-destination STOMP authorization — the second half of the BACKLOG item whose first half
 * ({@code CONNECT} authentication) shipped 2026-07-19.
 *
 * <h3>What this closes</h3>
 *
 * <p>Before this, any connected client could subscribe to any session's
 * {@code /topic/session/{id}/player} feed and watch another player's moves live.
 * {@link StompAuthChannelInterceptor} put a {@link Principal} on the session precisely so this
 * question could be asked; session ownership (recorded at open, see
 * {@code GameSessionService#open}) is what makes it answerable. A {@code SUBSCRIBE} to an
 * <b>owned</b> session's player topic is allowed only when the connection's principal is that
 * owner <em>or a subject that joined with a token</em> (ADR-012) — anyone else,
 * authenticated or not, is refused. Joining used to put a piece on the board and
 * leave the live feed owner-only, so a second authenticated client could move
 * over REST and never see the other player's frames.
 *
 * <h3>What this deliberately leaves open</h3>
 *
 * <ul>
 *   <li><b>Unowned sessions</b> (opened without credentials — the dev/desktop posture) have no
 *       access claim to enforce; their topics stay open, mirroring how missing-vs-forged
 *       credentials are treated at {@code CONNECT}.</li>
 *   <li><b>Unknown session ids</b>: allowed. Nothing will ever publish there, and refusing
 *       would turn this interceptor into an existence oracle for session ids.</li>
 *   <li><b>Maze and plugin topics</b> ({@code /topic/maze/**}, {@code /topic/plugins/**}):
 *       mazes are shared surfaces (any number of sessions play the same maze) and plugin
 *       failures are operator telemetry; neither carries per-user data. Scoping them would be
 *       authorization theater until the domain says otherwise.</li>
 * </ul>
 *
 * <p>Takes a lookup function rather than the service so the unit test needs no Spring;
 * {@code WebSocketConfig} wires {@code GameSessionService::find}.
 */
public class StompSubscriptionAuthorizationInterceptor implements ChannelInterceptor {

    /** {@code /topic/session/{uuid}/player} — the only destination family that is per-user. */
    private static final Pattern OWNED_DESTINATION =
            Pattern.compile("/topic/session/([0-9a-fA-F-]{36})/player");

    private final Function<UUID, GameSession> sessions;

    public StompSubscriptionAuthorizationInterceptor(Function<UUID, GameSession> sessions) {
        this.sessions = sessions;
    }

    @Override
    public Message<?> preSend(Message<?> message, MessageChannel channel) {
        StompHeaderAccessor accessor =
                MessageHeaderAccessor.getAccessor(message, StompHeaderAccessor.class);
        if (accessor == null || !StompCommand.SUBSCRIBE.equals(accessor.getCommand())) {
            return message;
        }
        String destination = accessor.getDestination();
        if (destination == null) {
            return message;
        }
        Matcher m = OWNED_DESTINATION.matcher(destination);
        if (!m.matches()) {
            return message;
        }
        UUID sessionId;
        try {
            sessionId = UUID.fromString(m.group(1));
        } catch (IllegalArgumentException e) {
            return message; // 36 chars of hex-and-dashes that still isn't a UUID: not ours
        }
        GameSession session = sessions.apply(sessionId);
        if (session == null) {
            return message;
        }
        Principal user = accessor.getUser();
        String subject = user == null ? null : user.getName();
        if (session.maySubscribe(subject)) {
            return message;
        }
        throw new StompAuthChannelInterceptor.StompAuthenticationException(
                "SUBSCRIBE to " + destination + " refused: session is owned by another subject");
    }
}
