// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.GameSession;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.PlayerMovedEvent;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationEventPublisher;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

/**
 * Pins session check-then-act per session (TESTING.md, gap P3 — promoted from "only if
 * inspection finds check-then-act": it did). {@code tryMove} was already locked;
 * {@code GameSession.join}'s last-seat bound was not.
 *
 * <h3>Why this exists</h3>
 *
 * <p>Sessions live in a {@code ConcurrentHashMap}, which protects the <em>map</em>, not
 * compound operations on one {@link GameSession} — and {@code tryMove} is exactly such a
 * compound: read position, validate against the grid, write position. Two tabs or a reconnect
 * race make concurrent calls on the same session realistic. Unsynchronized, two racing moves
 * can both validate against the same stale position (an illegal transition slips through),
 * lose a {@code moveCount} increment ({@code long++} is not atomic), or both drive the winning
 * move to completion (two leaderboard entries for one win).
 *
 * <p>Replayed against the pre-fix (unsynchronized) {@code tryMove} per the house rule: the
 * hammer test breaks the event chain / move accounting and the goal race double-submits,
 * within a few hundred rounds on every run tried. These tests are probabilistic by nature —
 * a race that slips through one run is not proof of safety — but the fixed implementation
 * makes the asserted invariants hold by construction, so for the pinned code they are
 * deterministic.
 *
 * <p>Semantics pinned deliberately: a racing move is re-validated against the position the
 * winner left behind — it either becomes a legal move from the <em>new</em> position or is
 * rejected. It is never applied against a stale read.
 */
class GameSessionServiceConcurrencyTest {

    private static final int THREADS = 4;
    private static final int ROUNDS = 500;

    private LeaderboardService leaderboard;
    private GameSessionService service;
    private List<PlayerMovedEvent> published;
    private MazeGrid grid;

    @BeforeEach
    void setUp() {
        leaderboard = mock(LeaderboardService.class);
        published = Collections.synchronizedList(new ArrayList<>());
        ApplicationEventPublisher capture = event -> {
            if (event instanceof PlayerMovedEvent moved) {
                published.add(moved);
            }
        };
        service = new GameSessionService(capture, leaderboard);
        // A real perfect maze, not a hand-built fixture — house rule. 16x16, fixed seed.
        grid = new RecursiveBacktrackerGenerator().generate(16, 16, 42L, new MazeStats());
        grid.setStart(new Point(0, 0));
        grid.setGoal(new Point(15, 15));
    }

    /**
     * The hammer: {@code THREADS} threads x {@code ROUNDS} barrier-aligned rounds, all
     * attacking the same session. Every thread reads the current position (deliberately
     * outside any lock — that is the client's reality) and races a move to one of its open
     * neighbors. Afterwards, two invariants that only hold if tryMove is atomic per session:
     * the published events form one contiguous chain (each move departs from exactly where
     * the previous move arrived), and every successful move was counted.
     */
    @Test
    void concurrentMovesOnOneSessionFormOneContiguousLegalChain() throws Exception {
        GameSession session = service.open(UUID.randomUUID(), "racer", grid.start());
        AtomicLong successes = new AtomicLong();
        CyclicBarrier round = new CyclicBarrier(THREADS);
        ExecutorService pool = Executors.newFixedThreadPool(THREADS);
        CountDownLatch done = new CountDownLatch(THREADS);

        for (int t = 0; t < THREADS; t++) {
            final int lane = t;
            pool.submit(() -> {
                try {
                    for (int i = 0; i < ROUNDS; i++) {
                        round.await(10, TimeUnit.SECONDS);
                        Point from = session.currentPosition();          // stale by design
                        List<Point> exits = grid.openNeighbors(from);
                        Point to = exits.get((lane + i) % exits.size()); // lanes diverge
                        if (service.tryMove(session.id(), grid, to)) {
                            successes.incrementAndGet();
                        }
                    }
                } catch (Exception e) {
                    throw new IllegalStateException(e);
                } finally {
                    done.countDown();
                }
            });
        }
        assertThat(done.await(60, TimeUnit.SECONDS)).as("workers finished").isTrue();
        pool.shutdown();

        assertThat(published).as("every success published exactly one event")
                .hasSize((int) successes.get());
        assertThat(session.moveCount()).as("no lost moveCount increments (long++ races)")
                .isEqualTo(successes.get());
        Point at = grid.start();
        for (int i = 0; i < published.size(); i++) {
            PlayerMovedEvent e = published.get(i);
            assertThat(e.from())
                    .as("event %d departs from where event %d arrived — no move applied "
                            + "against a stale position read", i, i - 1)
                    .isEqualTo(at);
            assertThat(grid.openNeighbors(e.from()))
                    .as("event %d is a legal step", i).contains(e.to());
            at = e.to();
        }
        assertThat(session.currentPosition()).isEqualTo(at);
    }

