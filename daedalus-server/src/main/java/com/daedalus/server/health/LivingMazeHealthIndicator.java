// SPDX-License-Identifier: MIT

package com.daedalus.server.health;

import com.daedalus.server.service.LivingMazeService;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.stereotype.Component;

/**
 * Reports whether living-maze ticks are completing, without condemning the
 * instance.
 *
 * <p>A thrown tick still retires that run so the shared ticker lives. That is
 * a stuck maze, not a crash — so this indicator stays {@code UP} and puts the
 * last failure on the payload, the same contract as
 * {@link PluginSubsystemHealthIndicator}.
 */
@Component
public class LivingMazeHealthIndicator implements HealthIndicator {

    private final LivingMazeService living;

    public LivingMazeHealthIndicator(LivingMazeService living) {
        this.living = living;
    }

    @Override
    public Health health() {
        Health.Builder builder = Health.up()
                .withDetail("liveCount", living.liveCount())
                .withDetail("lastTickFailed", living.lastTickFailed());
        String error = living.lastTickError();
        if (error != null) {
            builder.withDetail("lastTickError", error);
        }
        return builder.build();
    }
}
