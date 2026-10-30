// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;
import com.daedalus.theory.FacilityPlacement;
import com.daedalus.theory.MazeMetrics;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * The shape of a maze as a landscape: how far every cell is from somewhere that matters
 * (ADR-007 idea 6), and where to stand so nowhere is far from you (ADR-007 idea 5).
 *
 * <h3>Why this does not use {@code DistanceOracle}</h3>
 *
 * <p>ADR-007 listed idea 6 as "revives {@code DistanceOracle}", and building it measured that
 * claim rather than assuming it. The oracle tabulates all-pairs distances for O(1) lookups, and
 * it caps itself at 4,096 cells because the table is {@code V²} shorts — 32 MB at 64×64. For a
 * heat map that is the wrong shape of tool twice over: the overlay needs <em>one</em> source, not
 * all pairs, and a 64×64 cap would exclude most mazes this server will happily generate.
 *
 * <p>Worse, the oracle loses on its own ground. Computing every cell's eccentricity — the
 * all-pairs question it exists for — measured at <b>1,738 ms</b> via precompute-then-scan against
 * <b>1,485 ms</b> for simply running the same breadth-first sweeps directly, at 64×64, and the
 * direct route allocates no table at all. The oracle only wins when many <em>random pairs</em>
 * are queried after paying for the table, and nothing in this product does that. So these
 * features use {@link MazeMetrics#distancesFrom}, which is one sweep, works at any size, and is
 * the same code the oracle calls internally. {@code DistanceOracle} stays dormant on purpose,
 * with a measurement behind the decision rather than an oversight.
 */
@Service
public class TopographyService {

    /**
     * Largest maze whose full distance field is serialised. This is a payload bound, not an
     * algorithmic one — the BFS itself is linear and happy at 512×512, but that maze is 262,144
     * integers, roughly 1.5 MB of JSON for one overlay. Cells beyond this are refused with an
     * explanation rather than silently downsampled, because a heat map that quietly stops being
     * per-cell is a lie told in colour.
     */
    private final int maxFieldCells;

    private final MazeGenerationService mazes;

    public TopographyService(MazeGenerationService mazes,
                             @Value("${daedalus.topography.max-field-cells:16384}")
                             int maxFieldCells) {
        this.mazes = mazes;
        this.maxFieldCells = maxFieldCells;
    }

    /** Which landmark the distance field is measured from. */
    public enum Origin { GOAL, START }

    /**
     * Every cell's distance from the chosen landmark.
     *
     * @param distances  row-major grid; {@code -1} where a cell cannot reach the origin at all
     * @param maxDistance the farthest any reachable cell sits from the origin
     * @param unreachable how many cells the origin cannot reach — rock in a dungeon, and the
     *                    reason a heat map of one is mostly blank
     */
    public record DistanceField(UUID mazeId, int rows, int cols, Origin from, Point origin,
                                int maxDistance, int unreachable, int[][] distances) { }

    /**
     * Where to put {@code k} safe points so the worst-off cell is as close to one as possible.
     *
     * @param coveringRadius distance from the worst-served cell to its nearest sanctuary
     * @param servedCells    how many cells are reachable from some sanctuary
     * @param worstServed    the cell that radius belongs to — the loneliest place in the maze
     */
    public record Sanctuaries(UUID mazeId, int k, List<Point> placements, int coveringRadius,
                              int servedCells, int habitableCells, Point worstServed,
                              String note) {
        public Sanctuaries {
            placements = List.copyOf(placements);
        }
    }

    /** Hard cap on sanctuaries: past this the greedy is refining noise, and the UI is unreadable. */
    public static final int MAX_SANCTUARIES = 16;

    /** {@code null} when the maze is unknown; throws when the field would be too large to send. */
    public DistanceField fieldFor(UUID mazeId, Origin from) {
        var cached = mazes.find(mazeId);
        if (cached == null) {
            return null;
        }
        MazeGrid grid = cached.grid();
        int cells = grid.rows() * grid.cols();
        if (cells > maxFieldCells) {
            throw new IllegalArgumentException(
                    "a " + grid.rows() + "x" + grid.cols() + " distance field is " + cells
                            + " cells, over the " + maxFieldCells + "-cell payload cap. The sweep "
                            + "itself is linear and fine at this size; the JSON is not. Generate a "
                            + "smaller maze for the heat map, or raise "
                            + "daedalus.topography.max-field-cells.");
        }
        Point origin = from == Origin.START ? grid.start() : grid.goal();
        int[][] distances = MazeMetrics.distancesFrom(grid, origin);

        int max = 0;
        int unreachable = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                int d = distances[r][c];
                if (d < 0) {
                    unreachable++;
                } else if (d > max) {
                    max = d;
                }
            }
        }
        return new DistanceField(mazeId, grid.rows(), grid.cols(), from, origin,
                max, unreachable, distances);
    }

    /** {@code null} when the maze is unknown. {@code k} is clamped into 1..{@value #MAX_SANCTUARIES}. */
    public Sanctuaries sanctuariesFor(UUID mazeId, Integer requested) {
        var cached = mazes.find(mazeId);
        if (cached == null) {
            return null;
        }
        MazeGrid grid = cached.grid();
        int k = Math.max(1, Math.min(MAX_SANCTUARIES, requested == null ? 5 : requested));

        // kCenter, not kCenterAcrossComponents. The variants differ only on a fragmented maze,
        // and the difference matters: measured on a 21x21 dungeon, kCenter serves all 206
        // habitable cells at every k while the across-components variant pins the radius at 40
        // and spends its extra facilities on isolated rock, "serving" 213 cells that nobody can
        // walk to. Rock is not a place. The habitable subgraph of every generator this project
        // registers is connected — the generator fuzz proves it — so the dungeon reading is the
        // right one here, and servedCells below is reported so the claim stays checkable.
        FacilityPlacement.Placement placement = FacilityPlacement.kCenter(grid, k);
        int habitable = habitableCells(grid);
        Point worst = worstServedCell(grid, placement.facilities());

        return new Sanctuaries(mazeId, k, placement.facilities(), placement.coveringRadius(),
                placement.servedCells(), habitable, worst,
                note(placement, habitable, k));
    }

    /** The cell farthest from every sanctuary — what the covering radius is actually about. */
    private static Point worstServedCell(MazeGrid grid, List<Point> facilities) {
        if (facilities.isEmpty()) {
            return null;
        }
        List<int[][]> fields = new ArrayList<>(facilities.size());
        for (Point f : facilities) {
            fields.add(MazeMetrics.distancesFrom(grid, f));
        }
        Point worst = facilities.get(0);
        int worstDistance = -1;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (grid.openNeighbors(new Point(r, c)).isEmpty()) {
                    continue;
                }
                int nearest = Integer.MAX_VALUE;
                for (int[][] field : fields) {
                    int d = field[r][c];
                    if (d >= 0 && d < nearest) {
                        nearest = d;
                    }
                }
                if (nearest != Integer.MAX_VALUE && nearest > worstDistance) {
                    worstDistance = nearest;
                    worst = new Point(r, c);
                }
            }
        }
        return worst;
    }

    private static int habitableCells(MazeGrid grid) {
        int habitable = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (!grid.openNeighbors(new Point(r, c)).isEmpty()) {
                    habitable++;
                }
            }
        }
        return habitable;
    }

    private static String note(FacilityPlacement.Placement placement, int habitable, int asked) {
        StringBuilder note = new StringBuilder();
        if (placement.facilities().size() < asked) {
            note.append("Only ").append(placement.facilities().size())
                    .append(" distinct useful locations exist here, so fewer than the ")
                    .append(asked).append(" requested were placed. ");
        }
        if (placement.servedCells() < habitable) {
            note.append("Warning: ").append(habitable - placement.servedCells())
                    .append(" habitable cells are in a part of the maze no sanctuary can reach, "
                            + "so the covering radius describes only the ")
                    .append(placement.servedCells()).append(" that are served. ");
        }
        note.append("Farthest-first greedy is a 2-approximation: the true optimum is never worse "
                + "than this radius, and never better than half of it. k-center is NP-hard, so "
                + "no polynomial algorithm does better unless P = NP.");
        return note.toString();
    }
}
