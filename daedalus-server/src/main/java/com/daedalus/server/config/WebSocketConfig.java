// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.springframework.context.annotation.Configuration;
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
 */
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

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
}
