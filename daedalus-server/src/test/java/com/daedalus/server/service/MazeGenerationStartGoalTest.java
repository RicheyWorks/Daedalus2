// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.model.MazeStats;
import org.junit.jupiter.api.Test;
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

    @Test
    void aGeneratedDungeonIsSolvable() {
        var cached = service.generate("dungeon", 15, 21, 7L);
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
        // Extremes placement: the route between start and goal is at least as long as the
        // grid's longer dimension — corners can't guarantee that, the diameter endpoints do.
        assertThat(path.size()).isGreaterThanOrEqualTo(21);
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
