// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.api.dto.Hotspot;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.solvers.DijkstraSolver;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Weighted mazes over the API (the ADR-004 weighted-shading trigger, fired for real): a
 * {@code hotspots} list on generation makes the cached grid a {@link WeightedMazeGrid}, and
 * the weight-aware solvers route around expensive cells wherever the topology offers a
 * choice.
 *
 * <p>The detour test is the one that matters and it is deliberately built on a <b>dungeon</b>:
 * a perfect maze has exactly one route between any pair of cells, so no weight can change the
 * path — rooms and loops are where weighted routing exists at all. It places the hotspot ON
 * the unweighted shortest route and asserts the weighted route avoids it; against a build
 * where hotspots are ignored, the path is byte-identical and the test fails.
 */
class WeightedMazeApiTest {

    private static MazeGenerationService service() {
        return new MazeGenerationService(
                new GeneratorRegistry(List.of(new DungeonGenerator())),
                event -> { }, new SimpleMeterRegistry());
    }

    @Test
    void hotspotsMakeTheServedGridWeighted() {
        var cached = service().generate("dungeon", 15, 21, 7L,
                List.of(new Hotspot(3, 4, 25.0)));

        assertThat(cached.grid()).isInstanceOf(WeightedMazeGrid.class);
        assertThat(((WeightedMazeGrid) cached.grid()).weightOf(new Point(3, 4))).isEqualTo(25.0);
        assertThat(cached.hotspots()).containsExactly(new Hotspot(3, 4, 25.0));
    }

    @Test
    void uniformRequestsStayPlainGridsWithNoHotspotEcho() {
        var cached = service().generate("dungeon", 15, 21, 7L, null);
        assertThat(cached.grid()).isNotInstanceOf(WeightedMazeGrid.class);
        assertThat(cached.hotspots()).isNull();
    }

    @Test
    void dijkstraDetoursAroundAHotspotPlacedOnItsOwnBestRoute() {
        MazeGenerationService svc = service();

        // Unweighted best route on a loopy dungeon.
        var plain = svc.generate("dungeon", 15, 21, 7L, null);
        List<Point> before = new DijkstraSolver().solve(
                plain.grid(), plain.grid().start(), plain.grid().goal(), new MazeStats());
        assertThat(before).isNotEmpty();

        // Drop a prohibitively expensive hotspot on every interior cell of that route until
        // one produces a detour — a dungeon has loops, but not every route cell has an
        // alternative (corridor chokepoints don't). The assertion is that AT LEAST ONE does:
        // a topology with rooms where no weight can ever change any route would mean
        // weighted routing is theater, and this test exists to prove it is not.
        boolean detoured = false;
        for (int i = 1; i < before.size() - 1 && !detoured; i++) {
            Point blocked = before.get(i);
            var weighted = svc.generate("dungeon", 15, 21, 7L,
                    List.of(new Hotspot(blocked.row(), blocked.col(), 1000.0)));
            List<Point> after = new DijkstraSolver().solve(
                    weighted.grid(), weighted.grid().start(), weighted.grid().goal(),
                    new MazeStats());
            if (!after.isEmpty() && !after.contains(blocked)) {
                detoured = true;
                // The detour must still be a legal route between the same endpoints.
                assertThat(after.get(0)).isEqualTo(weighted.grid().start());
                assertThat(after.get(after.size() - 1)).isEqualTo(weighted.grid().goal());
            }
        }
        assertThat(detoured)
                .as("some cell of the unweighted route must be avoidable when made expensive")
                .isTrue();
    }

    @Test
    void outOfBoundsHotspotIsACallerError() {
        assertThatThrownBy(() -> service().generate("dungeon", 15, 21, 7L,
                List.of(new Hotspot(99, 99, 10.0))))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("outside");
    }
}
