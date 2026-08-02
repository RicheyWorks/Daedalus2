// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.model.MazeStats;
import com.daedalus.theory.MazeMetrics;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.ActiveProfiles;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Every maze the REST surface serves must be solvable — start and goal on carved, mutually
 * reachable cells.
 *
 * <h3>Why this exists</h3>
 *
 * <p>{@code MazeGenerationService} used to pin start at {@code (0,0)} and goal at
 * {@code (rows-1, cols-1)} — corners. Safe for every spanning-tree generator (all cells are
 * carved), silently wrong for {@code DungeonGenerator}, whose corners are solid rock: a
 * REST-generated dungeon had its entrance and exit inside walls, every solver returned
 * {@code success=false}, and a play session could never move. This is the *server-side twin*
 * of the corner-assumption bug the 07-19 audit fixed in `theory` — same assumption, different
 * layer, found by actually looking at the rendered output.
 *
 * <p>The fix reuses {@code MazeMetrics.placeStartAndGoalAtExtremes} (largest-component-seeded,
 * deterministic): dungeons become playable, and spanning-tree mazes get their two
 * farthest-apart cells — the maximum-challenge placement the core recommends — instead of a
 * corner walk. Uses the real service bean over the shared cached context.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")
class MazeGenerationStartGoalTest {

    @LocalServerPort
    private int port; // matches the shared context configuration so it is reused

    @Autowired
    private MazeGenerationService service;

    /**
     * Several seeds, because one is a fixture and six are a property — but read the note below
     * before treating this as the test that holds the corner fix. It is not, and cannot be.
     *
     * <p>Measured on 2026-08-02: deleting {@code placeStartAndGoalAtExtremes} from
     * {@code generate} left every test in this class green. Not seed luck — the 15×21 dungeon's
     * corner cells are rock in 200 of 200 seeds probed. {@code DungeonGenerator} sets its own
     * start and goal inside carved rooms (50/50 seeds, all solvable as generated), so the
     * service-level placement is redundant here and its removal is invisible to any dungeon,
     * at any seed. What does catch it is the diameter equality in
     * {@code aGeneratedPerfectMazeIsSolvableAndUsesTheExtremes} below, because spanning-tree
     * generators do leave the corner defaults in place. {@code mutants/claimteeth.py} keeps
     * asking this question of every test that claims to hold a fix.
     */
    @ParameterizedTest
    @ValueSource(longs = {1L, 3L, 7L, 11L, 19L, 42L})
    void aGeneratedDungeonIsSolvable(long seed) {
        var cached = service.generate("dungeon", 15, 21, seed);
        var grid = cached.grid();

        assertThat(grid.openNeighbors(grid.start()))
                .as("start must be a carved cell, not rock").isNotEmpty();
        assertThat(grid.openNeighbors(grid.goal()))
                .as("goal must be a carved cell, not rock").isNotEmpty();
        assertThat(new BfsSolver().solve(grid, grid.start(), grid.goal(), new MazeStats()))
                .as("a route must exist between the served start and goal").isNotEmpty();
        assertThat(cached.metadata().start()).isEqualTo(grid.start());
        assertThat(cached.metadata().goal()).isEqualTo(grid.goal());
    }

    @Test
    void aGeneratedPerfectMazeIsSolvableAndUsesTheExtremes() {
        var cached = service.generate("recursive-backtracker", 15, 21, 7L);
        var grid = cached.grid();

        var path = new BfsSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());
        assertThat(path).isNotEmpty();
        // Equality, not a bound. The old assertion here was "at least as long as the grid's
        // longer dimension", which a corner-to-corner walk on a 15x21 clears by itself — so it
        // held just as well with the placement deleted. A perfect maze is a tree, which makes
        // the double-BFS placement exact, so the served route must BE the diameter.
        assertThat(path.size() - 1)
                .as("start and goal must be the two farthest-apart cells, not merely far apart")
                .isEqualTo(MazeMetrics.exactDiameter(grid).distance());
    }

    @Test
    void generationIsStillDeterministicPerSeed() {
        var a = service.generate("dungeon", 15, 21, 99L);
        var b = service.generate("dungeon", 15, 21, 99L);
        assertThat(a.grid().start()).isEqualTo(b.grid().start());
        assertThat(a.grid().goal()).isEqualTo(b.grid().goal());
        assertThat(a.grid().toString()).isEqualTo(b.grid().toString());
    }
}