    /** Two threads race the winning move into the goal: exactly one wins, one leaderboard row. */
    @Test
    void racingTheWinningMoveCompletesTheSessionExactlyOnce() throws Exception {
        Point nextToGoal = grid.openNeighbors(grid.goal()).get(0);
        for (int attempt = 0; attempt < 200; attempt++) {
            leaderboard = mock(LeaderboardService.class);
            service = new GameSessionService(event -> { }, leaderboard);
            GameSession session = service.open(UUID.randomUUID(), "racer", nextToGoal);

            CyclicBarrier go = new CyclicBarrier(2);
            ExecutorService pool = Executors.newFixedThreadPool(2);
            List<Boolean> results = Collections.synchronizedList(new ArrayList<>());
            for (int t = 0; t < 2; t++) {
                pool.submit(() -> {
                    go.await(10, TimeUnit.SECONDS);
                    results.add(service.tryMove(session.id(), grid, grid.goal()));
                    return null;
                });
            }
            pool.shutdown();
            assertThat(pool.awaitTermination(30, TimeUnit.SECONDS)).isTrue();

            assertThat(results).as("exactly one racer lands the winning move")
                    .containsExactlyInAnyOrder(true, false);
            assertThat(session.completed()).isTrue();
            verify(leaderboard, times(1)).submit(any());
        }
    }

    /**
     * Last seat, two names, one slot. The map-level {@code join} used to let both through;
     * the service lock hid it from HTTP until a core pin forced the seat cap onto the
     * session itself. This is the same race on the service API: exactly one
     * {@code JoinRefusedException.FULL}, size stays {@code MAX_PLAYERS}.
     */
    @Test
    void twoThreadsCannotBothTakeTheLastJoinSlot() throws Exception {
        service = new GameSessionService(event -> { }, leaderboard, true);
        Point start = grid.start();
        for (int attempt = 0; attempt < 200; attempt++) {
            GameSession session = service.open(UUID.randomUUID(), "Alice", start);
            for (int i = 1; i <= GameSession.MAX_PLAYERS - 2; i++) {
                assertThat(service.join(session.id(), "p" + i, start)).isSameAs(session);
            }
            assertThat(session.players()).hasSize(GameSession.MAX_PLAYERS - 1);

            CyclicBarrier go = new CyclicBarrier(2);
            ExecutorService pool = Executors.newFixedThreadPool(2);
            List<Object> results = Collections.synchronizedList(new ArrayList<>());
            pool.submit(() -> raceServiceJoin(session.id(), "x", start, go, results));
            pool.submit(() -> raceServiceJoin(session.id(), "y", start, go, results));
            pool.shutdown();
            assertThat(pool.awaitTermination(30, TimeUnit.SECONDS)).isTrue();

            long accepted = results.stream().filter(r -> r instanceof GameSession).count();
            long full = results.stream()
                    .filter(r -> r instanceof GameSessionService.JoinRefusedException ex
                            && ex.reason() == GameSessionService.JoinRefusedException.Reason.FULL)
                    .count();
            assertThat(accepted).as("exactly one name sits down").isEqualTo(1);
            assertThat(full).as("the other name is FULL, not a silent extra seat").isEqualTo(1);
            assertThat(session.players()).hasSize(GameSession.MAX_PLAYERS);
            assertThat(session.completed()).isFalse();
        }
    }

    private void raceServiceJoin(UUID sessionId, String name, Point start,
                                 CyclicBarrier go, List<Object> results) {
        try {
            go.await(10, TimeUnit.SECONDS);
            results.add(service.join(sessionId, name, start));
        } catch (GameSessionService.JoinRefusedException refused) {
            results.add(refused);
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    /** Single-threaded contract the lock must not disturb: completed sessions reject moves. */
    @Test
    void movesAfterCompletionAreRejected() {
        Point nextToGoal = grid.openNeighbors(grid.goal()).get(0);
        GameSession session = service.open(UUID.randomUUID(), "solo", nextToGoal);

        assertThat(service.tryMove(session.id(), grid, grid.goal())).isTrue();
        assertThat(session.completed()).isTrue();
        long movesAtCompletion = session.moveCount();

        assertThat(service.tryMove(session.id(), grid, nextToGoal)).isFalse();
        assertThat(session.moveCount()).isEqualTo(movesAtCompletion);
    }
}
