// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.model.LeaderboardEntry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;

import java.time.Instant;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.NavigableSet;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * The Redis sorted sets are bounded, and bounded from the correct end.
 *
 * <h3>Why this exists</h3>
 *
 * <p>Until 2026-08-01 only the per-maze key had a bound (a 48h TTL). The global and
 * per-generator sets gained a member on every completed run and lost one never, which the
 * constructor's javadoc described as keeping "full history". Nothing could read that history:
 * {@code MazeController} caps {@code n} at 100 and every read is a {@code reverseRange} from
 * rank 0, so rank 101 downwards was storage no request could reach. The in-memory set had
 * carried the identical argument in its own javadoc — "retention past the deepest page anyone
 * can request is pure growth" — and had been capped for it. Only the Redis half was exempt.
 *
 * <h3>Why the fake, rather than verifying a call</h3>
 *
 * <p>Asserting {@code verify(zset).removeRange(key, 0, -101)} would pass on a trim that deletes
 * the <em>best</em> entries instead of the worst, which is the one mistake this code is actually
 * prone to: {@code removeRange} works on ascending rank while every read here is descending, so
 * the correct call looks backwards at a glance. The fake below implements enough real sorted-set
 * semantics — score ordering, rank windows, negative indices — that the tests can assert on
 * <em>which entries survive</em>. A test that asserts on arguments proves the call was made; only
 * state proves it was the right call.
 */
class LeaderboardRedisRetentionTest {

    private static final int CAP = 5;
    private static final String GLOBAL = "daedalus:leaderboard:global";
    private static final String PER_GEN = "daedalus:leaderboard:gen:recursive-backtracker";

    private FakeZSets sets;
    private LeaderboardService svc;

    @BeforeEach
    @SuppressWarnings("unchecked")
    void wireFakeRedis() {
        sets = new FakeZSets();
        RedisTemplate<String, Object> redis = mock(RedisTemplate.class);
        ZSetOperations<String, Object> ops = mock(ZSetOperations.class);

        when(redis.opsForZSet()).thenReturn(ops);
        when(ops.add(anyString(), any(), org.mockito.ArgumentMatchers.anyDouble()))
                .thenAnswer(i -> sets.add(i.getArgument(0), i.getArgument(1), i.getArgument(2)));
        when(ops.removeRange(anyString(), anyLong(), anyLong()))
                .thenAnswer(i -> sets.removeRange(i.getArgument(0), i.getArgument(1),
                        i.getArgument(2)));
        when(ops.reverseRange(anyString(), anyLong(), anyLong()))
                .thenAnswer(i -> sets.reverseRange(i.getArgument(0), i.getArgument(1),
                        i.getArgument(2)));

        svc = new LeaderboardService(redis, true, CAP);
    }

    private static LeaderboardEntry entry(UUID mazeId, String player, long score) {
        return new LeaderboardEntry(UUID.randomUUID(), mazeId, player, score, 10, 1000,
                "recursive-backtracker", Instant.now());
    }

    @Test
    void theGlobalSetStopsGrowingAtTheCap() {
        for (int i = 1; i <= CAP * 6; i++) {
            svc.submit(entry(null, "player" + i, i * 100L));
        }

        assertThat(sets.size(GLOBAL))
                .as("one member per completed run and no eviction is an unbounded set; the "
                        + "backend is supposed to hold a leaderboard, not an archive")
                .isEqualTo(CAP);
    }

    @Test
    void theTrimDropsTheWorstEntriesAndNotTheBest() {
        // Submitted worst-first, so a trim aimed at the wrong end would leave exactly the
        // entries this asserts are gone — and a size-only assertion could not tell the two apart.
        for (int i = 1; i <= CAP * 6; i++) {
            svc.submit(entry(null, "player" + i, i * 100L));
        }

        assertThat(sets.membersOf(GLOBAL))
                .extracting(e -> ((LeaderboardEntry) e).playerName())
                .as("removeRange works on ascending rank while every read here is descending, "
                        + "so the surviving set is the only honest check on the direction")
                .containsExactlyInAnyOrder("player26", "player27", "player28", "player29",
                        "player30");
    }

    @Test
    void everyPartitionIsBoundedNotJustTheGlobalOne() {
        UUID daily = UUID.randomUUID();
        for (int i = 1; i <= CAP * 4; i++) {
            svc.submit(entry(daily, "player" + i, i * 100L));
        }

        assertThat(sets.size(PER_GEN))
                .as("22 generators means 22 of these sets; unbounded each is 22 leaks")
                .isEqualTo(CAP);
        assertThat(sets.size("daedalus:leaderboard:maze:" + daily))
                .as("the per-maze TTL bounds how long the key lives, not how large it gets — "
                        + "a maze played hard for 48h still needs the rank bound")
                .isEqualTo(CAP);
    }

    @Test
    void trimmingDoesNotDisturbWhatReadsReturn() {
        for (int i = 1; i <= CAP * 6; i++) {
            svc.submit(entry(null, "player" + i, i * 100L));
        }

        assertThat(svc.top(3))
                .extracting(LeaderboardEntry::playerName)
                .as("the board is still the board — best first, unaffected by the eviction "
                        + "happening underneath it")
                .containsExactly("player30", "player29", "player28");
    }

    /**
     * Enough of a Redis sorted set to be worth asserting against: members ordered by score
     * ascending (insertion order breaking ties, as member ordering does in Redis), rank windows
     * inclusive at both ends, and negative indices counting back from the end.
     */
    private static final class FakeZSets {
        private record Member(double score, long seq, Object value) { }

        private final Map<String, NavigableSet<Member>> keys = new HashMap<>();
        private long seq;

        private NavigableSet<Member> set(String key) {
            return keys.computeIfAbsent(key, k -> new TreeSet<>(
                    Comparator.comparingDouble(Member::score).thenComparingLong(Member::seq)));
        }

        boolean add(String key, Object value, double score) {
            NavigableSet<Member> s = set(key);
            boolean existed = s.removeIf(m -> m.value().equals(value));
            s.add(new Member(score, seq++, value));
            return !existed;
        }

        /** Ascending rank, inclusive, negative indices relative to the end — as ZREMRANGEBYRANK. */
        long removeRange(String key, long start, long end) {
            List<Member> ordered = List.copyOf(set(key));
            int n = ordered.size();
            int from = (int) (start < 0 ? Math.max(0, n + start) : Math.min(start, n));
            int to = (int) (end < 0 ? n + end : Math.min(end, n - 1L));
            if (from > to || n == 0) {
                return 0;
            }
            List<Member> doomed = ordered.subList(from, to + 1);
            set(key).removeAll(doomed);
            return doomed.size();
        }

        /** Descending rank, inclusive — as ZREVRANGE. */
        Set<Object> reverseRange(String key, long start, long end) {
            List<Member> descending = List.copyOf(set(key).descendingSet());
            int n = descending.size();
            int from = (int) Math.min(Math.max(start, 0), n);
            int to = (int) (end < 0 ? n + end : Math.min(end, n - 1L));
            Set<Object> out = new LinkedHashSet<>();
            for (int i = from; i <= to && i < n; i++) {
                out.add(descending.get(i).value());
            }
            return out;
        }

        int size(String key) {
            return set(key).size();
        }

        List<Object> membersOf(String key) {
            return set(key).stream().map(Member::value).toList();
        }
    }
}
