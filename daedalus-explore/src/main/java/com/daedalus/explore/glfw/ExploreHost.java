// SPDX-License-Identifier: MIT

package com.daedalus.explore.glfw;

import com.daedalus.explore.ExploreBody;
import com.daedalus.explore.ExploreInput;
import com.daedalus.explore.ExploreMarker;
import com.daedalus.explore.ExploreMesh;
import com.daedalus.explore.ExplorePaint;
import com.daedalus.explore.ExploreWorld;
import com.daedalus.explore.WorldMesh;
import com.daedalus.explore.XrFrame;
import com.daedalus.explore.XrRuntime;
import com.daedalus.explore.XrRuntimes;
import org.lwjgl.glfw.GLFWErrorCallback;
import org.lwjgl.glfw.GLFWGamepadState;
import org.lwjgl.glfw.GLFWImage;
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
import static org.lwjgl.glfw.GLFW.GLFW_KEY_B;
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
import static org.lwjgl.glfw.GLFW.glfwSetWindowIcon;
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
import static org.lwjgl.opengl.GL11.GL_BLEND;
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
import static org.lwjgl.opengl.GL11.GL_ONE_MINUS_SRC_ALPHA;
import static org.lwjgl.opengl.GL11.GL_QUADS;
import static org.lwjgl.opengl.GL11.GL_PROJECTION;
import static org.lwjgl.opengl.GL11.GL_REPEAT;
import static org.lwjgl.opengl.GL11.GL_RGBA;
import static org.lwjgl.opengl.GL11.GL_SRC_ALPHA;
import static org.lwjgl.opengl.GL11.GL_TEXTURE_2D;
import static org.lwjgl.opengl.GL11.GL_TEXTURE_MAG_FILTER;
import static org.lwjgl.opengl.GL11.GL_TEXTURE_MIN_FILTER;
import static org.lwjgl.opengl.GL11.GL_TEXTURE_WRAP_S;
import static org.lwjgl.opengl.GL11.GL_TEXTURE_WRAP_T;
import static org.lwjgl.opengl.GL11.GL_TRIANGLE_FAN;
import static org.lwjgl.opengl.GL11.GL_TRIANGLES;
import static org.lwjgl.opengl.GL11.GL_UNSIGNED_BYTE;
import static org.lwjgl.opengl.GL11.glBegin;
import static org.lwjgl.opengl.GL11.glBindTexture;
import static org.lwjgl.opengl.GL11.glBlendFunc;
import static org.lwjgl.opengl.GL11.glClear;
import static org.lwjgl.opengl.GL11.glClearColor;
import static org.lwjgl.opengl.GL11.glColor3f;
import static org.lwjgl.opengl.GL11.glColor4f;
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
        long window = glfwCreateWindow(1280, 720, "DAEDALUS", NULL, NULL);
        if (window == NULL) {
            glfwTerminate();
            throw new IllegalStateException("Failed to create the explore window");
        }
        try (MemoryStack stack = MemoryStack.stackPush()) {
            byte[] rgba = ExplorePaint.windowIconRgba();
            ByteBuffer pixels = stack.malloc(rgba.length);
            pixels.put(rgba).flip();
            GLFWImage.Buffer icons = GLFWImage.malloc(1, stack);
            icons.width(ExplorePaint.WINDOW_ICON_SIZE);
            icons.height(ExplorePaint.WINDOW_ICON_SIZE);
            icons.pixels(pixels);
            glfwSetWindowIcon(window, icons);
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
            fog.put(ExplorePaint.FOG_R).put(ExplorePaint.FOG_G).put(ExplorePaint.FOG_B).put(1f);
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
        boolean blocksDown = false;
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
            boolean b = glfwGetKey(window, GLFW_KEY_B) == GLFW_PRESS;
            if (b && !blocksDown) {
                world.toggleBlocks();
            }
            blocksDown = b;
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
        double seconds = System.nanoTime() / 1_000_000_000.0;
        sky(world.body(), skyTex, aspect, seconds);
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
        faces(world, ExploreMesh.Face.WALL, wallTex, rgb, uv, seconds);
        faces(world, ExploreMesh.Face.FLOOR, floorTex, rgb, uv, seconds);
        faces(world, ExploreMesh.Face.CEILING, ceilTex, rgb, uv, seconds);
        glBindTexture(GL_TEXTURE_2D, 0);
        glDisable(GL_TEXTURE_2D);
        blockFaces(world, rgb, seconds);
        glBegin(GL_TRIANGLES);
        float[] pad = new float[3];
        for (ExploreMarker marker : world.markers()) {
            int tr = 2 * marker.cell().row() + 1;
            int tc = 2 * marker.cell().col() + 1;
            if (!world.fog().tileVisible(tr, tc)) {
                continue;
            }
            ExplorePaint.marker(marker.kind(), rgb);
            double wx = ExploreMesh.worldX(marker.cell().col());
            double wz = ExploreMesh.worldZ(marker.cell().row());
            var tiles = world.mesh() == null ? null : world.mesh().tiles();
            int th = tiles == null ? 1 : tiles.length;
            int tw = tiles == null || tiles[0] == null ? 1 : tiles[0].length;
            ExplorePaint.placePadTint(rgb, pad, seconds,
                    ExplorePaint.mapEdge(tr, tc, 0, th - 1, 0, tw - 1));
            placePad(wx, wz, pad[0], pad[1], pad[2]);
            for (ExplorePaint.PillarTri tri : ExplorePaint.pillarMesh(wx, wz)) {
                ExplorePaint.pillarTint(rgb, tri.boot(), tri.crown(), pad);
                glColor3f(pad[0], pad[1], pad[2]);
                glVertex3d(tri.x1(), tri.y1(), tri.z1());
                glVertex3d(tri.x2(), tri.y2(), tri.z2());
                glVertex3d(tri.x3(), tri.y3(), tri.z3());
            }
        }
        var endTiles = world.mesh() == null ? null : world.mesh().tiles();
        int endH = endTiles == null ? 1 : endTiles.length;
        int endW = endTiles == null || endTiles[0] == null ? 1 : endTiles[0].length;
        for (ExplorePaint.EndPlace end : ExplorePaint.endPlaces(world.fog(), world.mesh())) {
            ExplorePaint.mapEndTint(end.kind(), rgb);
            ExplorePaint.placePadTint(rgb, pad, seconds,
                    ExplorePaint.mapEdge(end.tileRow(), end.tileCol(), 0, endH - 1, 0, endW - 1));
            placePad(end.x(), end.z(), pad[0], pad[1], pad[2]);
        }
        if (world.showingBlocks() && world.blocks() != null) {
            for (ExplorePaint.BlockPlace cube : ExplorePaint.blockPlaces(world.blocks())) {
                ExplorePaint.blockPlaceTint(cube.type(), rgb);
                ExplorePaint.placePadTint(rgb, pad, seconds,
                        ExplorePaint.mapEdge(cube.tileRow(), cube.tileCol(), 0, endH - 1, 0, endW - 1));
                placePad(cube.x(), cube.z(), pad[0], pad[1], pad[2], ExplorePaint.BLOCK_PAD_R);
            }
        }
        glEnd();
        hud(aspect, world, faceTex, stride, seconds);
    }

    private static void sky(ExploreBody body, int skyTex, double aspect, double seconds) {
        glDisable(GL_DEPTH_TEST);
        glDisable(GL_FOG);
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(-aspect, aspect, -1, 1, -1, 1);
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        glEnable(GL_TEXTURE_2D);
        glBindTexture(GL_TEXTURE_2D, skyTex);
        float twinkle = ExplorePaint.skyTwinkle(seconds);
        glColor3f(twinkle, twinkle * 0.96f, twinkle * 0.90f);
        float span = (float) (1.15 * aspect);
        float[] bl = new float[2];
        float[] br = new float[2];
        float[] tr = new float[2];
        float[] tl = new float[2];
        ExplorePaint.skyUv(body.yaw(), body.pitch(), 0, 0.85f, bl, seconds);
        ExplorePaint.skyUv(body.yaw(), body.pitch(), span, 0.85f, br, seconds);
        ExplorePaint.skyUv(body.yaw(), body.pitch(), span, 0.15f, tr, seconds);
        ExplorePaint.skyUv(body.yaw(), body.pitch(), 0, 0.15f, tl, seconds);
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

    private static void blockFaces(ExploreWorld world, float[] rgb, double seconds) {
        if (!world.showingBlocks() || world.blocks() == null) {
            return;
        }
        ExploreBody body = world.body();
        var tiles = world.mesh() == null ? null : world.mesh().tiles();
        int th = tiles == null ? 1 : tiles.length;
        int tw = tiles == null || tiles[0] == null ? 1 : tiles[0].length;
        glBegin(GL_TRIANGLES);
        for (WorldMesh.Triangle tri : world.blocks().triangles()) {
            double edge = 0;
            if (tri != null && tri.at() != null) {
                int col = ExploreMesh.cellCol(tri.at().x() + 0.5);
                int row = ExploreMesh.cellRow(tri.at().z() + 0.5);
                edge = ExplorePaint.mapEdge(2 * row + 1, 2 * col + 1, 0, th - 1, 0, tw - 1);
            }
            ExplorePaint.blockTint(tri, rgb, body.x(), body.z(), body.yaw(), seconds, edge,
                    world.blocks().world());
            glColor3f(rgb[0], rgb[1], rgb[2]);
            glVertex3d(tri.x1(), tri.y1(), tri.z1());
            glVertex3d(tri.x2(), tri.y2(), tri.z2());
            glVertex3d(tri.x3(), tri.y3(), tri.z3());
        }
        glEnd();
    }

    private static void faces(ExploreWorld world, ExploreMesh.Face face, int tex,
                              float[] rgb, float[] uv, double seconds) {
        var tiles = world.mesh().tiles();
        int th = tiles == null ? 1 : tiles.length;
        int tw = tiles == null || tiles[0] == null ? 1 : tiles[0].length;
        glBindTexture(GL_TEXTURE_2D, tex);
        glBegin(GL_TRIANGLES);
        for (ExploreMesh.Triangle tri : world.mesh().triangles()) {
            if (tri.face() != face) {
                continue;
            }
            ExploreBody body = world.body();
            ExplorePaint.tint(tri, world.fog().tileVisible(tri.tr(), tri.tc()), rgb,
                    body.x(), body.z(), body.yaw(), seconds,
                    ExplorePaint.mapEdge(tri.tr(), tri.tc(), 0, th - 1, 0, tw - 1));
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

    private static void hud(double aspect, ExploreWorld world, int[] faceTex, double stride,
                            double seconds) {
        glDisable(GL_DEPTH_TEST);
        glDisable(GL_FOG);
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(-aspect, aspect, -1, 1, -1, 1);
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        vignette(aspect, seconds);
        ExplorePaint.Status line = ExplorePaint.status(
                world.fog(), world.body(), world.markers(), world.mesh(),
                world.showingBlocks() ? world.blocks() : null);
        status(aspect, line, faceTex, seconds);
        paintHand(aspect, line.mood(), stride);
        float aim = ExplorePaint.aimY();
        float soft = ExplorePaint.aimSoftArm(seconds);
        float thick = ExplorePaint.aimSoftThick(seconds);
        glColor3f(ExplorePaint.AIM_SOFT_R, ExplorePaint.AIM_SOFT_G, ExplorePaint.AIM_SOFT_B);
        fill(-soft, aim - thick / 2f, soft, aim + thick / 2f);
        fill(-thick / 2f, aim - soft, thick / 2f, aim + soft);
        glColor3f(ExplorePaint.AIM_BRIGHT_R, ExplorePaint.AIM_BRIGHT_G, ExplorePaint.AIM_BRIGHT_B);
        float arm = ExplorePaint.AIM_ARM;
        glBegin(GL_LINES);
        glVertex2f(-arm, aim);
        glVertex2f(arm, aim);
        glVertex2f(0, aim - arm * 1.33f);
        glVertex2f(0, aim + arm * 1.33f);
        glEnd();
        automap(aspect, world, seconds);
        glEnable(GL_DEPTH_TEST);
        glEnable(GL_FOG);
    }

    /** Soft edge shade over the playable band — tunnel presence, not a flat box. */
    private static void vignette(double aspect, double seconds) {
        float inset = ExplorePaint.VIGNETTE_INSET;
        float top = 1f;
        float playBot = -1f + ExplorePaint.STATUS_H;
        float a = ExplorePaint.vignetteAlpha(seconds);
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        glColor4f(ExplorePaint.VIGNETTE_R, ExplorePaint.VIGNETTE_G, ExplorePaint.VIGNETTE_B, a);
        fill(-aspect, top - inset, aspect, top);
        fill(-aspect, playBot, -aspect + inset, top);
        fill(aspect - inset, playBot, aspect, top);
        glDisable(GL_BLEND);
    }

    private static void paintHand(double aspect, int mood, double stride) {
        double seconds = System.nanoTime() / 1_000_000_000.0;
        float bob = ExplorePaint.handBob(seconds, stride);
        List<ExplorePaint.HandTri> mesh = ExplorePaint.handMesh(aspect, bob);
        float[] rgb = new float[3];
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        for (ExplorePaint.TorchBloom bloom : ExplorePaint.torchBloomWash(aspect, bob, seconds)) {
            glColor4f(ExplorePaint.BLOOM_R, ExplorePaint.BLOOM_G, ExplorePaint.BLOOM_B, bloom.a());
            fill(bloom.x() - bloom.rx(), bloom.y() - bloom.ry(),
                    bloom.x() + bloom.rx(), bloom.y() + bloom.ry());
        }
        glDisable(GL_BLEND);
        glBegin(GL_TRIANGLES);
        for (ExplorePaint.HandTri tri : mesh) {
            ExplorePaint.handTint(tri.part(), mood, rgb, seconds);
            glColor3f(rgb[0], rgb[1], rgb[2]);
            glVertex2f(tri.x1(), tri.y1());
            glVertex2f(tri.x2(), tri.y2());
            glVertex2f(tri.x3(), tri.y3());
        }
        glEnd();
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        for (ExplorePaint.DustMote mote : ExplorePaint.dustMotes(aspect, bob, seconds)) {
            glColor4f(ExplorePaint.DUST_R, ExplorePaint.DUST_G, ExplorePaint.DUST_B, mote.a());
            fill(mote.x() - mote.half(), mote.y() - mote.half(),
                    mote.x() + mote.half(), mote.y() + mote.half());
        }
        glDisable(GL_BLEND);
    }

    private static void status(double aspect, ExplorePaint.Status line, int[] faceTex,
                               double seconds) {
        float bot = -1f;
        float top = bot + ExplorePaint.STATUS_H;
        fillHud(-aspect, bot, aspect, top);
        float[] lipInk = new float[3];
        ExplorePaint.statusLipTint(lipInk);
        glColor3f(ExplorePaint.STATUS_GOLD_UNDER_R, ExplorePaint.STATUS_GOLD_UNDER_G,
                ExplorePaint.STATUS_GOLD_UNDER_B);
        fill(-aspect, top - ExplorePaint.statusGoldUnderH(seconds), aspect, top);
        glColor3f(lipInk[0], lipInk[1], lipInk[2]);
        fill(-aspect, top - ExplorePaint.statusGoldH(seconds), aspect, top);
        float faceLeft = (float) (-aspect + 0.04);
        float faceRight = faceLeft + 0.22f;
        float faceBot = bot + 0.03f;
        float faceTop = top - 0.03f;
        float lip = ExplorePaint.faceLip(seconds);
        float core = ExplorePaint.faceLipCore(seconds);
        glColor3f(ExplorePaint.STATUS_GOLD_UNDER_R, ExplorePaint.STATUS_GOLD_UNDER_G,
                ExplorePaint.STATUS_GOLD_UNDER_B);
        fill(faceLeft - lip, faceBot - lip, faceRight + lip, faceTop + lip);
        glColor3f(lipInk[0], lipInk[1], lipInk[2]);
        fill(faceLeft - core, faceBot - core, faceRight + core, faceTop + core);
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
        paintCaption(line, faceRight + 0.04f, bot + 0.09f, seconds);
        paintKeys(aspect, line, seconds);
    }

    private static void paintKeys(double aspect, ExplorePaint.Status line, double seconds) {
        int marks = Math.max(0, Math.min(8, line.marks()));
        boolean startSeen = line != null && line.startSeen();
        boolean goalSeen = line != null && line.goalSeen();
        boolean blockSeen = line != null && line.blockSeen();
        if (marks == 0 && !startSeen && !goalSeen && !blockSeen) {
            return;
        }
        float[] rgb = new float[3];
        float cy = -1f + ExplorePaint.STATUS_H * 0.52f;
        float x = (float) (aspect - 0.08);
        float softPad = ExplorePaint.keySoftPad(seconds);
        for (int i = marks - 1; i >= 0; i--) {
            ExplorePaint.keySoftTint(i, marks, line.mood(), rgb);
            glColor3f(rgb[0], rgb[1], rgb[2]);
            diamond(x, cy, 0.028f * softPad);
            ExplorePaint.keyTint(i, marks, line.mood(), rgb);
            glColor3f(rgb[0], rgb[1], rgb[2]);
            diamond(x, cy, 0.028f);
            x -= 0.07f;
        }
        if (blockSeen) {
            x = keyBlock(x, cy, softPad);
        }
        if (goalSeen) {
            x = keyEnd(x, cy, softPad, ExplorePaint.MapKind.GOAL);
        }
        if (startSeen) {
            keyEnd(x, cy, softPad, ExplorePaint.MapKind.START);
        }
    }

    private static float keyBlock(float x, float cy, float softPad) {
        float[] rgb = new float[3];
        ExplorePaint.keyBlockSoftTint(rgb);
        glColor3f(rgb[0], rgb[1], rgb[2]);
        diamond(x, cy, 0.028f * softPad);
        ExplorePaint.keyBlockTint(rgb);
        glColor3f(rgb[0], rgb[1], rgb[2]);
        diamond(x, cy, 0.028f);
        return x - 0.07f;
    }

    private static float keyEnd(float x, float cy, float softPad, ExplorePaint.MapKind kind) {
        float[] rgb = new float[3];
        ExplorePaint.keyEndSoftTint(kind, rgb);
        glColor3f(rgb[0], rgb[1], rgb[2]);
        diamond(x, cy, 0.028f * softPad);
        ExplorePaint.keyEndTint(kind, rgb);
        glColor3f(rgb[0], rgb[1], rgb[2]);
        diamond(x, cy, 0.028f);
        return x - 0.07f;
    }

    private static void diamond(float cx, float cy, float r) {
        glBegin(GL_QUADS);
        glVertex2f(cx, cy + r);
        glVertex2f(cx + r, cy);
        glVertex2f(cx, cy - r);
        glVertex2f(cx - r, cy);
        glEnd();
    }

    private static void paintCaption(ExplorePaint.Status line, float x0, float y0,
                                     double seconds) {
        String place = ExplorePaint.captionPlace(line);
        String meta = ExplorePaint.captionMeta(line);
        float gap = 0.008f;
        float placeCell = ExplorePaint.CAPTION_PLACE_CELL;
        float metaCell = ExplorePaint.CAPTION_META_CELL;
        float softPad = ExplorePaint.captionSoftPad(seconds);
        float placePad = placeCell * softPad;
        float metaPad = metaCell * softPad;
        float[] placeSoft = new float[3];
        float[] placeInk = new float[3];
        ExplorePaint.captionPlaceSoftTint(place, placeSoft);
        ExplorePaint.captionPlaceTint(place, placeInk);
        paintCaptionPass(place, x0, y0, placeCell, gap, placePad,
                placeSoft[0], placeSoft[1], placeSoft[2]);
        paintCaptionPass(place, x0, y0, placeCell, gap, 0,
                placeInk[0], placeInk[1], placeInk[2]);
        float metaX = x0 + ExplorePaint.captionWidth(place, placeCell, gap) + 0.02f;
        float metaY = y0 + (placeCell - metaCell) * ExplorePaint.GLYPH_H * 0.5f;
        if (!meta.isEmpty()) {
            paintCaptionPass(meta, metaX, metaY, metaCell, gap, metaPad,
                    ExplorePaint.CAPTION_SOFT_R * 0.7f, ExplorePaint.CAPTION_SOFT_G * 0.7f,
                    ExplorePaint.CAPTION_SOFT_B * 0.7f);
            paintCaptionPass(meta, metaX, metaY, metaCell, gap, 0,
                    ExplorePaint.CAPTION_META_R, ExplorePaint.CAPTION_META_G,
                    ExplorePaint.CAPTION_META_B);
        }
    }

    private static void paintCaptionPass(String text, float x0, float y0, float cell, float gap,
                                         float pad, float r, float g, float b) {
        if (text == null || text.isEmpty()) {
            return;
        }
        float x = x0;
        glColor3f(r, g, b);
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
                    glVertex2f(px - pad, py - pad);
                    glVertex2f(px + cell + pad, py - pad);
                    glVertex2f(px + cell + pad, py + cell + pad);
                    glVertex2f(px - pad, py + cell + pad);
                }
            }
            x += (ExplorePaint.GLYPH_W + 1) * cell + gap;
        }
        glEnd();
    }

    private static void automap(double aspect, ExploreWorld world, double seconds) {
        List<ExplorePaint.MapDot> dots = ExplorePaint.automap(
                world.fog(), world.mesh(), world.body(), world.markers(),
                world.showingBlocks() ? world.blocks() : null);
        if (dots.isEmpty()) {
            return;
        }
        double right = aspect - 0.05;
        double left = right - 0.40;
        double top = 0.93;
        double bot = top - 0.40;
        float frameOut = ExplorePaint.mapFrameOut(seconds);
        float frameIn = ExplorePaint.mapFrameIn(seconds);
        float[] frameInk = new float[3];
        ExplorePaint.mapFrameTint(frameInk);
        glColor3f(frameInk[0], frameInk[1], frameInk[2]);
        fill(left - frameOut, bot - frameOut, right + frameOut, top + frameOut);
        glColor3f(ExplorePaint.STATUS_GOLD_UNDER_R, ExplorePaint.STATUS_GOLD_UNDER_G,
                ExplorePaint.STATUS_GOLD_UNDER_B);
        fill(left - frameIn, bot - frameIn, right + frameIn, top + frameIn);
        fillPocket(left, bot, right, top);
        double sx = (right - left) / ExplorePaint.MAP;
        double sy = (top - bot) / ExplorePaint.MAP;
        glBegin(GL_QUADS);
        for (ExplorePaint.MapDot dot : dots) {
            if (dot.kind() == ExplorePaint.MapKind.HERE
                    || dot.kind() == ExplorePaint.MapKind.MARK
                    || dot.kind() == ExplorePaint.MapKind.START
                    || dot.kind() == ExplorePaint.MapKind.GOAL
                    || dot.kind() == ExplorePaint.MapKind.BLOCK) {
                continue;
            }
            mapColor(dot.kind(), seconds, dot.edge());
            double x0 = left + dot.x() * sx;
            double y0 = bot + dot.y() * sy;
            glVertex2f((float) x0, (float) y0);
            glVertex2f((float) (x0 + sx), (float) y0);
            glVertex2f((float) (x0 + sx), (float) (y0 + sy));
            glVertex2f((float) x0, (float) (y0 + sy));
        }
        glEnd();
        float endHalo = ExplorePaint.mapEndHalo(seconds);
        for (ExplorePaint.MapDot dot : dots) {
            if (dot.kind() != ExplorePaint.MapKind.START
                    && dot.kind() != ExplorePaint.MapKind.GOAL) {
                continue;
            }
            double x0 = left + dot.x() * sx;
            double y0 = bot + dot.y() * sy;
            double padX = sx * endHalo;
            double padY = sy * endHalo;
            float[] ink = new float[3];
            ExplorePaint.mapEndSoftTint(dot.kind(), ink, dot.edge());
            glColor3f(ink[0], ink[1], ink[2]);
            fill(x0 - padX, y0 - padY, x0 + sx + padX, y0 + sy + padY);
            ExplorePaint.mapEndTint(dot.kind(), ink, dot.edge());
            glColor3f(ink[0], ink[1], ink[2]);
            fill(x0, y0, x0 + sx, y0 + sy);
        }
        float markHalo = ExplorePaint.mapMarkHalo(seconds);
        for (ExplorePaint.MapDot dot : dots) {
            if (dot.kind() != ExplorePaint.MapKind.MARK) {
                continue;
            }
            double x0 = left + dot.x() * sx;
            double y0 = bot + dot.y() * sy;
            double padX = sx * markHalo;
            double padY = sy * markHalo;
            float[] ink = new float[3];
            ExplorePaint.mapMarkSoftTint(dot.story(), ink, dot.edge());
            glColor3f(ink[0], ink[1], ink[2]);
            fill(x0 - padX, y0 - padY, x0 + sx + padX, y0 + sy + padY);
            ExplorePaint.mapMarkTint(dot.story(), ink, dot.edge());
            glColor3f(ink[0], ink[1], ink[2]);
            fill(x0, y0, x0 + sx, y0 + sy);
        }
        float blockHalo = ExplorePaint.mapBlockHalo(seconds);
        for (ExplorePaint.MapDot dot : dots) {
            if (dot.kind() != ExplorePaint.MapKind.BLOCK) {
                continue;
            }
            double x0 = left + dot.x() * sx;
            double y0 = bot + dot.y() * sy;
            double padX = sx * blockHalo;
            double padY = sy * blockHalo;
            float[] ink = new float[3];
            ExplorePaint.mapBlockSoftTint(dot.edge(), ink);
            glColor3f(ink[0], ink[1], ink[2]);
            fill(x0 - padX, y0 - padY, x0 + sx + padX, y0 + sy + padY);
            ExplorePaint.mapStoneTint(ExplorePaint.MapKind.BLOCK, seconds, dot.edge(), ink);
            glColor3f(ink[0], ink[1], ink[2]);
            fill(x0, y0, x0 + sx, y0 + sy);
        }
        float hereHalo = ExplorePaint.mapHereHalo(seconds);
        for (ExplorePaint.MapDot dot : dots) {
            if (dot.kind() != ExplorePaint.MapKind.HERE) {
                continue;
            }
            double x0 = left + dot.x() * sx;
            double y0 = bot + dot.y() * sy;
            double padX = sx * hereHalo;
            double padY = sy * hereHalo;
            float[] hereInk = new float[3];
            WorldMesh hereBlocks = world.showingBlocks() ? world.blocks() : null;
            ExplorePaint.mapHereSoftTint(world.body(), world.mesh(), hereBlocks, hereInk,
                    dot.edge());
            glColor3f(hereInk[0], hereInk[1], hereInk[2]);
            fill(x0 - padX, y0 - padY, x0 + sx + padX, y0 + sy + padY);
            ExplorePaint.mapHereTint(world.body(), world.mesh(), hereBlocks, hereInk,
                    dot.edge());
            glColor3f(hereInk[0], hereInk[1], hereInk[2]);
            fill(x0, y0, x0 + sx, y0 + sy);
        }
    }

    private static void mapColor(ExplorePaint.MapKind kind, double seconds, double edge) {
        float[] rgb = new float[3];
        switch (kind) {
            case HERE -> glColor3f(ExplorePaint.MAP_HERE_R, ExplorePaint.MAP_HERE_G,
                    ExplorePaint.MAP_HERE_B);
            case MARK -> glColor3f(ExplorePaint.MAP_MARK_R, ExplorePaint.MAP_MARK_G,
                    ExplorePaint.MAP_MARK_B);
            case START -> glColor3f(ExplorePaint.MAP_START_R, ExplorePaint.MAP_START_G,
                    ExplorePaint.MAP_START_B);
            case GOAL -> glColor3f(ExplorePaint.MAP_GOAL_R, ExplorePaint.MAP_GOAL_G,
                    ExplorePaint.MAP_GOAL_B);
            default -> {
                ExplorePaint.mapStoneTint(kind, seconds, edge, rgb);
                glColor3f(rgb[0], rgb[1], rgb[2]);
            }
        }
    }

    private static void fillHud(double x0, double y0, double x1, double y1) {
        float[] mid = new float[3];
        float[] rim = new float[3];
        ExplorePaint.hudVoidTint(0, mid);
        ExplorePaint.hudVoidTint(1, rim);
        fillWell(x0, y0, x1, y1, mid, rim);
    }

    private static void fillPocket(double x0, double y0, double x1, double y1) {
        float[] mid = new float[3];
        float[] rim = new float[3];
        ExplorePaint.mapPocketTint(0, mid);
        ExplorePaint.mapPocketTint(1, rim);
        fillWell(x0, y0, x1, y1, mid, rim);
    }

    private static void fillWell(double x0, double y0, double x1, double y1,
                                 float[] mid, float[] rim) {
        float cx = (float) ((x0 + x1) * 0.5);
        float cy = (float) ((y0 + y1) * 0.5);
        glBegin(GL_TRIANGLE_FAN);
        glColor3f(mid[0], mid[1], mid[2]);
        glVertex2f(cx, cy);
        glColor3f(rim[0], rim[1], rim[2]);
        glVertex2f((float) x0, (float) y0);
        glVertex2f((float) x1, (float) y0);
        glVertex2f((float) x1, (float) y1);
        glVertex2f((float) x0, (float) y1);
        glVertex2f((float) x0, (float) y0);
        glEnd();
    }

    private static void fill(double x0, double y0, double x1, double y1) {
        glBegin(GL_QUADS);
        glVertex2f((float) x0, (float) y0);
        glVertex2f((float) x1, (float) y0);
        glVertex2f((float) x1, (float) y1);
        glVertex2f((float) x0, (float) y1);
        glEnd();
    }

    private static void placePad(double x, double z, float r, float g, float b) {
        placePad(x, z, r, g, b, ExplorePaint.PLACE_PAD_R);
    }

    private static void placePad(double x, double z, float r, float g, float b, float rad) {
        double y = ExplorePaint.PLACE_PAD_Y;
        int segs = ExplorePaint.PLACE_PAD_SEGS;
        glColor3f(r, g, b);
        for (int i = 0; i < segs; i++) {
            double a0 = i * Math.PI * 2.0 / segs;
            double a1 = (i + 1) * Math.PI * 2.0 / segs;
            glVertex3d(x, y, z);
            glVertex3d(x + rad * Math.cos(a0), y, z + rad * Math.sin(a0));
            glVertex3d(x + rad * Math.cos(a1), y, z + rad * Math.sin(a1));
        }
    }

}
