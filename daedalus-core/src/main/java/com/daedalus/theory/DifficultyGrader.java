// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;

/**
 * Measures how hard a maze is to <em>play</em>, from its structure alone (ADR-006 idea #10's
 * prerequisite: a campaign can only order stages by difficulty if difficulty is measurable).
 *
 * <p>Three measurable facts, each with an argued direction:
 * <ul>
 *   <li><b>Detour factor</b> — route length over {@code rows + cols}. A maze whose solution
 *       runs straight to the goal is easy however large it is; one that marches you the long
 *       way around is not. This is the dominant term.</li>
 *   <li><b>Branchiness</b> — dead ends per unit perimeter ({@code rows + cols}). Dead ends are
 *       where a human loses time: every one is a decision that can go wrong. Note the
 *       denominator: dead ends <em>per cell</em> looks like the natural choice and is a trap,
 *       because a 3×3 maze devotes a third of its cells to dead ends while a 41×41 devotes an
 *       eighth. Normalizing that way ranks a trivial 3×3 above a 5×5 — measured, not
 *       hypothetical — which would put a campaign's first stage above its second.</li>
 *   <li><b>Scale</b> — {@code sqrt(area)}, contributing mildly. Size alone is weak evidence
 *       (a big maze with a straight route is easy), so it must not dominate.</li>
 * </ul>
 * and one discount: <b>alternate routes</b>. Start↔goal edge connectivity above 1 means the
 * maze is braided — more than one way through — which forgives mistakes, so it reduces the
 * score.
 *
 * <p><b>Honesty about the numbers.</b> The weights and label thresholds here are <em>chosen</em>
 * to spread the mazes this project actually generates across a readable range; they are not
 * calibrated against human play times, and this class does not pretend otherwise. What it does
 * guarantee — and what {@code DifficultyGraderTest} pins — is <em>ordering</em>: braiding a
 * maze lowers its score, lengthening the route raises it, and a trivially straight corridor
 * always grades below a winding maze of the same size. Ordering is all the campaign ladder
 * needs.
 *
 * <p>Hazards (living erosion, traffic) are deliberately not graded here: this reads a static
 * snapshot, and a hazard is a property of how a stage is <em>run</em>. The campaign adds its
 * own hazard premium on top.
 */
public final class DifficultyGrader {

    /** Weight of the detour term — the dominant signal. */
    private static final double W_DETOUR = 2.0;
    /** Weight of branchiness (dead ends per unit perimeter). */
    private static final double W_BRANCHINESS = 0.5;
    /** Weight of scale; deliberately mild. */
    private static final double W_SCALE = 0.06;
    /** Discount per alternate route beyond the first. */
    private static final double BRAID_DISCOUNT = 1.2;

    private DifficultyGrader() {
    }

    /**
     * A graded maze: the score plus every measurement behind it, so a caller can show its
     * work instead of asking to be trusted.
     *
     * @param score             composite difficulty, higher is harder
     * @param label             human-readable band ({@code gentle} … {@code brutal})
     * @param routeLength       cells on the shortest start→goal route (0 if unreachable)
     * @param deadEnds          cells with exactly one opening
     * @param alternateRoutes   start↔goal edge connectivity: 1 on a perfect maze, more when braided
     * @param detourFactor      {@code routeLength / (rows + cols)}
     * @param branchiness       {@code deadEnds / (rows + cols)} — see the class note on why the
     *                          denominator is perimeter and not area
     */
    public record Grade(double score, String label, int routeLength, int deadEnds,
                        int alternateRoutes, double detourFactor, double branchiness) {}

    /** Grade a maze's static structure. */
    public static Grade grade(MazeGrid grid) {
        int rows = grid.rows();
        int cols = grid.cols();
        int area = Math.max(1, rows * cols);
        int perimeter = Math.max(1, rows + cols);

        int routeLength = MazeMetrics.shortestPath(grid, grid.start(), grid.goal()).size();
        int deadEnds = Braider.deadEnds(grid).size();
        int alternateRoutes = MazeFlow.minCutStartToGoal(grid).cutSize();

        double detourFactor = routeLength / (double) perimeter;
        double branchiness = deadEnds / (double) perimeter;

        double score = W_DETOUR * detourFactor
                + W_BRANCHINESS * branchiness
                + W_SCALE * Math.sqrt(area)
                - BRAID_DISCOUNT * Math.max(0, alternateRoutes - 1);
        score = Math.max(0.0, score);

        return new Grade(round(score), labelFor(score), routeLength, deadEnds, alternateRoutes,
                round(detourFactor), round(branchiness));
    }

    /**
     * Bands over the score, placed against measured output rather than intuition: sweeping six
     * generators across 7×7…41×41 puts this project's mazes in roughly {@code [2.1, 13.3]}, with
     * a 3×3 and a straight corridor at the floor (~2.1) and a 41×41 recursive-backtracker at the
     * ceiling (~13.3). So a small binary-tree maze grades {@code gentle} and a large
     * recursive-backtracker one {@code brutal}, which is what those mazes actually feel like.
     */
    private static String labelFor(double score) {
        if (score < 3.0) return "gentle";
        if (score < 4.5) return "moderate";
        if (score < 6.0) return "tricky";
        if (score < 8.5) return "hard";
        if (score < 11.5) return "punishing";
        return "brutal";
    }

    private static double round(double v) {
        return Math.round(v * 100.0) / 100.0;
    }
}
