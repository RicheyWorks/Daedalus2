// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import com.daedalus.server.security.JwtTokenService;
import com.daedalus.server.security.StompAuthChannelInterceptor;
import com.daedalus.server.security.StompSendRejectionInterceptor;
import com.daedalus.server.security.StompSubscriptionAuthorizationInterceptor;
import com.daedalus.server.service.GameSessionService;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;
import org.springframework.messaging.simp.config.ChannelRegistration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

/**
 * WebSocket / STOMP wiring.
 *
 * <p>Destinations the server actually publishes to, verified against
 * {@code MazeWebSocketController}'s {@code convertAndSend} calls:
 * <ul>
 *   <li>{@code /topic/maze/{mazeId}/state}        — generate, living tick, or
 *       traffic pulse ({@code GeneratedFrame} / {@code MutationFrame} /
 *       {@code TrafficFrame}; consumers branch on {@code generatorId},
 *       {@code tick}, {@code congestedCells})</li>
 *   <li>{@code /topic/maze/{mazeId}/solver}       — solver finished a run</li>
 *   <li>{@code /topic/session/{sessionId}/player} — player moved</li>
 *   <li>{@code /topic/plugins/failures}           — a plugin threw in any lifecycle phase</li>
 * </ul>
 *
 * <p>This list previously named {@code /topic/maze/{id}/player} (the player topic is keyed by
 * <em>session</em>, not maze), {@code /topic/leaderboard} (no such destination exists) and
 * {@code /app/maze/{id}/move} (no {@code @MessageMapping} handler exists). Corrected
 * 2026-07-19 against the source; a wrong topic name here costs an integrator a debugging
 * session, because subscribing to a destination nobody publishes to fails silently.
 *
 * <p>Traffic is <b>server → client only</b>, and as of 2026-07-31 that is enforced rather than
 * merely true of the handler set. The {@code /app} application prefix and the {@code /user}
 * destination prefix are configured below but unused: there are no {@code @MessageMapping}
 * handlers, and nothing calls {@code convertAndSendToUser}.
 *
 * <p><b>An earlier version of this paragraph got that wrong, and the mistake is instructive.</b>
 * It read "do not read their presence as evidence that a client can send frames today" — a
 * reassurance drawn from the correct observation that no {@code @MessageMapping} exists. The
 * inference does not hold. A client {@code SEND} addressed to a {@code /topic} destination is not
 * dispatched to application code at all; the simple broker enabled below handles it and relays it
 * to every subscriber. Measured against a running server: an anonymous second client published a
 * forged move frame into another player's session feed, and the spectator could not tell it from
 * a real one. "No handler of ours" is not "no handler".
 * {@link StompSendRejectionInterceptor} now refuses client {@code SEND} outright.
 *
 * <p>{@link StompAuthChannelInterceptor} authenticates the {@code CONNECT} frame, so the
 * messaging layer has a {@link java.security.Principal}. It is <em>required</em> under the
 * {@code prod} profile and advisory elsewhere. The HTTP {@code /ws/**} upgrade is public in
 * prod: browsers cannot attach {@code Authorization} to a SockJS handshake, so the token
 * rides {@code CONNECT} or it does not ride at all.
 * {@link StompSubscriptionAuthorizationInterceptor} then enforces the per-destination rule
 * that principal exists for: {@code SUBSCRIBE} to an owned session's
 * {@code /topic/session/{id}/player} is refused unless the principal is the owner.
 */
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    private final JwtTokenService tokenService;
    private final Environment environment;
    private final GameSessionService sessions;

    public WebSocketConfig(JwtTokenService tokenService,
                           Environment environment,
                           GameSessionService sessions) {
        this.tokenService = tokenService;
        this.environment = environment;
        this.sessions = sessions;
    }

    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        registry.enableSimpleBroker("/topic", "/queue");
        registry.setApplicationDestinationPrefixes("/app");
        registry.setUserDestinationPrefix("/user");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws").setAllowedOriginPatterns("*").withSockJS();
    }

    @Override
    public void configureClientInboundChannel(ChannelRegistration registration) {
        boolean required = environment.matchesProfiles("prod");
        // Order matters: authentication first (attaches the Principal at CONNECT), then the
        // per-destination rule that reads that Principal on SUBSCRIBE.
        registration.interceptors(
                new StompAuthChannelInterceptor(tokenService.decoder(), required),
                new StompSubscriptionAuthorizationInterceptor(sessions::find),
                // Third, refuse client SEND outright. The first two guard who may connect and
                // who may read; until 2026-07-31 nothing guarded who may write, and with a
                // simple broker on /topic that meant any connected client could publish a
                // forged move frame into any session's feed. Measured, not theorised.
                new StompSendRejectionInterceptor());
    }
}
