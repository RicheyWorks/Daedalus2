// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.GameSession;
import com.daedalus.model.Point;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationEventPublisher;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

/**
 * A living tick can {@code replace()} the cached grid after the controller has
 * already {@code find}d a snapshot and before {@code tryMove} takes the session
 * lock. Agent steps re-read inside {@code computeIfPresent}. Session moves used
 * to keep walking the snapshot, so a newly carved opening was a wall and a
 * just-sealed wall was still a corridor.
 */
class GameSessionLiveGridTest {

    private MazeGenerationService gen;
    private GameSessionService sessions;
    private MazeGenerationService.Cached cached;
    private MazeGrid stale;

    @BeforeEach
    void setUp() {
        ApplicationEventPublisher events = event -> { };
        gen = new MazeGenerationService(
                new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                events, new SimpleMeterRegistry());
        sessions = new GameSessionService(events, mock(LeaderboardService.class));
        cached = gen.generate("recursive-backtracker", 9, 9, 42L);
        stale = cached.grid();
    }

    @Test
    void aNewlyCarvedOpeningIsAcceptedEvenWhenTheSnapshotStillShowsAWall() {
        GameSession s = sessions.open(cached.metadata().id(), "p", stale.start());
        Point from = stale.start();
        Point opened = closedNeighbor(stale, from);
        assertThat(stale.openNeighbors(from)).doesNotContain(opened);

        MazeGrid live = stale.copy();
        live.carve(from, opened);
        swap(live);

        assertThat(sessions.tryMove(s.id(), "p", stale, opened)).isFalse();
        assertThat(s.playerPosition("p")).isEqualTo(from);
        assertThat(sessions.tryMove(s.id(), "p", stale, opened, gen)).isTrue();
        assertThat(s.playerPosition("p")).isEqualTo(opened);
    }

    @Test
    void aJustSealedWallIsRefusedEvenWhenTheSnapshotStillShowsAnOpening() {
        GameSession s = sessions.open(cached.metadata().id(), "p", stale.start());
        Point from = stale.start();
        Point wasOpen = stale.openNeighbors(from).get(0);

        MazeGrid live = stale.copy();
        live.seal(from, wasOpen);
        swap(live);

        assertThat(stale.openNeighbors(from)).contains(wasOpen);
        assertThat(sessions.tryMove(s.id(), "p", stale, wasOpen, gen)).isFalse();
        assertThat(s.playerPosition("p")).isEqualTo(from);
    }

    private void swap(MazeGrid live) {
        assertThat(gen.replace(cached.metadata().id(),
                new MazeGenerationService.Cached(cached.metadata(), live, cached.stats(),
                        cached.hotspots(), cached.braid()))).isTrue();
    }

    private static Point closedNeighbor(MazeGrid grid, Point from) {
        for (Point n : grid.neighbors(from)) {
            if (!grid.openNeighbors(from).contains(n)) {
                return n;
            }
        }
        throw new AssertionError("start " + from + " has no closed neighbour on a tree");
    }
}
