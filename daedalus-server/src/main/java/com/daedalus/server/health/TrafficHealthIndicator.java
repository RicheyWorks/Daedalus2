// SPDX-License-Identifier: MIT

package com.daedalus.server.health;

import com.daedalus.server.service.TrafficService;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.stereotype.Component;

/**
 * Reports whether traffic ticks are completing, without condemning the
 * instance.
 *
 * <p>A thrown tick still retires that tracker so the shared ticker lives.
 * That is stuck congestion, not a crash — so this indicator stays {@code UP}
 * and puts the last failure on the payload, the same contract as
 * {@link PluginSubsystemHealthIndicator}.
 */
@Component
public class TrafficHealthIndicator implements HealthIndicator {

    private final TrafficService traffic;

    public TrafficHealthIndicator(TrafficService traffic) {
        this.traffic = traffic;
    }

    @Override
    public Health health() {
        Health.Builder builder = Health.up()
                .withDetail("trackedCount", traffic.trackedCount())
                .withDetail("lastTickFailed", traffic.lastTickFailed());
        String error = traffic.lastTickError();
        if (error != null) {
            builder.withDetail("lastTickError", error);
        }
        return builder.build();
    }
}
