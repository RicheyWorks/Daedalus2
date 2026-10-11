// SPDX-License-Identifier: MIT

package com.daedalus.server.health;

import com.daedalus.server.service.TrafficService;
import org.junit.jupiter.api.Test;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.Status;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * A thrown traffic tick is a detail, never a DOWN. Same contract as
 * {@link PluginSubsystemHealthIndicator}: one broken maze must not take the
 * instance out of rotation.
 */
class TrafficHealthIndicatorTest {

    @Test
    void aCleanTickerReportsNoErrorNoise() {
        TrafficService traffic = mock(TrafficService.class);
        when(traffic.trackedCount()).thenReturn(1);
        when(traffic.lastTickFailed()).thenReturn(false);
        when(traffic.lastTickError()).thenReturn(null);

        Health health = new TrafficHealthIndicator(traffic).health();
        assertThat(health.getStatus()).isEqualTo(Status.UP);
        assertThat(health.getDetails()).containsEntry("trackedCount", 1);
        assertThat(health.getDetails()).containsEntry("lastTickFailed", false);
        assertThat(health.getDetails()).doesNotContainKey("lastTickError");
    }

    @Test
    void aFailedTickIsDescribedWithoutChangingTheStatus() {
        TrafficService traffic = mock(TrafficService.class);
        when(traffic.trackedCount()).thenReturn(0);
        when(traffic.lastTickFailed()).thenReturn(true);
        when(traffic.lastTickError()).thenReturn("cache swap failed");

        Health health = new TrafficHealthIndicator(traffic).health();
        assertThat(health.getStatus())
                .as("stuck congestion must not pull the instance out of rotation")
                .isEqualTo(Status.UP);
        assertThat(health.getDetails()).containsEntry("lastTickFailed", true);
        assertThat(health.getDetails()).containsEntry("lastTickError", "cache swap failed");
    }
}
