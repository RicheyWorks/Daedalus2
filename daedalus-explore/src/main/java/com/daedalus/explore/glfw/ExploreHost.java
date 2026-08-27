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
import org.lwjgl.system.MemoryUtil;

import java.nio.ByteBuffer;
import java.nio.DoubleBuffer;
import java.nio.FloatBuffer;
import java.nio.IntBuffer;
import java.util.List;
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
import static org.lwjgl.opengl.GL11.GL_FOG;
import static org.lwjgl.opengl.GL11.GL_FOG_COLOR;
import static org.lwjgl.opengl.GL11.GL_FOG_END;
import static org.lwjgl.opengl.GL11.GL_FOG_MODE;
import static org.lwjgl.opengl.GL11.GL_FOG_START;
import static org.lwjgl.opengl.GL11.GL_LINEAR;
import static org.lwjgl.opengl.GL11.GL_LINES;
import static org.lwjgl.opengl.GL11.GL_MODELVIEW;
import static org.lwjgl.opengl.GL11.GL_NEAREST;
import static org.lwjgl.opengl.GL11.GL_QUADS;
import static org.lwjgl.opengl.GL11.GL_PROJECTION;
import static org.lwjgl.opengl.GL11.GL_REPEAT;
import static org.lwjgl.opengl.GL11.GL_RGBA;
import static org.lwjgl.opengl.GL11.GL_TEXTURE_2D;
import static org.lwjgl.opengl.GL11.GL_TEXTURE_MAG_FILTER;
import static org.lwjgl.opengl.GL11.GL_TEXTURE_MIN_FILTER;
import static org.lwjgl.opengl.GL11.GL_TEXTURE_WRAP_S;
import static org.lwjgl.opengl.GL11.GL_TEXTURE_WRAP_T;
import static org.lwjgl.opengl.GL11.GL_TRIANGLES;
import static org.lwjgl.opengl.GL11.GL_UNSIGNED_BYTE;
import static org.lwjgl.opengl.GL11.glBegin;
import static org.lwjgl.opengl.GL11.glBindTexture;
import static org.lwjgl.opengl.GL11.glClear;
import static org.lwjgl.opengl.GL11.glClearColor;
import static org.lwjgl.opengl.GL11.glColor3f;
import static org.lwjgl.opengl.GL11.glDisable;
import static org.lwjgl.opengl.GL11.glEnable;
import static org.lwjgl.opengl.GL11.glEnd;
import static org.lwjgl.opengl.GL11.glFogf;
import static org.lwjgl.opengl.GL11.glFogfv;
import static org.lwjgl.opengl.GL11.glFogi;
import static org.lwjgl.opengl.GL11.glFrustum;
import static org.lwjgl.opengl.GL11.glGenTextures;
import static org.lwjgl.opengl.GL11.glLoadIdentity;
import static org.lwjgl.opengl.GL11.glMatrixMode;
import static org.lwjgl.opengl.GL11.glOrtho;
import static org.lwjgl.opengl.GL11.glRotatef;
import static org.lwjgl.opengl.GL11.glTexCoord2f;
import static org.lwjgl.opengl.GL11.glTexImage2D;
import static org.lwjgl.opengl.GL11.glTexParameteri;
import static org.lwjgl.opengl.GL11.glTranslatef;
import static org.lwjgl.opengl.GL11.glVertex2f;
import static org.lwjgl.opengl.GL11.glVertex3d;
import static org.lwjgl.opengl.GL11.glViewport;
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
        glEnable(GL_TEXTURE_2D);
        glEnable(GL_FOG);
        glFogi(GL_FOG_MODE, GL_LINEAR);
        glFogf(GL_FOG_START, 1.6f);
        glFogf(GL_FOG_END, 14f);
        try (MemoryStack stack = MemoryStack.stackPush()) {
            FloatBuffer fog = stack.mallocFloat(4);
            fog.put(ExplorePaint.SKY_R).put(ExplorePaint.SKY_G).put(ExplorePaint.SKY_B).put(1f);
            fog.flip();
            glFogfv(GL_FOG_COLOR, fog);
        }
        glClearColor(ExplorePaint.SKY_R, ExplorePaint.SKY_G, ExplorePaint.SKY_B, 1f);
        int wallTex = upload(ExplorePaint.brickRgba());
        int floorTex = upload(ExplorePaint.floorRgba());
        int ceilTex = upload(ExplorePaint.ceilingRgba());

        Optional<XrRuntime> xr = XrRuntimes.firstPresent(ExploreHost.class.getClassLoader());
        xr.ifPresent(runtime -> runtime.attach(world));

        double last = System.nanoTime();
        double[] cursor = {0, 0};
        boolean liveDown = false;
        boolean jamDown = false;
        boolean harden = false;
        GLFWGamepadState pad = GLFWGamepadState.create();
        boolean[] snapHeld = {false, false};
        int frames = 0;
        while (!glfwWindowShouldClose(window)) {
            glfwPollEvents();
            if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS) {
                glfwSetWindowShouldClose(window, true);
            }
            double now = System.nanoTime();
            double dt = Math.min(0.05, (now - last) / 1_000_000_000.0);
            last = now;

            ExploreInput.Intent intent = keys(window).plus(mouse(window, cursor))
                    .plus(pad(pad, dt, snapHeld));
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

            draw(window, world, wallTex, floorTex, ceilTex);
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

    private static ExploreInput.Intent pad(GLFWGamepadState state, double dt,
                                         boolean[] snapHeld) {
        if (!glfwJoystickIsGamepad(GLFW_JOYSTICK_1) || !glfwGetGamepadState(GLFW_JOYSTICK_1, state)) {
            return ExploreInput.Intent.none();
        }
        boolean left = state.buttons(GLFW_GAMEPAD_BUTTON_DPAD_LEFT) == GLFW_PRESS;
        boolean right = state.buttons(GLFW_GAMEPAD_BUTTON_DPAD_RIGHT) == GLFW_PRESS;
        boolean snapLeft = left && !snapHeld[0];
        boolean snapRight = right && !snapHeld[1];
        snapHeld[0] = left;
        snapHeld[1] = right;
        return ExploreInput.gamepad(
                state.axes(GLFW_GAMEPAD_AXIS_LEFT_X),
                state.axes(GLFW_GAMEPAD_AXIS_LEFT_Y),
                state.axes(GLFW_GAMEPAD_AXIS_RIGHT_X),
                state.axes(GLFW_GAMEPAD_AXIS_RIGHT_Y),
                snapLeft, snapRight, dt);
    }

    private static int upload(byte[] rgba) {
        int id = glGenTextures();
        glBindTexture(GL_TEXTURE_2D, id);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
        ByteBuffer buf = MemoryUtil.memAlloc(rgba.length);
        buf.put(rgba).flip();
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, ExplorePaint.TEX, ExplorePaint.TEX, 0,
                GL_RGBA, GL_UNSIGNED_BYTE, buf);
        MemoryUtil.memFree(buf);
        return id;
    }

    private static void draw(long window, ExploreWorld world, int wallTex, int floorTex,
                             int ceilTex) {
        int width;
        int height;
        try (MemoryStack stack = MemoryStack.stackPush()) {
            IntBuffer w = stack.mallocInt(1);
            IntBuffer h = stack.mallocInt(1);
            glfwGetWindowSize(window, w, h);
            width = Math.max(1, w.get(0));
            height = Math.max(1, h.get(0));
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
        glEnable(GL_TEXTURE_2D);
        glEnable(GL_FOG);
        float[] rgb = new float[3];
        float[] uv = new float[2];
        faces(world, ExploreMesh.Face.WALL, wallTex, rgb, uv);
        faces(world, ExploreMesh.Face.FLOOR, floorTex, rgb, uv);
        faces(world, ExploreMesh.Face.CEILING, ceilTex, rgb, uv);
        glBindTexture(GL_TEXTURE_2D, 0);
        glDisable(GL_TEXTURE_2D);
        glBegin(GL_TRIANGLES);
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
        hud(width, height, world);
    }

    private static void faces(ExploreWorld world, ExploreMesh.Face face, int tex,
                              float[] rgb, float[] uv) {
        glBindTexture(GL_TEXTURE_2D, tex);
        glBegin(GL_TRIANGLES);
        for (ExploreMesh.Triangle tri : world.mesh().triangles()) {
            if (tri.face() != face) {
                continue;
            }
            ExploreBody body = world.body();
            ExplorePaint.tint(tri, world.fog().tileVisible(tri.tr(), tri.tc()), rgb,
                    body.x(), body.z(), body.yaw());
            glColor3f(rgb[0], rgb[1], rgb[2]);
            ExplorePaint.uv(tri, tri.x1(), tri.y1(), tri.z1(), uv);
            glTexCoord2f(uv[0], uv[1]);
            glVertex3d(tri.x1(), tri.y1(), tri.z1());
            ExplorePaint.uv(tri, tri.x2(), tri.y2(), tri.z2(), uv);
            glTexCoord2f(uv[0], uv[1]);
            glVertex3d(tri.x2(), tri.y2(), tri.z2());
            ExplorePaint.uv(tri, tri.x3(), tri.y3(), tri.z3(), uv);
            glTexCoord2f(uv[0], uv[1]);
            glVertex3d(tri.x3(), tri.y3(), tri.z3());
        }
        glEnd();
    }

    private static void hud(int width, int height, ExploreWorld world) {
        glDisable(GL_DEPTH_TEST);
        glDisable(GL_FOG);
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        double aspect = width / (double) height;
        glOrtho(-aspect, aspect, -1, 1, -1, 1);
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        glColor3f(0.92f, 0.84f, 0.28f);
        glBegin(GL_LINES);
        glVertex2f(-0.03f, 0);
        glVertex2f(0.03f, 0);
        glVertex2f(0, -0.04f);
        glVertex2f(0, 0.04f);
        glEnd();
        automap(aspect, world);
        glEnable(GL_DEPTH_TEST);
        glEnable(GL_FOG);
    }

    private static void automap(double aspect, ExploreWorld world) {
        List<ExplorePaint.MapDot> dots = ExplorePaint.automap(
                world.fog(), world.mesh(), world.body(), world.markers());
        if (dots.isEmpty()) {
            return;
        }
        double right = aspect - 0.05;
        double left = right - 0.40;
        double top = 0.93;
        double bot = top - 0.40;
        glColor3f(0.16f, 0.11f, 0.08f);
        fill(left - 0.014, bot - 0.014, right + 0.014, top + 0.014);
        glColor3f(0.04f, 0.03f, 0.03f);
        fill(left, bot, right, top);
        double sx = (right - left) / ExplorePaint.MAP;
        double sy = (top - bot) / ExplorePaint.MAP;
        glBegin(GL_QUADS);
        for (ExplorePaint.MapDot dot : dots) {
            mapColor(dot.kind());
            double x0 = left + dot.x() * sx;
            double y0 = bot + dot.y() * sy;
            glVertex2f((float) x0, (float) y0);
            glVertex2f((float) (x0 + sx), (float) y0);
            glVertex2f((float) (x0 + sx), (float) (y0 + sy));
            glVertex2f((float) x0, (float) (y0 + sy));
        }
        glEnd();
    }

    private static void mapColor(ExplorePaint.MapKind kind) {
        switch (kind) {
            case WALL -> glColor3f(0.62f, 0.38f, 0.20f);
            case HERE -> glColor3f(0.95f, 0.86f, 0.28f);
            case MARK -> glColor3f(0.78f, 0.22f, 0.16f);
            default -> glColor3f(0.28f, 0.20f, 0.12f);
        }
    }

    private static void fill(double x0, double y0, double x1, double y1) {
        glBegin(GL_QUADS);
        glVertex2f((float) x0, (float) y0);
        glVertex2f((float) x1, (float) y0);
        glVertex2f((float) x1, (float) y1);
        glVertex2f((float) x0, (float) y1);
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
