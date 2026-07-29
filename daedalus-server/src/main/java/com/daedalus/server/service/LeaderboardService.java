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
    private final int maxEntries;
    private final ConcurrentSkipListSet<LeaderboardEntry> memory = new ConcurrentSkipListSet<>();

    /** Default retention — see the three-arg constructor. */
    public LeaderboardService(RedisTemplate<String, Object> redis, boolean redisEnabled) {
        this(redis, redisEnabled, 100);
    }

    /**
     * @param maxEntries in-memory retention cap. The set previously kept every entry ever
     *        submitted — one per completed session, forever. A leaderboard's whole point is
     *        the top of the ordering, so retention past the deepest page anyone can request
     *        ({@code top(n)} caps n at 100) is pure growth. Trimmed from the worst end on
     *        every submit; the Redis backend keeps full history independently.
     */
    @Autowired
    public LeaderboardService(@Autowired(required = false) RedisTemplate<String, Object> redis,
                              @Value("${daedalus.redis.enabled:false}") boolean redisEnabled,
                              @Value("${daedalus.leaderboard.max-entries:100}") int maxEntries) {
        this.maxEntries = Math.max(1, maxEntries);
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
        // Natural order is best-first, so pollLast() drops the worst. Approximate under
        // concurrent submits, exact at rest — fine for a cap whose only job is boundedness.
        while (memory.size() > maxEntries) {
            memory.pollLast();
        }
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
