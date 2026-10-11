// SPDX-License-Identifier: MIT

package com.daedalus.server.health;

import com.daedalus.server.service.LeaderboardService;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.stereotype.Component;

/**
 * Reports whether leaderboard Redis reads and writes are landing, without
 * condemning the instance.
 *
 * <p>When {@code daedalus.redis.enabled} is true and Redis throws, the page
 * still stays 200 from memory. Two instances then score different boards.
 * That is split-brain, not a crash — so this indicator stays {@code UP} and
 * puts the last fallback on the payload, the same contract as
 * {@link PluginSubsystemHealthIndicator}.
 */
@Component
public class LeaderboardHealthIndicator implements HealthIndicator {

    private final LeaderboardService board;

    public LeaderboardHealthIndicator(LeaderboardService board) {
        this.board = board;
    }

    @Override
    public Health health() {
        Health.Builder builder = Health.up()
                .withDetail("redisConfigured", board.redisConfigured())
                .withDetail("lastWriteFellBack", board.lastWriteFellBack())
                .withDetail("lastReadFellBack", board.lastReadFellBack());
        String writeError = board.lastWriteError();
        if (writeError != null) {
            builder.withDetail("lastWriteError", writeError);
        }
        String readError = board.lastReadError();
        if (readError != null) {
            builder.withDetail("lastReadError", readError);
        }
        return builder.build();
    }
}
