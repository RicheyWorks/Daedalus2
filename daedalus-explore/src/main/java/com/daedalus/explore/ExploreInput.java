// SPDX-License-Identifier: MIT

package com.daedalus.explore;

/**
 * One look/move intent. Keyboard, mouse, and gamepad add into the same
 * vector so GLFW and tests share a mapping.
 */
public final class ExploreInput {

    public static final double DEADZONE = 0.18;
    public static final double LOOK_SENS = 0.0022;
    public static final double STICK_LOOK = 1.8;
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
     * Left stick is move ({@code +ly} walks the look direction), right stick
     * is look. GLFW reports stick-up as −1; the host passes that axis raw so
     * Xbox/Windows does not walk opposite the camera.
     */
    public static Intent gamepad(double lx, double ly, double rx, double ry,
                                boolean snapLeft, boolean snapRight) {
        double mx = dead(lx);
        double my = dead(ly);
        double lookX = dead(rx);
        double lookY = dead(ry);
        Intent move = normalizeMove(my, mx);
        double yaw = -lookX * STICK_LOOK;
        if (snapLeft) {
            yaw -= SNAP_TURN;
        }
        if (snapRight) {
            yaw += SNAP_TURN;
        }
        return move.plus(new Intent(0, 0, yaw, -lookY * STICK_LOOK));
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
