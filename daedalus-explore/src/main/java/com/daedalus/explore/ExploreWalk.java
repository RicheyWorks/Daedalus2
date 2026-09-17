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
        return step(mesh, null, body, dx, dz);
    }

    /**
     * Same corridor legality as {@link #step(ExploreMesh, ExploreBody, double, double)}.
     * Occupied cubes refuse the body when {@code blocks} is present — discrete
     * {@link WorldMesh#blocked}, not a maze hull.
     */
    public static Outcome step(ExploreMesh mesh, WorldMesh blocks, ExploreBody body,
                               double dx, double dz) {
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
            double[] slid = slide(mesh, blocks, x, z, tx, tz);
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

    private static double[] slide(ExploreMesh mesh, WorldMesh blocks, double fromX, double fromZ,
                                 double toX, double toZ) {
        if (!blocked(mesh, blocks, toX, toZ)) {
            return new double[] {toX, toZ};
        }
        if (!blocked(mesh, blocks, toX, fromZ)) {
            return new double[] {toX, fromZ};
        }
        if (!blocked(mesh, blocks, fromX, toZ)) {
            return new double[] {fromX, toZ};
        }
        return new double[] {fromX, fromZ};
    }

    private static boolean blocked(ExploreMesh mesh, WorldMesh blocks, double x, double z) {
        if (mesh.blocked(x, z, ExploreMesh.PLAYER_RADIUS)) {
            return true;
        }
        return cubeBlocked(blocks, x, z);
    }

    /**
     * Sample the player disc at boot and eye height. One point at the
     * centroid misses the cube when the feet clip a corner.
     */
    static boolean cubeBlocked(WorldMesh blocks, double x, double z) {
        if (blocks == null) {
            return false;
        }
        double r = ExploreMesh.PLAYER_RADIUS;
        double[] ys = {0.35, ExploreBody.EYE_Y};
        double[] ox = {0, r, -r, 0, 0};
        double[] oz = {0, 0, 0, r, -r};
        for (double y : ys) {
            for (int i = 0; i < ox.length; i++) {
                if (blocks.blocked(x + ox[i], y, z + oz[i])) {
                    return true;
                }
            }
        }
        return false;
    }
}
