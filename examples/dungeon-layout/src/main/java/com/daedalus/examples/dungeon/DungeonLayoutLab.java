// SPDX-License-Identifier: MIT

package com.daedalus.examples.dungeon;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.theory.FacilityPlacement;
import com.daedalus.theory.LongestPath;
import com.daedalus.theory.MazeMetrics;

import java.util.ArrayList;
import java.util.List;

/**
 * Daedalus as the spatial layer under a narrative game engine.
 *
 * <p>ai-dungeon-master already generates the <em>story</em>: its own {@code DungeonGenerator}
 * produces loot, allies, enemies and quests, and its {@code WorldMap} holds a
 * {@code List<String>} of discovered locations. What it has no notion of is <em>geometry</em> —
 * there is no layout, no distance, no notion of one room being deeper than another. That is
 * exactly the gap this engine fills, and nothing in either project has to change for it to.
 *
 * <p>Four questions a level designer asks, each answered by an existing `theory` class:
 *
 * <ol>
 *   <li><b>What does the level look like?</b> {@code DungeonGenerator} — BSP rooms joined by
 *       corridors, deliberately <em>not</em> a perfect maze, because rooms with one entrance
 *       make bad dungeons.</li>
 *   <li><b>How deep is it?</b> {@code MazeMetrics} diameter — the longest shortest-path in the
 *       level. Note this example uses {@link MazeMetrics#exactDiameter} rather than the fast
 *       estimate: a dungeon is braided by construction, and on a looped graph the two-sweep
 *       estimate can read up to 20% short.</li>
 *   <li><b>What is the hardest route through it?</b> {@code LongestPath} — the longest
 *       <em>simple</em> path from entrance to boss. This is NP-hard, so the answer is exact
 *       within a search budget and a lower bound beyond it; the {@code exact} flag says
 *       which.</li>
 *   <li><b>Where do treasure and save points go?</b> {@code FacilityPlacement.kCenter} —
 *       spread them so the worst-served room is as close as possible to one. The plain
 *       variant is the right one here: unreachable cells are solid rock, not places, so they
 *       should neither be served nor distort the radius. (The
 *       {@code kCenterAcrossComponents} variant exists for partitioned <em>networks</em>,
 *       where every fragment still holds real nodes.)</li>
 * </ol>
 *
 * <p>The output is deliberately shaped as named locations — {@link Location} — because that is
 * what a narrative engine consumes. Daedalus decides where things are; the game decides what
 * they mean.
 */
public final class DungeonLayoutLab {

    private static final int ROWS = 33;
    private static final int COLS = 33;
    private static final long SEED = 20260719L;

    private DungeonLayoutLab() {
    }

    /**
     * A place in the level, ready to be handed to a narrative engine.
     *
     * @param name     a stable identifier the story layer can attach content to
     * @param cell     where it sits in the grid
     * @param depth    steps from the entrance — a natural difficulty gradient
     * @param kind     what the level designer intends it to be
     */
    public record Location(String name, Point cell, int depth, String kind) {
    }

    public static void main(String[] args) {
        MazeGrid level = buildLevel();
        report(level);
    }

    /**
     * A dungeon, then braided. {@code DungeonGenerator} already produces loops, and braiding
     * removes the remaining dead-end stubs — corridors that go nowhere are a level-design
     * smell, and they also make every route forced, which flattens the "hardest route"
     * question into a triviality.
     */
    static MazeGrid buildLevel() {
        MazeGrid level = new DungeonGenerator().generate(ROWS, COLS, SEED, new MazeStats());
        Braider.braid(level, 0.7, SEED);
        MazeMetrics.placeStartAndGoalAtExtremes(level);
        return level;
    }

    /**
     * Entrance, boss room, and the treasure/save points between them, as named locations.
     *
     * @param level      the generated level
     * @param treasures  how many treasure or save points to place
     */
    static List<Location> planLocations(MazeGrid level, int treasures) {
        Point entrance = level.start();
        Point boss = level.goal();
        int[][] depth = MazeMetrics.distancesFrom(level, entrance);

        List<Location> plan = new ArrayList<>();
        plan.add(new Location("entrance", entrance, 0, "ENTRANCE"));

        FacilityPlacement.Placement placement = FacilityPlacement.kCenter(level, treasures);
        int index = 1;
        for (Point cell : placement.facilities()) {
            if (cell.equals(entrance) || cell.equals(boss)) {
                continue; // already named
            }
            plan.add(new Location("vault-" + index++, cell, depth[cell.row()][cell.col()],
                    "TREASURE"));
        }

        plan.add(new Location("boss-chamber", boss, depth[boss.row()][boss.col()], "BOSS"));
        return plan;
    }

    private static void report(MazeGrid level) {
        System.out.printf("Dungeon %dx%d, seed %d%n%n", ROWS, COLS, SEED);

        MazeMetrics.Diameter depth = MazeMetrics.exactDiameter(level);
        MazeMetrics.Diameter estimate = MazeMetrics.diameter(level);
        System.out.println("1. Level depth");
        System.out.printf("   exact diameter      %d steps  (%s -> %s)%n",
                depth.distance(), depth.from(), depth.to());
        System.out.printf("   fast estimate       %d steps  %s%n", estimate.distance(),
                estimate.distance() == depth.distance()
                        ? "(agrees here)"
                        : "(reads short — the level has loops)");

        System.out.println("\n2. Hardest route from entrance to boss");
        LongestPath.LongPath hardest = LongestPath.hardestRoute(level);
        List<Point> direct = MazeMetrics.shortestPath(level, level.start(), level.goal());
        System.out.printf("   direct route        %d cells%n", direct.size());
        System.out.printf("   longest simple      %d cells  (%s)%n", hardest.path().size(),
                hardest.exact() ? "exact, search budget sufficed"
                        : "lower bound, budget exhausted");
        if (!direct.isEmpty()) {
            System.out.printf("   the long way round is %.1fx the direct route%n",
                    hardest.path().size() / (double) direct.size());
        }

        System.out.println("\n3. Placement (kCenter — solid rock is not a place)");
        FacilityPlacement.Placement placement = FacilityPlacement.kCenter(level, 5);
        System.out.printf("   covering radius     %d steps%n", placement.coveringRadius());
        System.out.printf("   rooms served        %d of %d floor cells%n",
                placement.servedCells(), floorCells(level));

        System.out.println("\n4. Locations for the narrative layer");
        for (Location location : planLocations(level, 5)) {
            System.out.printf("   %-14s %-9s depth %3d  at %s%n",
                    location.name(), location.kind(), location.depth(), location.cell());
        }
    }

    /** Cells reachable from the entrance — the level's actual floor area. */
    static int floorCells(MazeGrid level) {
        int count = 0;
        for (int[] row : MazeMetrics.distancesFrom(level, level.start())) {
            for (int d : row) {
                if (d >= 0) {
                    count++;
                }
            }
        }
        return count;
    }
}
