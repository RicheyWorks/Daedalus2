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
 * <p>Topic conventions:
 * <ul>
 *   <li>{@code /topic/maze/{id}/state}      — full maze grid snapshots</li>
 *   <li>{@code /topic/maze/{id}/player}     — player movement events</li>
 *   <li>{@code /topic/maze/{id}/solver}     — live solver step-by-step trace</li>
 *   <li>{@code /topic/leaderboard}          — leaderboard deltas</li>
 *   <li>{@code /app/maze/{id}/move}         — client → server move commands</li>
 * </ul>
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
