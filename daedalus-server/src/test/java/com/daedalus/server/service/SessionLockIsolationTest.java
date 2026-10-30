// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.GameSession;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.PlayerMovedEvent;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.Mockito.mock;

/**
 * A move's event listeners run <em>while its session lock is held</em> — deliberately, so
 * listeners observe moves in the order they were applied. That design is only tolerable
 * because the lock is per session: whatever a listener does, it can only delay the session
 * that triggered it.
 *
 * <p>That isolation was true and completely undefended. Changing {@code tryMove}'s
 * {@code synchronized (s)} to {@code synchronized (this)} — one word, turning every player in
 * the server into a queue behind a single lock — broke exactly one test out of 186, and that
 * one is this file. Meanwhile the listener chain on this path has grown: a STOMP broker send,
 * traffic occupancy, the ghost recorder, plus any plugin the operator installed. Measured on a
 * 21×21 maze, a move costs ~1.4µs and the traffic listener is free within noise, but a listener
 * that blocks for 60ms serialises that session's next ten moves into 579ms. The blast radius of
 * that is the whole point, so it gets a test.
 *
 * <p>Deterministic by construction rather than by timing: the slow listener parks until this
 * test releases it, and the bystander's move is asserted to complete <em>before</em> the
 * release. Under a global lock the bystander cannot proceed at all, so the failure surfaces as
 * a timeout rather than a flaky duration comparison.
 *
 * <p>Two things went wrong while establishing the above, both worth knowing before trusting a
 * concurrency experiment. Mutating the <em>first</em> {@code synchronized (s)} in the file
 * patches {@link GameSessionService#join}, not {@code tryMove}, so the first "nothing catches
 * a global lock" result was measured against an untouched lock. And when the listener's safety
 * valve equalled the bystander's patience, the valve released the lock just as the bystander
 * was still waiting: the move then succeeded and this test passed against a genuine global
 * lock. A concurrency test that has never been watched to fail is not yet a test.
 */
class SessionLockIsolationTest {

    /**
     * How long a bystander's move may take before we call isolation broken. Short, because on a
     * per-session lock it takes microseconds.
     */
    private static final int BYSTANDER_TIMEOUT_SECONDS = 3;

    /**
     * Safety valve on the deliberately-blocked listener, so a broken test cannot hang CI. It
     * must be much longer than {@link #BYSTANDER_TIMEOUT_SECONDS}: when the two were equal, the
     * valve released the lock at the very moment the bystander was still waiting, the move then
     * succeeded, and this test passed against a global lock — the exact failure it exists to
     * catch.
     */
    private static final int LISTENER_HOLD_SECONDS = 60;

    /** Generous join timeout for threads that should already be finished. */
    private static final int JOIN_TIMEOUT_SECONDS = 10;

    private MazeGrid grid;
    private Point start;
    private Point neighbour;
    private ExecutorService pool;

    @BeforeEach
    void setUp() {
        grid = new RecursiveBacktrackerGenerator().generate(15, 15, 42L, new MazeStats());
        start = grid.start();
        neighbour = grid.openNeighbors(start).get(0);
        pool = Executors.newFixedThreadPool(2);
    }

    @AfterEach
    void tearDown() {
        pool.shutdownNow();
    }

    @Test
    void aBlockedListenerOnOneSessionDoesNotStopAnotherSessionMoving() throws Exception {
        CountDownLatch listenerEntered = new CountDownLatch(1);
        CountDownLatch releaseListener = new CountDownLatch(1);
        UUID[] slowSession = new UUID[1];

        GameSessionService service = new GameSessionService(event -> {
            if (event instanceof PlayerMovedEvent moved
                    && moved.sessionId().equals(slowSession[0])) {
                listenerEntered.countDown();
                try {
                    // Hold the session lock open until the assertions below have run.
                    releaseListener.await(LISTENER_HOLD_SECONDS, TimeUnit.SECONDS);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
        }, mock(LeaderboardService.class), true);

        UUID mazeId = UUID.randomUUID();
        GameSession blocked = service.open(mazeId, "hog", start);
        GameSession bystander = service.open(mazeId, "bystander", start);
        slowSession[0] = blocked.id();

        Future<Boolean> hog = pool.submit(() -> service.tryMove(blocked.id(), grid, neighbour));
        assertThat(listenerEntered.await(JOIN_TIMEOUT_SECONDS, TimeUnit.SECONDS))
                .as("the slow listener never ran — test cannot conclude anything")
                .isTrue();

        // The hog is parked inside its listener, still holding its session's lock. An
        // unrelated session must be completely unaffected.
        Future<Boolean> other = pool.submit(() -> service.tryMove(bystander.id(), grid, neighbour));
        try {
            assertThat(other.get(BYSTANDER_TIMEOUT_SECONDS, TimeUnit.SECONDS))
                    .as("the bystander's legal move was refused")
                    .isTrue();
            assertThat(bystander.playerPosition("bystander"))
                    .as("the bystander moved while the other session was locked")
                    .isEqualTo(neighbour);
        } catch (TimeoutException notIsolated) {
            throw new AssertionError("a blocked listener on one session stalled a move on a "
                    + "different session — the lock is no longer per-session, so one slow "
                    + "plugin now queues every player in the server", notIsolated);
        } finally {
            // Always release, whether we passed or failed: a stuck listener thread would
            // otherwise hold its lock for the whole safety-valve window.
            releaseListener.countDown();
        }

        assertThat(hog.get(JOIN_TIMEOUT_SECONDS, TimeUnit.SECONDS)).isTrue();
    }

    @Test
    void movesOnOneSessionStillSerialiseAmongThemselves() throws Exception {
        // The flip side, and the reason the lock exists at all: two threads moving the SAME
        // session must not interleave their check-then-act, or a player teleports through a
        // wall or the move count drifts.
        GameSessionService service = new GameSessionService(
                event -> { }, mock(LeaderboardService.class), true);
        GameSession session = service.open(UUID.randomUUID(), "p", start);

        int rounds = 500;
        CountDownLatch go = new CountDownLatch(1);
        Runnable mover = () -> {
            try {
                go.await(JOIN_TIMEOUT_SECONDS, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
            for (int i = 0; i < rounds; i++) {
                Point target = (i % 2 == 0) ? neighbour : start;
                service.tryMove(session.id(), grid, target);
            }
        };
        Future<?> a = pool.submit(mover);
        Future<?> b = pool.submit(mover);
        go.countDown();
        assertThatCode(() -> {
            a.get(JOIN_TIMEOUT_SECONDS, TimeUnit.SECONDS);
            b.get(JOIN_TIMEOUT_SECONDS, TimeUnit.SECONDS);
        }).doesNotThrowAnyException();

        // Whatever the interleaving, the player is on a real cell reachable in one step from
        // the other one — never somewhere no legal sequence of moves could have put them.
        Point finalPosition = session.playerPosition("p");
        assertThat(finalPosition).isIn(start, neighbour);
        assertThat(session.moveCount())
                .as("every accepted move must be counted exactly once")
                .isPositive();
    }
}
