// SPDX-License-Identifier: MIT

package com.daedalus.explore.glfw;

import com.daedalus.explore.ExploreBody;
import com.daedalus.explore.ExploreInput;
import com.daedalus.explore.ExploreMarker;
import com.daedalus.explore.ExploreMesh;
import com.daedalus.explore.ExplorePaint;
import com.daedalus.explore.ExploreWorld;
import com.daedalus.explore.XrFrame;
import com.daedalus.explore.XrRuntime;
import com.daedalus.explore.XrRuntimes;
import org.lwjgl.glfw.GLFWErrorCallback;
import org.lwjgl.glfw.GLFWGamepadState;
import org.lwjgl.glfw.GLFWVidMode;
import org.lwjgl.opengl.GL;
import org.lwjgl.system.MemoryStack;

import java.nio.DoubleBuffer;
import java.nio.IntBuffer;
import java.util.Optional;

import static org.lwjgl.glfw.GLFW.GLFW_CONTEXT_VERSION_MAJOR;
import static org.lwjgl.glfw.GLFW.GLFW_CONTEXT_VERSION_MINOR;
import static org.lwjgl.glfw.GLFW.GLFW_FALSE;
import static org.lwjgl.glfw.GLFW.GLFW_GAMEPAD_AXIS_LEFT_X;
import static org.lwjgl.glfw.GLFW.GLFW_GAMEPAD_AXIS_LEFT_Y;
import static org.lwjgl.glfw.GLFW.GLFW_GAMEPAD_AXIS_RIGHT_X;
import static org.lwjgl.glfw.GLFW.GLFW_GAMEPAD_AXIS_RIGHT_Y;
import static org.lwjgl.glfw.GLFW.GLFW_GAMEPAD_BUTTON_DPAD_LEFT;
import static org.lwjgl.glfw.GLFW.GLFW_GAMEPAD_BUTTON_DPAD_RIGHT;
import static org.lwjgl.glfw.GLFW.GLFW_JOYSTICK_1;
import static org.lwjgl.glfw.GLFW.GLFW_KEY_A;
import static org.lwjgl.glfw.GLFW.GLFW_KEY_D;
import static org.lwjgl.glfw.GLFW.GLFW_KEY_ESCAPE;
import static org.lwjgl.glfw.GLFW.GLFW_KEY_H;
import static org.lwjgl.glfw.GLFW.GLFW_KEY_J;
import static org.lwjgl.glfw.GLFW.GLFW_KEY_L;
import static org.lwjgl.glfw.GLFW.GLFW_KEY_S;
import static org.lwjgl.glfw.GLFW.GLFW_KEY_W;
import static org.lwjgl.glfw.GLFW.GLFW_PRESS;
import static org.lwjgl.glfw.GLFW.GLFW_RESIZABLE;
import static org.lwjgl.glfw.GLFW.GLFW_TRUE;
import static org.lwjgl.glfw.GLFW.GLFW_VISIBLE;
import static org.lwjgl.glfw.GLFW.glfwCreateWindow;
import static org.lwjgl.glfw.GLFW.glfwDefaultWindowHints;
import static org.lwjgl.glfw.GLFW.glfwDestroyWindow;
import static org.lwjgl.glfw.GLFW.glfwGetCursorPos;
import static org.lwjgl.glfw.GLFW.glfwGetGamepadState;
import static org.lwjgl.glfw.GLFW.glfwGetKey;
import static org.lwjgl.glfw.GLFW.glfwGetPrimaryMonitor;
import static org.lwjgl.glfw.GLFW.glfwGetVideoMode;
import static org.lwjgl.glfw.GLFW.glfwGetWindowSize;
import static org.lwjgl.glfw.GLFW.glfwInit;
import static org.lwjgl.glfw.GLFW.glfwJoystickIsGamepad;
import static org.lwjgl.glfw.GLFW.glfwMakeContextCurrent;
import static org.lwjgl.glfw.GLFW.glfwPollEvents;
import static org.lwjgl.glfw.GLFW.glfwSetInputMode;
import static org.lwjgl.glfw.GLFW.glfwSetWindowPos;
import static org.lwjgl.glfw.GLFW.glfwSetWindowShouldClose;
import static org.lwjgl.glfw.GLFW.glfwShowWindow;
import static org.lwjgl.glfw.GLFW.glfwSwapBuffers;
import static org.lwjgl.glfw.GLFW.glfwSwapInterval;
import static org.lwjgl.glfw.GLFW.glfwTerminate;
import static org.lwjgl.glfw.GLFW.glfwWindowHint;
import static org.lwjgl.glfw.GLFW.glfwWindowShouldClose;
import static org.lwjgl.glfw.GLFW.GLFW_CURSOR;
import static org.lwjgl.glfw.GLFW.GLFW_CURSOR_DISABLED;
import static org.lwjgl.opengl.GL11.GL_COLOR_BUFFER_BIT;
import static org.lwjgl.opengl.GL11.GL_DEPTH_BUFFER_BIT;
import static org.lwjgl.opengl.GL11.GL_DEPTH_TEST;
import static org.lwjgl.opengl.GL11.GL_MODELVIEW;
import static org.lwjgl.opengl.GL11.GL_PROJECTION;
import static org.lwjgl.opengl.GL11.GL_TRIANGLES;
import static org.lwjgl.opengl.GL11.glBegin;
import static org.lwjgl.opengl.GL11.glClear;
import static org.lwjgl.opengl.GL11.glClearColor;
import static org.lwjgl.opengl.GL11.glColor3f;
import static org.lwjgl.opengl.GL11.glEnable;
import static org.lwjgl.opengl.GL11.glEnd;
import static org.lwjgl.opengl.GL11.glLoadIdentity;
import static org.lwjgl.opengl.GL11.glMatrixMode;
import static org.lwjgl.opengl.GL11.glRotatef;
import static org.lwjgl.opengl.GL11.glTranslatef;
import static org.lwjgl.opengl.GL11.glVertex3d;
import static org.lwjgl.opengl.GL11.glViewport;
import static org.lwjgl.opengl.GL11.glFrustum;
import static org.lwjgl.system.MemoryUtil.NULL;

