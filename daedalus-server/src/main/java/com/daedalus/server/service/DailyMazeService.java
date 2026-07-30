// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.LocalDate;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * The daily maze (ADR-006 idea #4): one shared challenge per UTC day. The seed derives from
 * the date alone, so every instance — today's server, a restarted server, a second replica —
 * generates the <em>same topology</em> without any coordination or storage. That is the whole
 * trick: determinism the project already guarantees end-to-end (generator seeds, extremes
 * start/goal placement) turns "shared daily challenge" into a pure convention.
 *
 * <p>Generation is lazy (first request of the day pays the ~ms cost) and the date→id map
 * self-prunes to the last few days, so this adds no unbounded store (house rule,
 * 2026-07-29 audit). If the maze cache evicts the day's maze (2h idle TTL on a quiet
 * server), the next request regenerates it — same seed, same maze, new id — rather than
 * pinning cache entries or resurrecting evicted ones.
 */
@Service
public class DailyMazeService {

    /** Today's date (UTC) and its maze. */
    public record Daily(LocalDate date, MazeGenerationService.Cached maze) {}

    private final MazeGenerationService gen;
    private final String generatorId;
    private final int rows;
    private final int cols;
    private final Clock clock;

    private final ConcurrentHashMap<LocalDate, UUID> byDate = new ConcurrentHashMap<>();

    @Autowired
    public DailyMazeService(MazeGenerationService gen,
            @Value("${daedalus.daily.generator-id:recursive-backtracker}") String generatorId,
            @Value("${daedalus.daily.rows:21}") int rows,
            @Value("${daedalus.daily.cols:21}") int cols) {
        this(gen, generatorId, rows, cols, Clock.systemUTC());
    }

    /** Test seam: inject the clock to cross day boundaries deterministically. */
    DailyMazeService(MazeGenerationService gen, String generatorId, int rows, int cols,
                     Clock clock) {
        this.gen = gen;
        this.generatorId = generatorId;
        this.rows = rows;
        this.cols = cols;
        this.clock = clock;
    }

    /** Today's maze — generated on first request, identical for every caller until midnight UTC. */
    public Daily today() {
        LocalDate date = LocalDate.now(clock);
        byDate.keySet().removeIf(d -> d.isBefore(date.minusDays(2))); // self-pruning, stays tiny

        while (true) {
            UUID id = byDate.get(date);
            if (id != null) {
                var cached = gen.find(id);
                if (cached != null) {
                    return new Daily(date, cached);
                }
                byDate.remove(date, id); // evicted from the maze cache — regenerate (same seed)
                continue;
            }
            var fresh = gen.generate(generatorId, rows, cols, seedFor(date));
            UUID winner = byDate.putIfAbsent(date, fresh.metadata().id());
            if (winner == null) {
                return new Daily(date, fresh);
            }
            // Lost a first-request race: the winner's maze is the canonical one for the day
            // (the loser's copy is topologically identical anyway — same seed). Loop to fetch.
        }
    }

    /**
     * Date → seed, stable across instances and restarts by construction (epoch day spread by
     * the 64-bit golden ratio so consecutive days land far apart in seed space).
     */
    static long seedFor(LocalDate date) {
        return date.toEpochDay() * 0x9E3779B97F4A7C15L;
    }
}
