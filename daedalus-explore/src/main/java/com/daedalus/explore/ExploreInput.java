// SPDX-License-Identifier: MIT

package com.daedalus.explore;

/**
 * One look/move intent. Keyboard, mouse, and gamepad add into the same
 * vector so GLFW and tests share a mapping.
 */
public final class ExploreInput {

    public static final double DEADZONE = 0.18;
    public static final double LOOK_SENS = 0.0022;
    /** Radians per second at full right-stick. Must be scaled by frame dt. */
    public static final double STICK_LOOK = 2.4;
    public static final double SNAP_TURN = Math.toRadians(45);

    public record Intent(double forward, double strafe, double yawDelta, double pitchDelta) {
        public Intent plus(Intent other) {
            if (other == null) {
                return this;
            }
            return new Intent(forward + other.forward, strafe + other.strafe,
                    yawDelta + other.yawDelta, pitchDelta + other.pitchDelta);
        }

        public static Intent none() {
            return new Intent(0, 0, 0, 0);
        }
    }

    private ExploreInput() {
    }

    public static Intent keyboard(boolean w, boolean a, boolean s, boolean d) {
        double forward = (w ? 1 : 0) + (s ? -1 : 0);
        double strafe = (d ? 1 : 0) + (a ? -1 : 0);
        return normalizeMove(forward, strafe);
    }

    public static Intent mouse(double dx, double dy) {
        return new Intent(0, 0, -dx * LOOK_SENS, -dy * LOOK_SENS);
    }

    /**
     * Raw GLFW Xbox axes: stick-up is −1, stick-right is +1. Left stick
     * walks the look; right stick looks at {@link #STICK_LOOK} rad/s × dt.
     */
    public static Intent gamepad(double lx, double ly, double rx, double ry,
                                boolean snapLeft, boolean snapRight) {
        return gamepad(lx, ly, rx, ry, snapLeft, snapRight, 0);
    }

    public static Intent gamepad(double lx, double ly, double rx, double ry,
                                boolean snapLeft, boolean snapRight, double dt) {
        double scale = STICK_LOOK * Math.max(0, dt);
        Intent move = normalizeMove(-dead(ly), dead(lx));
        // Same signs as mouse(): stick-right / mouse-right is negative yaw;
        // GLFW stick-up is −1, same as mouse-up, so −ry looks up.
        double yaw = -dead(rx) * scale;
        if (snapLeft) {
            yaw += SNAP_TURN;
        }
        if (snapRight) {
            yaw -= SNAP_TURN;
        }
        return move.plus(new Intent(0, 0, yaw, -dead(ry) * scale));
    }

    public static double dead(double axis) {
        if (Math.abs(axis) < DEADZONE) {
            return 0;
        }
        double sign = axis < 0 ? -1 : 1;
        return sign * (Math.abs(axis) - DEADZONE) / (1.0 - DEADZONE);
    }

    public static void applyLook(ExploreBody body, Intent intent) {
        if (body == null || intent == null) {
            return;
        }
        body.look(intent.yawDelta(), intent.pitchDelta());
    }

    public static double[] moveVector(ExploreBody body, Intent intent, double speed) {
        if (body == null || intent == null) {
            return new double[] {0, 0};
        }
        double yaw = body.yaw();
        double f = intent.forward() * speed;
        double s = intent.strafe() * speed;
        double dx = Math.sin(yaw) * f + Math.cos(yaw) * s;
        double dz = -Math.cos(yaw) * f + Math.sin(yaw) * s;
        return new double[] {dx, dz};
    }

    private static Intent normalizeMove(double forward, double strafe) {
        double mag = Math.hypot(forward, strafe);
        if (mag > 1.0) {
            return new Intent(forward / mag, strafe / mag, 0, 0);
        }
        return new Intent(forward, strafe, 0, 0);
    }
}
