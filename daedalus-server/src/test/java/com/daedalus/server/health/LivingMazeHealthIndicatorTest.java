// SPDX-License-Identifier: MIT

package com.daedalus.server.health;

import com.daedalus.server.service.LivingMazeService;
import org.junit.jupiter.api.Test;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.Status;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * A thrown living tick is a detail, never a DOWN. Same contract as
 * {@link PluginSubsystemHealthIndicator}: one broken maze must not take the
 * instance out of rotation.
 */
class LivingMazeHealthIndicatorTest {

    @Test
    void aCleanTickerReportsNoErrorNoise() {
        LivingMazeService living = mock(LivingMazeService.class);
        when(living.liveCount()).thenReturn(1);
        when(living.lastTickFailed()).thenReturn(false);
        when(living.lastTickError()).thenReturn(null);

        Health health = new LivingMazeHealthIndicator(living).health();
        assertThat(health.getStatus()).isEqualTo(Status.UP);
        assertThat(health.getDetails()).containsEntry("liveCount", 1);
        assertThat(health.getDetails()).containsEntry("lastTickFailed", false);
        assertThat(health.getDetails()).doesNotContainKey("lastTickError");
    }

    @Test
    void aFailedTickIsDescribedWithoutChangingTheStatus() {
        LivingMazeService living = mock(LivingMazeService.class);
        when(living.liveCount()).thenReturn(0);
        when(living.lastTickFailed()).thenReturn(true);
        when(living.lastTickError()).thenReturn("cache swap failed");

        Health health = new LivingMazeHealthIndicator(living).health();
        assertThat(health.getStatus())
                .as("a stuck maze must not pull the instance out of rotation")
                .isEqualTo(Status.UP);
        assertThat(health.getDetails()).containsEntry("lastTickFailed", true);
        assertThat(health.getDetails()).containsEntry("lastTickError", "cache swap failed");
    }
}
