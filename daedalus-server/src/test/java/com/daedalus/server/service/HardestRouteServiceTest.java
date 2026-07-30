// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Hardest-route mode (ADR-007 idea 3).
 *
 * <p>The feature's honesty is the thing worth testing. It reports a detour ratio, and the
 * temptation with a number like that is to show it and move on — but on a perfect maze it is
 * necessarily 1.0, because a tree has exactly one simple path between two cells. A test suite
 * that only exercised braided mazes would let a broken loop count or a fabricated "hardest"
 * route pass unnoticed, so both sides are pinned here: the tree case must report exactly 1.0
 * and say why, and the looped case must report a real, strictly longer walk.
 */
class HardestRouteServiceTest {

    private MazeGenerationService gen;
    private HardestRouteService hardest;

    @BeforeEach
    void setUp() {
        gen = new MazeGenerationService(
                new GeneratorRegistry(List.of(
                        new RecursiveBacktrackerGenerator(), new DungeonGenerator())),
                event -> { }, new SimpleMeterRegistry());
        hardest = new HardestRouteService(gen);
    }

    @Test
    void unknownMaze_isNull_soTheControllerCan404() {
        assertThat(hardest.forMaze(UUID.randomUUID())).isNull();
    }

    @Test
    void aPerfectMaze_hasExactlyOneRoute_andSaysSo() {
        var cached = gen.generate("recursive-backtracker", 21, 21, 7L);

        var route = hardest.forMaze(cached.metadata().id());

        assertThat(route.loops()).as("a perfect maze is a tree, so it has no cycles").isZero();
        assertThat(route.hardestLength())
                .as("in a tree the longest simple path IS the only simple path")
                .isEqualTo(route.shortestLength());
        assertThat(route.detour()).isEqualTo(1.0);
        assertThat(route.exact()).isTrue();
        assertThat(route.note()).contains("tree");
        assertWalkable(cached.grid(), route);
    }

    @Test
    void aDungeon_hasLoopsAndAStrictlyCruellerRoute() {
        var cached = gen.generate("dungeon", 21, 21, 7L);

        var route = hardest.forMaze(cached.metadata().id());

        assertThat(route.loops()).as("rooms and corridors make cycles").isPositive();
        assertThat(route.hardestLength())
                .as("with loops to choose between, the hardest route must beat the shortest")
                .isGreaterThan(route.shortestLength());
        assertThat(route.detour()).isGreaterThan(1.0);
        assertWalkable(cached.grid(), route);
    }

    @Test
    void braidingAMazeOpensTheGapThatWasZeroBefore() {
        // The same maze, before and after loops exist — the measurement the feature is for.
        var cached = gen.generate("recursive-backtracker", 21, 21, 11L);
        var before = hardest.forMaze(cached.metadata().id());

        Braider.braid(cached.grid(), 0.5, 11L);
        var after = hardest.forMaze(cached.metadata().id());

        assertThat(before.detour()).isEqualTo(1.0);
        assertThat(after.loops()).isGreaterThan(before.loops());
        assertThat(after.detour())
                .as("braiding is exactly the operation that makes this feature mean something")
                .isGreaterThan(1.5);
        assertWalkable(cached.grid(), after);
    }

    @Test
    void theLoopCountIsTheCyclomaticNumber_notAGuess() {
        // A 2x3 ring is one cycle: 6 cells, 6 passages, one component -> 6 - (6 - 1) = 1.
        MazeGrid ring = new MazeGrid(2, 3);
        ring.carve(new Point(0, 0), new Point(0, 1));
        ring.carve(new Point(0, 1), new Point(0, 2));
        ring.carve(new Point(0, 2), new Point(1, 2));
        ring.carve(new Point(1, 2), new Point(1, 1));
        ring.carve(new Point(1, 1), new Point(1, 0));
        ring.carve(new Point(1, 0), new Point(0, 0));
        var cached = gen.adopt(ring, "hand-built-ring", 0L);

        var route = hardest.forMaze(cached.metadata().id());

        assertThat(route.loops()).isEqualTo(1);
        // Extremes placement puts start and goal on opposite corners of the ring: three steps
        // apart whichever way you walk, so this is also the case where the ratio is exactly 1
        // despite a genuine cycle existing — a loop count above zero does not promise a detour.
        assertThat(route.shortestLength()).isEqualTo(3);
        assertThat(route.hardestLength()).isEqualTo(3);
        assertThat(route.detour()).isEqualTo(1.0);
        assertThat(route.exact()).isTrue();
        assertWalkable(ring, route);
    }

    /** The reported route must be a walk a player could actually take, not just a number. */
    private static void assertWalkable(MazeGrid grid, HardestRouteService.HardestRoute route) {
        List<Point> path = route.path();
        assertThat(path).isNotEmpty();
        assertThat(new HashSet<>(path)).as("simple: no cell entered twice").hasSameSizeAs(path);
        assertThat(path.get(0)).isEqualTo(route.from());
        assertThat(path.get(path.size() - 1)).isEqualTo(route.to());
        assertThat(path).hasSize(route.hardestLength() + 1);
        for (int i = 0; i + 1 < path.size(); i++) {
            assertThat(grid.openNeighbors(path.get(i)))
                    .as("step %d of the route walks through a wall", i)
                    .contains(path.get(i + 1));
        }
    }
}
