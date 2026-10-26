// SPDX-License-Identifier: MIT

package com.daedalus.model;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Session ownership and the join allowlist (ADR-012). The interceptor lives in the
 * server module; the decision it asks is here, so a core-only {@code mvn test} has
 * to pin it — the same hole {@link LeaderboardEntryOrderingTest} exists to close.
 */
class GameSessionTest {

    private static GameSession owned() {
        return new GameSession(UUID.randomUUID(), "Alice", new Point(0, 0), "alice");
    }

    @Test
    void unownedSessionsAdmitAnyone() {
        GameSession s = new GameSession(UUID.randomUUID(), "anon", new Point(0, 0));
        assertThat(s.maySubscribe(null)).isTrue();
        assertThat(s.maySubscribe("mallory")).isTrue();
    }

    @Test
    void anOwnedSessionAdmitsTheOwnerAndRefusesEveryoneElse() {
        GameSession s = owned();
        assertThat(s.maySubscribe("alice")).isTrue();
        assertThat(s.maySubscribe("mallory")).isFalse();
        assertThat(s.maySubscribe(null)).isFalse();
    }

    @Test
    void joiningWithASubjectGrantsSubscribe() {
        GameSession s = owned();
        assertThat(s.join("Bob", new Point(0, 0), "bob")).isTrue();
        assertThat(s.maySubscribe("bob")).isTrue();
        assertThat(s.maySubscribe("mallory")).isFalse();
    }

    @Test
    void anAnonymousJoinPutsAPieceOnTheBoardWithoutGrantingTheFeed() {
        GameSession s = owned();
        assertThat(s.join("Bob", new Point(0, 0))).isTrue();
        assertThat(s.players()).containsKey("Bob");
        assertThat(s.maySubscribe("bob")).isFalse();
    }

    @Test
    void rejoiningDoesNotTeleportAndDoesNotHandTheSeatToADifferentSubject() {
        GameSession s = owned();
        s.join("Bob", new Point(0, 0), "bob");
        s.move("Bob", new Point(1, 0));

        assertThat(s.join("Bob", new Point(0, 0), "mallory")).isTrue();
        assertThat(s.playerPosition("Bob")).isEqualTo(new Point(1, 0));
        assertThat(s.maySubscribe("bob")).isTrue();
        assertThat(s.maySubscribe("mallory")).isFalse();
    }

    /**
     * {@code join} is check-then-act: read {@code size()}, then {@code putIfAbsent}.
     * {@code ConcurrentHashMap} does not make that compound atomic, so two names racing
     * the last seat can both pass the bound and land a ninth player. Replay against
     * the unsynchronized body overflowed within this loop on every run tried.
     */
    @Test
    void twoThreadsCannotBothTakeTheLastSeat() throws Exception {
        Point start = new Point(0, 0);
        for (int attempt = 0; attempt < 200; attempt++) {
            GameSession s = owned();
            for (int i = 1; i <= GameSession.MAX_PLAYERS - 2; i++) {
                assertThat(s.join("p" + i, start)).isTrue();
            }
            assertThat(s.players()).hasSize(GameSession.MAX_PLAYERS - 1);

            CyclicBarrier go = new CyclicBarrier(2);
            ExecutorService pool = Executors.newFixedThreadPool(2);
            List<Boolean> results = Collections.synchronizedList(new ArrayList<>());
            CountDownLatch done = new CountDownLatch(2);
            pool.submit(() -> raceJoin(s, "x", start, go, results, done));
            pool.submit(() -> raceJoin(s, "y", start, go, results, done));
            assertThat(done.await(10, TimeUnit.SECONDS)).isTrue();
            pool.shutdown();

            assertThat(results).as("exactly one racer takes the last seat")
                    .containsExactlyInAnyOrder(true, false);
            assertThat(s.players()).hasSize(GameSession.MAX_PLAYERS);
            assertThat(s.players().keySet()).containsAnyOf("x", "y");
            assertThat(s.players().containsKey("x") && s.players().containsKey("y")).isFalse();
        }
    }

    private static void raceJoin(GameSession s, String name, Point start, CyclicBarrier go,
                                 List<Boolean> results, CountDownLatch done) {
        try {
            go.await(10, TimeUnit.SECONDS);
            results.add(s.join(name, start, name));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        } finally {
            done.countDown();
        }
    }

    @Test
    void aFullSessionRefusesANewNameAndStillAcceptsARejoin() {
        GameSession s = owned();
        for (int i = 1; i < GameSession.MAX_PLAYERS; i++) {
            assertThat(s.join("p" + i, new Point(0, 0), "s" + i)).isTrue();
        }
        assertThat(s.players()).hasSize(GameSession.MAX_PLAYERS);
        assertThat(s.join("overflow", new Point(0, 0), "overflow")).isFalse();
        assertThat(s.players()).doesNotContainKey("overflow");
        assertThat(s.maySubscribe("overflow")).isFalse();

        assertThat(s.join("p1", new Point(0, 0), "impostor")).isTrue();
        assertThat(s.maySubscribe("s1")).isTrue();
        assertThat(s.maySubscribe("impostor")).isFalse();
    }

    @Test
    void aJoinersHopsAreRecordedAndAreNotGhostMaterial() {
        GameSession s = owned();
        s.join("Bob", new Point(0, 0), "bob");
        s.move("Alice", new Point(0, 1));
        s.move("Bob", new Point(1, 0));
        s.move("Bob", new Point(1, 1));

        assertThat(s.trail()).extracting(GameSession.TimedMove::to)
                .containsExactly(new Point(0, 1));
        assertThat(s.walks()).containsOnlyKeys("Alice", "Bob");
        assertThat(s.walks().get("Bob")).extracting(GameSession.TimedMove::to)
                .containsExactly(new Point(1, 0), new Point(1, 1));
        assertThat(s.walks().get("Alice")).isEqualTo(s.trail());
    }

    @Test
    void completeRecordsTheWinnerNotTheOpener() {
        GameSession s = owned();
        s.join("Bob", new Point(0, 0), "bob");
        s.complete(99, "Bob");
        assertThat(s.completed()).isTrue();
        assertThat(s.completedBy()).isEqualTo("Bob");
        assertThat(s.score()).isEqualTo(99);
        assertThat(s.playerName()).isEqualTo("Alice");
    }
}
