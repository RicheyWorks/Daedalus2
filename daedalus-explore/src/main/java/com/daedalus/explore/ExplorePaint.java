// SPDX-License-Identifier: MIT

package com.daedalus.explore;

/**
 * Flat Doom-like tints for extruded faces. GLFW only applies these;
 * tests lock the palette so the well stays a maze, not a void.
 */
public final class ExplorePaint {

    public static final float SKY_R = 0.10f;
    public static final float SKY_G = 0.08f;
    public static final float SKY_B = 0.07f;

    private ExplorePaint() {
    }

    public static void tint(ExploreMesh.Triangle tri, boolean visible, float[] rgb) {
        if (rgb == null || rgb.length < 3 || tri == null || tri.face() == null) {
            return;
        }
        if (!visible) {
            if (tri.face() == ExploreMesh.Face.WALL) {
                set(rgb, 0.09f, 0.07f, 0.06f);
            } else {
                set(rgb, SKY_R, SKY_G, SKY_B);
            }
            return;
        }
        switch (tri.face()) {
            case FLOOR -> floor(tri, rgb);
            case CEILING -> set(rgb, 0.20f, 0.14f, 0.11f);
            case WALL -> wall(tri, rgb);
            default -> set(rgb, SKY_R, SKY_G, SKY_B);
        }
    }

    public static void marker(String kind, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        if ("BOSS".equals(kind)) {
            set(rgb, 0.72f, 0.18f, 0.12f);
        } else if ("ENTRANCE".equals(kind)) {
            set(rgb, 0.82f, 0.62f, 0.18f);
        } else {
            set(rgb, 0.28f, 0.52f, 0.58f);
        }
    }

    private static void floor(ExploreMesh.Triangle tri, float[] rgb) {
        float check = ((tri.tr() + tri.tc()) & 1) == 0 ? 1f : 0.82f;
        set(rgb, 0.34f * check, 0.24f * check, 0.14f * check);
    }

    private static void wall(ExploreMesh.Triangle tri, float[] rgb) {
        double nx = (tri.y2() - tri.y1()) * (tri.z3() - tri.z1())
                - (tri.z2() - tri.z1()) * (tri.y3() - tri.y1());
        double nz = (tri.x2() - tri.x1()) * (tri.y3() - tri.y1())
                - (tri.y2() - tri.y1()) * (tri.x3() - tri.x1());
        boolean eastWest = Math.abs(nx) > Math.abs(nz);
        double midY = (tri.y1() + tri.y2() + tri.y3()) / 3.0;
        float boot = midY < ExploreMesh.WALL_HEIGHT * 0.38 ? 0.70f : 1f;
        float stripe = stripe(tri, eastWest);
        float shade = boot * stripe;
        if (eastWest) {
            set(rgb, 0.48f * shade, 0.28f * shade, 0.16f * shade);
        } else {
            set(rgb, 0.64f * shade, 0.40f * shade, 0.22f * shade);
        }
    }

    private static float stripe(ExploreMesh.Triangle tri, boolean eastWest) {
        double u = eastWest
                ? (tri.z1() + tri.z2() + tri.z3()) / 3.0
                : (tri.x1() + tri.x2() + tri.x3()) / 3.0;
        int band = (int) Math.floor(u / ExploreMesh.TILE);
        return (band & 1) == 0 ? 1f : 0.84f;
    }

    private static void set(float[] rgb, float r, float g, float b) {
        rgb[0] = r;
        rgb[1] = g;
        rgb[2] = b;
    }
}
