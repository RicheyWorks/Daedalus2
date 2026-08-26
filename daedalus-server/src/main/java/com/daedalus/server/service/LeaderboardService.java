// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.model.LeaderboardEntry;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentSkipListSet;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

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
    private static final String PER_MAZE_KEY = "daedalus:leaderboard:maze:";
    /** Per-maze boards expire — a maze's runs stop mattering once nobody plays it (and the
     *  daily rolls over after a day), so time is the natural bound on key growth. */
    private static final java.time.Duration PER_MAZE_TTL = java.time.Duration.ofHours(48);

    private final RedisTemplate<String, Object> redis;
    private final boolean redisEnabled;
    private final int maxEntries;
    private final ConcurrentSkipListSet<LeaderboardEntry> memory = new ConcurrentSkipListSet<>();
    /** Guards in-memory add-and-trim; ConcurrentSkipListSet does not make that compound atomic. */
    private final Object memoryLock = new Object();
    private final Counter writeFallback;
    private final AtomicBoolean lastWriteFellBack = new AtomicBoolean();
    private final AtomicReference<String> lastWriteError = new AtomicReference<>();

    /** Default retention — see the three-arg constructor. */
    public LeaderboardService(RedisTemplate<String, Object> redis, boolean redisEnabled) {
        this(redis, redisEnabled, 100);
    }

    /**
     * @param maxEntries retention cap, applied to <em>both</em> backends. The set previously
     *        kept every entry ever submitted — one per completed session, forever. A
     *        leaderboard's whole point is the top of the ordering, so retention past the
     *        deepest page anyone can request ({@code top(n)} caps n at 100) is pure growth.
     *        Trimmed from the worst end on every submit.
     */
    public LeaderboardService(RedisTemplate<String, Object> redis, boolean redisEnabled,
                              int maxEntries) {
        this(redis, redisEnabled, maxEntries, new SimpleMeterRegistry());
    }

    @Autowired
    public LeaderboardService(@Autowired(required = false) RedisTemplate<String, Object> redis,
                              @Value("${daedalus.redis.enabled:false}") boolean redisEnabled,
                              @Value("${daedalus.leaderboard.max-entries:100}") int maxEntries,
                              MeterRegistry meters) {
        this.maxEntries = Math.max(1, maxEntries);
        this.redis = redis;
        this.redisEnabled = redisEnabled && redis != null;
        this.writeFallback = Counter.builder("daedalus.leaderboard.redis.write.fallback")
                .description("Redis leaderboard writes that stayed in-memory")
                .register(meters);
        if (this.redisEnabled) {
            log.info("LeaderboardService: Redis backend active");
        } else {
            log.info("LeaderboardService: in-memory backend (Redis disabled or unavailable)");
        }
    }

    /** Whether Redis is the intended write path. False is a chosen memory board, not a fallback. */
    public boolean redisConfigured() {
        return redisEnabled;
    }

    /** True after a Redis write exception until a later write succeeds. */
    public boolean lastWriteFellBack() {
        return lastWriteFellBack.get();
    }

    /** Last Redis write exception, or null when the last write succeeded or never ran. */
    public String lastWriteError() {
        return lastWriteError.get();
    }

    public void submit(LeaderboardEntry entry) {
        synchronized (memoryLock) {
            memory.add(entry);
            // Natural order is best-first, so pollLast() drops the worst. Size-then-poll
            // without this lock lets two threads both see size == cap+1 and both evict,
            // dropping a run that should have stayed.
            while (memory.size() > maxEntries) {
                memory.pollLast();
            }
        }
        if (!redisEnabled) return;
        try {
            ZSetOperations<String, Object> zset = redis.opsForZSet();
            addAndTrim(zset, GLOBAL_KEY, entry);
            addAndTrim(zset, PER_GEN_KEY + entry.mazeGeneratorId(), entry);
            if (entry.mazeId() != null) {
                String mazeKey = PER_MAZE_KEY + entry.mazeId();
                addAndTrim(zset, mazeKey, entry);
                redis.expire(mazeKey, PER_MAZE_TTL);
            }
            lastWriteFellBack.set(false);
            lastWriteError.set(null);
        } catch (Exception e) {
            // A finished run must stay 200. Two instances then score different boards
            // until Redis writes again — surface that, do not 500 the submit.
            lastWriteFellBack.set(true);
            lastWriteError.set(e.toString());
            writeFallback.increment();
            log.warn("Redis leaderboard write failed; staying in-memory: {}", e.toString());
        }
    }

    /**
     * Writes one entry to a sorted set and drops everything past {@code maxEntries}.
     *
     * <p>The trim is the same argument the in-memory cap makes, applied where it was missing.
     * Only {@code PER_MAZE_KEY} carried a bound before — a 48h TTL — so the global and
     * per-generator sets grew by one member per completed run, forever, holding runs that no
     * request could reach: {@code top(n)} is capped at 100 by the controller and every read is
     * a {@code reverseRange} from rank 0, so rank 101 down was write-only storage. A leaderboard
     * that never forgets is not a feature, it is a slow leak with a scoreboard attached.
     *
     * <p>{@code removeRange(key, 0, -(maxEntries + 1))} deletes by <em>ascending</em> rank, and
     * rank 0 is the lowest score, so this keeps the best {@code maxEntries} and drops the rest —
     * the direction that matters, and the one that is easy to get backwards. On an already-trimmed
     * set it removes nothing and costs an O(log N) lookup, which is why it can run on every write
     * instead of behind a size check that would need its own round trip.
     */
    private void addAndTrim(ZSetOperations<String, Object> zset, String key,
                            LeaderboardEntry entry) {
        zset.add(key, entry, entry.score());
        zset.removeRange(key, 0, -(maxEntries + 1L));
    }

    /**
     * Top-N for one maze — the partition behind the daily challenge's board (and any
     * shared permalink race). In-memory this is a filter over the bounded global set,
     * which is honest at portfolio scale: the retention cap governs how far down a
     * single maze's runs can sit before they age out of the global top. The Redis
     * backend keeps a true per-maze sorted set (48h TTL).
     */
    public List<LeaderboardEntry> top(int n, UUID mazeId) {
        if (mazeId == null) {
            return top(n);
        }
        if (redisEnabled) {
            try {
                Set<Object> raw = redis.opsForZSet()
                        .reverseRange(PER_MAZE_KEY + mazeId, 0, n - 1);
                if (raw != null && !raw.isEmpty()) {
                    List<LeaderboardEntry> out = new ArrayList<>();
                    for (Object o : raw) if (o instanceof LeaderboardEntry e) out.add(e);
                    return out;
                }
            } catch (Exception e) {
                log.warn("Redis per-maze leaderboard read failed; using in-memory: {}",
                        e.toString());
            }
        }
        List<LeaderboardEntry> out = new ArrayList<>();
        for (LeaderboardEntry e : memory) {
            if (mazeId.equals(e.mazeId())) out.add(e);
        }
        out.sort(Comparator.naturalOrder());
        return out.subList(0, Math.min(n, out.size()));
    }

    /**
     * Top-N for one generator — the read path this partition never had.
     *
     * <p>{@code submit} has written {@code PER_GEN_KEY + mazeGeneratorId} since the Redis
     * backend landed, and nothing in the codebase read it: a sorted-set write plus a trim on
     * every completed run, serving no request. That is the same "write-only storage" the trim's
     * own javadoc argues against three lines above it, and it was worse than it looked, because
     * the id being written was the constant {@code "unknown"} — so the partition was not merely
     * unread, it was a single set holding every run on every generator.
     *
     * <p>Comparing algorithms is the thing this project is *about*, so the partition is worth
     * more than the write it costs; the fix is a reader, not a delete. In-memory this filters
     * the bounded global set, exactly as the per-maze board does, and for the same reason: the
     * retention cap is what governs how far down one generator's runs can sit.
     */
    public List<LeaderboardEntry> topByGenerator(int n, String generatorId) {
        if (generatorId == null || generatorId.isBlank()) {
            return top(n);
        }
        if (redisEnabled) {
            try {
                Set<Object> raw = redis.opsForZSet()
                        .reverseRange(PER_GEN_KEY + generatorId, 0, n - 1);
                if (raw != null && !raw.isEmpty()) {
                    List<LeaderboardEntry> out = new ArrayList<>();
                    for (Object o : raw) if (o instanceof LeaderboardEntry e) out.add(e);
                    return out;
                }
            } catch (Exception e) {
                log.warn("Redis per-generator leaderboard read failed; using in-memory: {}",
                        e.toString());
            }
        }
        List<LeaderboardEntry> out = new ArrayList<>();
        for (LeaderboardEntry e : memory) {
            if (generatorId.equals(e.mazeGeneratorId())) out.add(e);
        }
        out.sort(Comparator.naturalOrder());
        return out.subList(0, Math.min(n, out.size()));
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
