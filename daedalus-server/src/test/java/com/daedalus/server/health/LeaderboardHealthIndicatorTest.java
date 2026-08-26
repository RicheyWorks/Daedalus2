// SPDX-License-Identifier: MIT

package com.daedalus.server.health;

import com.daedalus.server.service.LeaderboardService;
import org.junit.jupiter.api.Test;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.Status;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Leaderboard Redis split-brain is a detail, never a DOWN. Same contract as
 * {@link PluginSubsystemHealthIndicator}: a completed run must not take the
 * instance out of rotation.
 */
class LeaderboardHealthIndicatorTest {

    @Test
    void aCleanRedisBoardReportsNoErrorNoise() {
        LeaderboardService board = mock(LeaderboardService.class);
        when(board.redisConfigured()).thenReturn(true);
        when(board.lastWriteFellBack()).thenReturn(false);
        when(board.lastWriteError()).thenReturn(null);

        Health health = new LeaderboardHealthIndicator(board).health();
        assertThat(health.getStatus()).isEqualTo(Status.UP);
        assertThat(health.getDetails()).containsEntry("redisConfigured", true);
        assertThat(health.getDetails()).containsEntry("lastWriteFellBack", false);
        assertThat(health.getDetails()).doesNotContainKey("lastWriteError");
    }

    @Test
    void aWriteFallbackIsDescribedWithoutChangingTheStatus() {
        LeaderboardService board = mock(LeaderboardService.class);
        when(board.redisConfigured()).thenReturn(true);
        when(board.lastWriteFellBack()).thenReturn(true);
        when(board.lastWriteError()).thenReturn("connection refused");

        Health health = new LeaderboardHealthIndicator(board).health();
        assertThat(health.getStatus())
                .as("split-brain must not pull the instance out of rotation")
                .isEqualTo(Status.UP);
        assertThat(health.getDetails()).containsEntry("lastWriteFellBack", true);
        assertThat(health.getDetails()).containsEntry("lastWriteError", "connection refused");
    }
}
