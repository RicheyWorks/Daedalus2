// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.model.Point;

/**
 * First-person pose. Yaw 0 looks north (−Z). Pitch is clamped so the
 * camera cannot invert.
 */
public final class ExploreBody {

    public static final double EYE_Y = 1.2;
    public static final double PITCH_LIMIT = Math.toRadians(89);

    private double x;
    private double z;
    private double yaw;
    private double pitch;

    public ExploreBody(double x, double z, double yaw, double pitch) {
        this.x = x;
        this.z = z;
        this.yaw = yaw;
        this.pitch = clampPitch(pitch);
    }

    public static ExploreBody atCell(Point cell) {
        if (cell == null) {
            throw new NullPointerException("cell");
        }
        return new ExploreBody(ExploreMesh.worldX(cell.col()), ExploreMesh.worldZ(cell.row()),
                0, 0);
    }

    public double x() {
        return x;
    }

    public double z() {
        return z;
    }

    public double yaw() {
        return yaw;
    }

    public double pitch() {
        return pitch;
    }

    public Point cell() {
        return new Point(ExploreMesh.cellRow(z), ExploreMesh.cellCol(x));
    }

    public void moveTo(double nx, double nz) {
        this.x = nx;
        this.z = nz;
    }

    public void look(double yawDelta, double pitchDelta) {
        this.yaw += yawDelta;
        this.pitch = clampPitch(this.pitch + pitchDelta);
    }

    public static double clampPitch(double pitch) {
        if (pitch > PITCH_LIMIT) {
            return PITCH_LIMIT;
        }
        if (pitch < -PITCH_LIMIT) {
            return -PITCH_LIMIT;
        }
        return pitch;
    }
}
