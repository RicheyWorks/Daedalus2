// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;

/**
 * Free-walk with wall slide. A cell change must be in
 * {@link MazeGrid#openNeighbors(Point)} — same legality as the 2D well.
 */
public final class ExploreWalk {

    private static final double STEP = 0.12;

    private ExploreWalk() {
    }

    public record Outcome(boolean moved, boolean cellChanged, Point from, Point to) {
    }

    public static Outcome step(ExploreMesh mesh, ExploreBody body, double dx, double dz) {
        if (mesh == null || body == null) {
            return new Outcome(false, false, null, null);
        }
        Point from = body.cell();
        double ox = body.x();
        double oz = body.z();
        double x = ox;
        double z = oz;
        int parts = Math.max(1, (int) Math.ceil(Math.hypot(dx, dz) / STEP));
        for (int i = 1; i <= parts; i++) {
            double tx = ox + dx * i / parts;
            double tz = oz + dz * i / parts;
            double[] slid = slide(mesh, x, z, tx, tz);
            Point next = new Point(ExploreMesh.cellRow(slid[1]), ExploreMesh.cellCol(slid[0]));
            if (!legalCellStep(mesh.grid(), from, next)) {
                break;
            }
            x = slid[0];
            z = slid[1];
            from = next;
        }
        body.moveTo(x, z);
        Point to = body.cell();
        Point start = new Point(ExploreMesh.cellRow(oz), ExploreMesh.cellCol(ox));
        boolean moved = x != ox || z != oz;
        return new Outcome(moved, !to.equals(start), start, to);
    }

    public static boolean legalCellStep(MazeGrid grid, Point from, Point to) {
        if (grid == null || from == null || to == null) {
            return false;
        }
        if (from.equals(to)) {
            return true;
        }
        if (!grid.inBounds(to)) {
            return false;
        }
        return grid.openNeighbors(from).contains(to);
    }

    private static double[] slide(ExploreMesh mesh, double fromX, double fromZ,
                                 double toX, double toZ) {
        if (!mesh.blocked(toX, toZ, ExploreMesh.PLAYER_RADIUS)) {
            return new double[] {toX, toZ};
        }
        if (!mesh.blocked(toX, fromZ, ExploreMesh.PLAYER_RADIUS)) {
            return new double[] {toX, fromZ};
        }
        if (!mesh.blocked(fromX, toZ, ExploreMesh.PLAYER_RADIUS)) {
            return new double[] {fromX, toZ};
        }
        return new double[] {fromX, fromZ};
    }
}
