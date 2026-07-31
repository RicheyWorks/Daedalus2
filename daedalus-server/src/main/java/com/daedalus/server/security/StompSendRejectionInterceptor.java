// SPDX-License-Identifier: MIT

package com.daedalus.server.security;

import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.ChannelInterceptor;
import org.springframework.messaging.support.MessageHeaderAccessor;

/**
 * Refuses every client {@code SEND} frame. This STOMP surface is broadcast-only.
 *
 * <h3>The hole this closes</h3>
 *
 * <p>{@link StompAuthChannelInterceptor} authenticates {@code CONNECT} and
 * {@link StompSubscriptionAuthorizationInterceptor} authorises {@code SUBSCRIBE} per
 * destination. Nothing looked at {@code SEND} — and because the broker is Spring's
 * <em>simple</em> broker with {@code /topic} enabled, a client frame addressed to a
 * {@code /topic} destination is handled by the broker directly and relayed to every subscriber
 * without passing through any application code.
 *
 * <p>Measured against a running server on 2026-07-31: a second client connected anonymously,
 * sent one frame to another player's {@code /topic/session/&#123;id&#125;/player}, and the
 * spectator received it — byte-identical in shape to a real server-published move. The same
 * worked on {@code /topic/maze/&#123;id&#125;}.
 *
 * <p>The asymmetry is the point. Considerable care went into deciding who may <em>read</em> an
 * owned session's move feed; nobody asked who may <em>write</em> to it, and the answer was
 * everybody. A guard on one direction of a channel reads, from a distance, exactly like a guard
 * on the channel.
 *
 * <p>What an attacker gets is display, not state: {@code PlayerMovedEvent} is published by the
 * server from its own record of the move, so the score, the leaderboard and the waypoint
 * progress were never forgeable. But the spectator seam, the ghost racer and the multiplayer
 * view all render what arrives on these topics, and "the number is right but the picture is a
 * lie" is not a comfortable place to stand.
 *
 * <h3>Why the rule is total rather than per-destination</h3>
 *
 * <p>The obvious shape — allow {@code SEND} to {@code /app/**} and refuse it to {@code /topic}
 * — is more permission than this application can use. There is not a single
 * {@code @MessageMapping} or {@code @SubscribeMapping} in the codebase: every frame a client
 * receives originates from a Spring event handled in {@code MazeWebSocketController} and
 * published through {@code SimpMessagingTemplate}. A client has nothing legitimate to say, so
 * the narrowest correct rule is to refuse all of it, and a rule with no exceptions has no
 * exceptions to get wrong later.
 *
 * <p>That reasoning has an expiry date, and {@code StompSendRejectionTest} enforces it: it
 * scans the sources for message-mapping annotations and fails the build if one appears. The day
 * this application grows a real client-to-server message, this blanket refusal becomes wrong,
 * and the build will say so rather than the feature silently not working.
 *
 * <p>Server-side publishing is unaffected. {@code SimpMessagingTemplate} writes to the broker
 * channel; this interceptor is registered on the <em>client inbound</em> channel and never sees
 * those messages.
 */
public class StompSendRejectionInterceptor implements ChannelInterceptor {

    @Override
    public Message<?> preSend(Message<?> message, MessageChannel channel) {
        StompHeaderAccessor accessor =
                MessageHeaderAccessor.getAccessor(message, StompHeaderAccessor.class);
        if (accessor == null || !StompCommand.SEND.equals(accessor.getCommand())) {
            return message;
        }
        // Returning null drops the frame before the broker sees it; Spring turns the refusal
        // into a STOMP ERROR frame for the sender, which is the same shape SUBSCRIBE refusal
        // already produces, so a client sees one consistent failure mode.
        throw new IllegalStateException(
                "This STOMP surface is broadcast-only; clients may not SEND. "
                        + "Destination was: " + accessor.getDestination());
    }
}
