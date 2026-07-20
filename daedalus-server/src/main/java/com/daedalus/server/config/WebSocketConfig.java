// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import com.daedalus.server.security.JwtTokenService;
import com.daedalus.server.security.StompAuthChannelInterceptor;
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
 *   <li>{@code /topic/maze/{mazeId}/state}        — maze finished generating</li>
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
 * <p>Traffic is currently <b>server → client only</b>. The {@code /app} application prefix and
 * the {@code /user} destination prefix are configured below but unused: there are no
 * {@code @MessageMapping} handlers, and nothing calls {@code convertAndSendToUser}. They are
 * left in place because inbound commands are a planned direction and removing them would be
 * churn — but do not read their presence as evidence that a client can send frames today.
 *
 * <p>{@link StompAuthChannelInterceptor} authenticates the {@code CONNECT} frame, so the
 * messaging layer has a {@link java.security.Principal} rather than relying solely on the
 * HTTP rule guarding the {@code /ws/**} upgrade. It is <em>required</em> under the {@code prod}
 * profile and advisory elsewhere, matching how {@code SecurityConfig} and
 * {@code ProdSecurityConfig} already split the HTTP surface.
 */
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    private final JwtTokenService tokenService;
    private final Environment environment;

    public WebSocketConfig(JwtTokenService tokenService, Environment environment) {
        this.tokenService = tokenService;
        this.environment = environment;
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
        registration.interceptors(
                new StompAuthChannelInterceptor(tokenService.decoder(), required));
    }
}