/**
 * GLFW first-person shell. Launch-only — tests must not load this class.
 *
 * <p>WASD + mouse, Xbox-standard gamepad, L living pulse, J occupy,
 * H harden on the next L. Escape quits.
 */
public final class ExploreHost {

    private ExploreHost() {
    }

    public static void run(ExploreWorld world) {
        run(world, false);
    }

    public static void run(ExploreWorld world, boolean smoke) {
        GLFWErrorCallback.createPrint(System.err).set();
        if (!glfwInit()) {
            throw new IllegalStateException("Unable to initialize GLFW");
        }
        glfwDefaultWindowHints();
        glfwWindowHint(GLFW_VISIBLE, GLFW_FALSE);
        glfwWindowHint(GLFW_RESIZABLE, GLFW_TRUE);
        glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 2);
        glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 1);
        long window = glfwCreateWindow(1280, 720, "Daedalus Explore", NULL, NULL);
        if (window == NULL) {
            glfwTerminate();
            throw new IllegalStateException("Failed to create the explore window");
        }
        try (MemoryStack stack = MemoryStack.stackPush()) {
            IntBuffer w = stack.mallocInt(1);
            IntBuffer h = stack.mallocInt(1);
            glfwGetWindowSize(window, w, h);
            GLFWVidMode vid = glfwGetVideoMode(glfwGetPrimaryMonitor());
            if (vid != null) {
                glfwSetWindowPos(window, (vid.width() - w.get(0)) / 2,
                        (vid.height() - h.get(0)) / 2);
            }
        }
        glfwMakeContextCurrent(window);
        glfwSwapInterval(1);
        glfwShowWindow(window);
        glfwSetInputMode(window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);
        GL.createCapabilities();
        glEnable(GL_DEPTH_TEST);
        glClearColor(ExplorePaint.SKY_R, ExplorePaint.SKY_G, ExplorePaint.SKY_B, 1f);

        Optional<XrRuntime> xr = XrRuntimes.firstPresent(ExploreHost.class.getClassLoader());
        xr.ifPresent(runtime -> runtime.attach(world));

        double last = System.nanoTime();
        double[] cursor = {0, 0};
        boolean liveDown = false;
        boolean jamDown = false;
        boolean harden = false;
        GLFWGamepadState pad = GLFWGamepadState.create();
        int frames = 0;
        while (!glfwWindowShouldClose(window)) {
            glfwPollEvents();
            if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS) {
                glfwSetWindowShouldClose(window, true);
            }
            double now = System.nanoTime();
            double dt = Math.min(0.05, (now - last) / 1_000_000_000.0);
            last = now;

            ExploreInput.Intent intent = keys(window).plus(mouse(window, cursor)).plus(pad(pad));
            XrFrame frame = xr.map(XrRuntime::beginFrame).orElse(XrFrame.none());
            intent = intent.plus(new ExploreInput.Intent(0, 0, frame.yawDelta(), frame.pitchDelta()));
            if (frame.snapLeft() || frame.snapRight()) {
                intent = intent.plus(ExploreInput.gamepad(0, 0, 0, 0,
                        frame.snapLeft(), frame.snapRight()));
            }
            world.apply(intent, dt);

            boolean l = glfwGetKey(window, GLFW_KEY_L) == GLFW_PRESS;
            if (l && !liveDown) {
                world.pulseLive(System.nanoTime(), harden);
            }
            liveDown = l;
            boolean j = glfwGetKey(window, GLFW_KEY_J) == GLFW_PRESS;
            if (j && !jamDown) {
                world.occupyHere();
            }
            jamDown = j;
            harden = glfwGetKey(window, GLFW_KEY_H) == GLFW_PRESS;

            draw(window, world);
            xr.ifPresent(runtime -> runtime.endFrame(frame));
            glfwSwapBuffers(window);
            if (smoke && ++frames >= 3) {
                break;
            }
        }
        xr.ifPresent(XrRuntime::stop);
        glfwDestroyWindow(window);
        glfwTerminate();
    }

    private static ExploreInput.Intent keys(long window) {
        return ExploreInput.keyboard(
                glfwGetKey(window, GLFW_KEY_W) == GLFW_PRESS,
                glfwGetKey(window, GLFW_KEY_A) == GLFW_PRESS,
                glfwGetKey(window, GLFW_KEY_S) == GLFW_PRESS,
                glfwGetKey(window, GLFW_KEY_D) == GLFW_PRESS);
    }

    private static ExploreInput.Intent mouse(long window, double[] last) {
        try (MemoryStack stack = MemoryStack.stackPush()) {
            DoubleBuffer x = stack.mallocDouble(1);
            DoubleBuffer y = stack.mallocDouble(1);
            glfwGetCursorPos(window, x, y);
            double mx = x.get(0);
            double my = y.get(0);
            if (last[0] == 0 && last[1] == 0) {
                last[0] = mx;
                last[1] = my;
                return ExploreInput.Intent.none();
            }
            ExploreInput.Intent intent = ExploreInput.mouse(mx - last[0], my - last[1]);
            last[0] = mx;
            last[1] = my;
            return intent;
        }
    }

    private static ExploreInput.Intent pad(GLFWGamepadState state) {
        if (!glfwJoystickIsGamepad(GLFW_JOYSTICK_1) || !glfwGetGamepadState(GLFW_JOYSTICK_1, state)) {
            return ExploreInput.Intent.none();
        }
        return ExploreInput.gamepad(
                state.axes(GLFW_GAMEPAD_AXIS_LEFT_X),
                state.axes(GLFW_GAMEPAD_AXIS_LEFT_Y),
                state.axes(GLFW_GAMEPAD_AXIS_RIGHT_X),
                -state.axes(GLFW_GAMEPAD_AXIS_RIGHT_Y),
                state.buttons(GLFW_GAMEPAD_BUTTON_DPAD_LEFT) == GLFW_PRESS,
                state.buttons(GLFW_GAMEPAD_BUTTON_DPAD_RIGHT) == GLFW_PRESS);
    }

    private static void draw(long window, ExploreWorld world) {
        try (MemoryStack stack = MemoryStack.stackPush()) {
            IntBuffer w = stack.mallocInt(1);
            IntBuffer h = stack.mallocInt(1);
            glfwGetWindowSize(window, w, h);
            int width = Math.max(1, w.get(0));
            int height = Math.max(1, h.get(0));
            glViewport(0, 0, width, height);
            glMatrixMode(GL_PROJECTION);
            glLoadIdentity();
            double aspect = width / (double) height;
            glFrustum(-0.12 * aspect, 0.12 * aspect, -0.12, 0.12, 0.08, 200);
            glMatrixMode(GL_MODELVIEW);
            glLoadIdentity();
            ExploreBody body = world.body();
            glRotatef((float) Math.toDegrees(-body.pitch()), 1, 0, 0);
            glRotatef((float) Math.toDegrees(-body.yaw()), 0, 1, 0);
            glTranslatef((float) -body.x(), (float) -ExploreBody.EYE_Y, (float) -body.z());
        }
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        float[] rgb = new float[3];
        glBegin(GL_TRIANGLES);
        for (ExploreMesh.Triangle tri : world.mesh().triangles()) {
            ExplorePaint.tint(tri, world.fog().tileVisible(tri.tr(), tri.tc()), rgb);
            glColor3f(rgb[0], rgb[1], rgb[2]);
            glVertex3d(tri.x1(), tri.y1(), tri.z1());
            glVertex3d(tri.x2(), tri.y2(), tri.z2());
            glVertex3d(tri.x3(), tri.y3(), tri.z3());
        }
        for (ExploreMarker marker : world.markers()) {
            int tr = 2 * marker.cell().row() + 1;
            int tc = 2 * marker.cell().col() + 1;
            if (!world.fog().tileVisible(tr, tc)) {
                continue;
            }
            ExplorePaint.marker(marker.kind(), rgb);
            glColor3f(rgb[0], rgb[1], rgb[2]);
            pillar(ExploreMesh.worldX(marker.cell().col()),
                    ExploreMesh.worldZ(marker.cell().row()));
        }
        glEnd();
    }

    private static void pillar(double x, double z) {
        double h = 0.16;
        double y1 = 0.95;
        double x0 = x - h;
        double x1 = x + h;
        double z0 = z - h;
        double z1 = z + h;
        glVertex3d(x0, 0, z0);
        glVertex3d(x1, 0, z0);
        glVertex3d(x1, y1, z0);
        glVertex3d(x0, 0, z0);
        glVertex3d(x1, y1, z0);
        glVertex3d(x0, y1, z0);
        glVertex3d(x0, 0, z1);
        glVertex3d(x1, y1, z1);
        glVertex3d(x1, 0, z1);
        glVertex3d(x0, 0, z1);
        glVertex3d(x0, y1, z1);
        glVertex3d(x1, y1, z1);
        glVertex3d(x0, 0, z0);
        glVertex3d(x0, y1, z0);
        glVertex3d(x0, y1, z1);
        glVertex3d(x0, 0, z0);
        glVertex3d(x0, y1, z1);
        glVertex3d(x0, 0, z1);
        glVertex3d(x1, 0, z0);
        glVertex3d(x1, 0, z1);
        glVertex3d(x1, y1, z1);
        glVertex3d(x1, 0, z0);
        glVertex3d(x1, y1, z1);
        glVertex3d(x1, y1, z0);
        glVertex3d(x0, y1, z0);
        glVertex3d(x1, y1, z0);
        glVertex3d(x1, y1, z1);
        glVertex3d(x0, y1, z0);
        glVertex3d(x1, y1, z1);
        glVertex3d(x0, y1, z1);
    }
}
