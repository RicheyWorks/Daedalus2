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
        int skyTex = upload(ExplorePaint.skyRgba());
        int[] faceTex = {
                upload(ExplorePaint.faceRgba(0)),
                upload(ExplorePaint.faceRgba(1)),
                upload(ExplorePaint.faceRgba(2))
        };

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
            double stride = Math.hypot(intent.forward(), intent.strafe());

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

            draw(window, world, wallTex, floorTex, ceilTex, skyTex, faceTex, stride);
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
                             int ceilTex, int skyTex, int[] faceTex, double stride) {
        int width;
        int height;
        double aspect;
        try (MemoryStack stack = MemoryStack.stackPush()) {
            IntBuffer w = stack.mallocInt(1);
            IntBuffer h = stack.mallocInt(1);
            glfwGetWindowSize(window, w, h);
            width = Math.max(1, w.get(0));
            height = Math.max(1, h.get(0));
            aspect = width / (double) height;
            glViewport(0, 0, width, height);
        }
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        sky(world.body(), skyTex, aspect);
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glFrustum(-0.12 * aspect, 0.12 * aspect, -0.12, 0.12, 0.08, 200);
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        ExploreBody body = world.body();
        glRotatef((float) Math.toDegrees(-body.pitch()), 1, 0, 0);
        glRotatef((float) Math.toDegrees(-body.yaw()), 0, 1, 0);
        glTranslatef((float) -body.x(), (float) -ExploreBody.EYE_Y, (float) -body.z());
        glEnable(GL_DEPTH_TEST);
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
        hud(aspect, world, faceTex, stride);
    }

    private static void sky(ExploreBody body, int skyTex, double aspect) {
        glDisable(GL_DEPTH_TEST);
        glDisable(GL_FOG);
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(-aspect, aspect, -1, 1, -1, 1);
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        glEnable(GL_TEXTURE_2D);
        glBindTexture(GL_TEXTURE_2D, skyTex);
        glColor3f(1f, 1f, 1f);
        float span = (float) (1.15 * aspect);
        float[] bl = new float[2];
        float[] br = new float[2];
        float[] tr = new float[2];
        float[] tl = new float[2];
        ExplorePaint.skyUv(body.yaw(), body.pitch(), 0, 0.85f, bl);
        ExplorePaint.skyUv(body.yaw(), body.pitch(), span, 0.85f, br);
        ExplorePaint.skyUv(body.yaw(), body.pitch(), span, 0.15f, tr);
        ExplorePaint.skyUv(body.yaw(), body.pitch(), 0, 0.15f, tl);
        glBegin(GL_QUADS);
        glTexCoord2f(bl[0], bl[1]);
        glVertex2f((float) -aspect, -1f);
        glTexCoord2f(br[0], br[1]);
        glVertex2f((float) aspect, -1f);
        glTexCoord2f(tr[0], tr[1]);
        glVertex2f((float) aspect, 1f);
        glTexCoord2f(tl[0], tl[1]);
        glVertex2f((float) -aspect, 1f);
        glEnd();
        glBindTexture(GL_TEXTURE_2D, 0);
        glDisable(GL_TEXTURE_2D);
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

    private static void hud(double aspect, ExploreWorld world, int[] faceTex, double stride) {
        glDisable(GL_DEPTH_TEST);
        glDisable(GL_FOG);
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(-aspect, aspect, -1, 1, -1, 1);
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        ExplorePaint.Status line = ExplorePaint.status(
                world.fog(), world.body(), world.markers());
        status(aspect, line, faceTex);
        paintHand(aspect, line.mood(), stride);
        float aim = ExplorePaint.aimY();
        glColor3f(0.92f, 0.84f, 0.28f);
        glBegin(GL_LINES);
        glVertex2f(-0.03f, aim);
        glVertex2f(0.03f, aim);
        glVertex2f(0, aim - 0.04f);
        glVertex2f(0, aim + 0.04f);
        glEnd();
        automap(aspect, world);
        glEnable(GL_DEPTH_TEST);
        glEnable(GL_FOG);
    }

    private static void paintHand(double aspect, int mood, double stride) {
        float bob = ExplorePaint.handBob(System.nanoTime() / 1_000_000_000.0, stride);
        List<ExplorePaint.HandTri> mesh = ExplorePaint.handMesh(aspect, bob);
        float[] rgb = new float[3];
        glBegin(GL_TRIANGLES);
        for (ExplorePaint.HandTri tri : mesh) {
            ExplorePaint.handTint(tri.part(), mood, rgb);
            glColor3f(rgb[0], rgb[1], rgb[2]);
            glVertex2f(tri.x1(), tri.y1());
            glVertex2f(tri.x2(), tri.y2());
            glVertex2f(tri.x3(), tri.y3());
        }
        glEnd();
    }

    private static void status(double aspect, ExplorePaint.Status line, int[] faceTex) {
        float bot = -1f;
        float top = bot + ExplorePaint.STATUS_H;
        glColor3f(0.12f, 0.08f, 0.06f);
        fill(-aspect, bot, aspect, top);
        glColor3f(0.36f, 0.22f, 0.12f);
        fill(-aspect, top - 0.012, aspect, top);
        float faceLeft = (float) (-aspect + 0.04);
        float faceRight = faceLeft + 0.22f;
        float faceBot = bot + 0.03f;
        float faceTop = top - 0.03f;
        int mood = Math.max(0, Math.min(faceTex.length - 1, line.mood()));
        glEnable(GL_TEXTURE_2D);
        glBindTexture(GL_TEXTURE_2D, faceTex[mood]);
        glColor3f(1f, 1f, 1f);
        glBegin(GL_QUADS);
        glTexCoord2f(0, 1);
        glVertex2f(faceLeft, faceBot);
        glTexCoord2f(1, 1);
        glVertex2f(faceRight, faceBot);
        glTexCoord2f(1, 0);
        glVertex2f(faceRight, faceTop);
        glTexCoord2f(0, 0);
        glVertex2f(faceLeft, faceTop);
        glEnd();
        glBindTexture(GL_TEXTURE_2D, 0);
        glDisable(GL_TEXTURE_2D);
        paintCaption(ExplorePaint.caption(line), faceRight + 0.04f, bot + 0.09f);
        paintKeys(aspect, line);
    }

    private static void paintKeys(double aspect, ExplorePaint.Status line) {
        int marks = Math.max(0, Math.min(8, line.marks()));
        if (marks == 0) {
            return;
        }
        float[] rgb = new float[3];
        float cy = -1f + ExplorePaint.STATUS_H * 0.52f;
        float x = (float) (aspect - 0.08);
        for (int i = marks - 1; i >= 0; i--) {
            ExplorePaint.keyTint(i, marks, line.mood(), rgb);
            glColor3f(rgb[0], rgb[1], rgb[2]);
            diamond(x, cy, 0.028f);
            x -= 0.07f;
        }
    }

    private static void diamond(float cx, float cy, float r) {
        glBegin(GL_QUADS);
        glVertex2f(cx, cy + r);
        glVertex2f(cx + r, cy);
        glVertex2f(cx, cy - r);
        glVertex2f(cx - r, cy);
        glEnd();
    }

    private static void paintCaption(String text, float x0, float y0) {
        if (text == null || text.isEmpty()) {
            return;
        }
        float cell = 0.022f;
        float gap = 0.008f;
        float x = x0;
        glBegin(GL_QUADS);
        for (int i = 0; i < text.length(); i++) {
            char ch = text.charAt(i);
            if (ch == ' ') {
                x += (ExplorePaint.GLYPH_W + 1) * cell + gap;
                continue;
            }
            for (int gy = 0; gy < ExplorePaint.GLYPH_H; gy++) {
                for (int gx = 0; gx < ExplorePaint.GLYPH_W; gx++) {
                    if (!ExplorePaint.glyphDot(ch, gx, gy)) {
                        continue;
                    }
                    float px = x + gx * cell;
                    float py = y0 + (ExplorePaint.GLYPH_H - 1 - gy) * cell;
                    glColor3f(0.94f, 0.78f, 0.32f);
                    glVertex2f(px, py);
                    glVertex2f(px + cell, py);
                    glVertex2f(px + cell, py + cell);
                    glVertex2f(px, py + cell);
                }
            }
            x += (ExplorePaint.GLYPH_W + 1) * cell + gap;
        }
        glEnd();
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
