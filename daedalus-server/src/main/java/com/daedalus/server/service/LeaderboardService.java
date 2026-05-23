// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.model.LeaderboardEntry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentSkipListSet;

/**
 * Leaderboard persistence.
 *
 * <p>Uses Redis sorted sets when available (key-per-generator for per-algorithm
 * leaderboards plus a global aggregate). Falls back to an in-memory sorted set
 * when Redis is offline or {@code daedalus.redis.enabled=false}.
 *
 * <p>The {@code RedisTemplate} bean is injected as optional via
 * {@code @Autowired(required = false)} — when {@code RedisConfig} is gated off (the
 * default), no template exists and we operate fully in-memory without complaint.
 */
@Service
public class LeaderboardService {

    private static final Logger log = LoggerFactory.getLogger(LeaderboardService.class);
    private static final String GLOBAL_KEY = "daedalus:leaderboard:global";
    private static final String PER_GEN_KEY = "daedalus:leaderboard:gen:";

    private final RedisTemplate<String, Object> redis;
    private final boolean redisEnabled;
    private final ConcurrentSkipListSet<LeaderboardEntry> memory = new ConcurrentSkipListSet<>();

    @Autowired
    public LeaderboardService(@Autowired(required = false) RedisTemplate<String, Object> redis,
                              @Value("${daedalus.redis.enabled:false}") boolean redisEnabled) {
        this.redis = redis;
        this.redisEnabled = redisEnabled && redis != null;
        if (this.redisEnabled) {
            log.info("LeaderboardService: Redis backend active");
        } else {
            log.info("LeaderboardService: in-memory backend (Redis disabled or unavailable)");
        }
    }

    public void submit(LeaderboardEntry entry) {
        memory.add(entry);
        if (!redisEnabled) return;
        try {
            ZSetOperations<String, Object> zset = redis.opsForZSet();
            zset.add(GLOBAL_KEY, entry, entry.score());
            zset.add(PER_GEN_KEY + entry.mazeGeneratorId(), entry, entry.score());
        } catch (Exception e) {
            log.warn("Redis leaderboard write failed; staying in-memory: {}", e.toString());
        }
    }

    public List<LeaderboardEntry> top(int n) {
        if (redisEnabled) {
            try {
                Set<Object> raw = redis.opsForZSet().reverseRange(GLOBAL_KEY, 0, n - 1);
                if (raw != null) {
                    List<LeaderboardEntry> out = new ArrayList<>();
                    for (Object o : raw) if (o instanceof LeaderboardEntry e) out.add(e);
                    if (!out.isEmpty()) return out;
                }
            } catch (Exception e) {
                log.warn("Redis leaderboard read failed; using in-memory: {}", e.toString());
            }
        }
        List<LeaderboardEntry> out = new ArrayList<>(memory);
        out.sort(Comparator.naturalOrder());
        return out.subList(0, Math.min(n, out.size()));
    }
}
