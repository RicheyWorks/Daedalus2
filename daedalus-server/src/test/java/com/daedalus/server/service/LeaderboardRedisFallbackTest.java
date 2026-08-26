// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.model.LeaderboardEntry;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;

import java.time.Instant;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * A Redis write failure must not 500 a finished run, and it must not stay a
 * warn-only log. The in-memory set is the board the player just scored on;
 * another instance reading Redis is looking at a different board.
 */
class LeaderboardRedisFallbackTest {

    private static LeaderboardEntry entry() {
        return new LeaderboardEntry(UUID.randomUUID(), UUID.randomUUID(), "alice",
                100, 10, 1000, "recursive-backtracker", Instant.EPOCH);
    }

    @Test
    void aRedisWriteFailureKeepsTheRunAndFlagsTheFallback() {
        @SuppressWarnings("unchecked")
        RedisTemplate<String, Object> redis = mock(RedisTemplate.class);
        when(redis.opsForZSet()).thenThrow(new RuntimeException("connection refused"));
        SimpleMeterRegistry meters = new SimpleMeterRegistry();
        LeaderboardService svc = new LeaderboardService(redis, true, 10, meters);

        assertThatCode(() -> svc.submit(entry())).doesNotThrowAnyException();
        assertThat(svc.top(1)).as("the finished run stayed in memory").hasSize(1);
        assertThat(svc.lastWriteFellBack())
                .as("split-brain must be visible after a Redis write miss")
                .isTrue();
        assertThat(svc.lastWriteError()).contains("connection refused");
        assertThat(meters.counter("daedalus.leaderboard.redis.write.fallback").count())
                .isEqualTo(1.0);
    }

    @Test
    void aLaterSuccessfulWriteClearsTheFallbackFlag() {
        @SuppressWarnings("unchecked")
        RedisTemplate<String, Object> redis = mock(RedisTemplate.class);
        when(redis.opsForZSet())
                .thenThrow(new RuntimeException("down"))
                .thenReturn(mock(ZSetOperations.class));
        LeaderboardService svc = new LeaderboardService(redis, true, 10, new SimpleMeterRegistry());

        svc.submit(entry());
        assertThat(svc.lastWriteFellBack()).isTrue();
        svc.submit(entry());
        assertThat(svc.lastWriteFellBack())
                .as("health must recover when Redis writes again")
                .isFalse();
        assertThat(svc.lastWriteError()).isNull();
    }

    @Test
    void aChosenMemoryBoardIsNotAFallback() {
        LeaderboardService svc = new LeaderboardService(null, false, 10);
        svc.submit(entry());
        assertThat(svc.redisConfigured()).isFalse();
        assertThat(svc.lastWriteFellBack()).isFalse();
        assertThat(svc.lastWriteError()).isNull();
    }
}
