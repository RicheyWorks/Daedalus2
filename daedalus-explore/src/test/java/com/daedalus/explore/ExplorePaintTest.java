// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

class ExplorePaintTest {

    @Test
    void visibleWallsAreTanNotSky() {
        float[] rgb = new float[3];
        ExplorePaint.tint(nsWall(0, 1.4, 0), true, rgb);
        assertThat(rgb[0]).isGreaterThan(0.4f);
        assertThat(rgb[0]).isGreaterThan(rgb[2]);
        assertThat(rgb[1]).isGreaterThan(rgb[2]);
    }

    @Test
    void eastWestWallsAreDarkerThanNorthSouth() {
        float[] ns = new float[3];
        float[] ew = new float[3];
        ExplorePaint.tint(nsWall(0, 1.4, 0), true, ns);
        ExplorePaint.tint(ewWall(0, 1.4, 0), true, ew);
        assertThat(ew[0]).isLessThan(ns[0]);
    }

    @Test
    void floorAndCeilingStayBrown() {
        float[] floor = new float[3];
        float[] ceil = new float[3];
        ExplorePaint.tint(face(ExploreMesh.Face.FLOOR, 0, 3, 3), true, floor);
        ExplorePaint.tint(face(ExploreMesh.Face.CEILING, 2.8, 3, 3), true, ceil);
        assertThat(floor[0]).isGreaterThan(floor[2]);
        assertThat(ceil[0]).isGreaterThan(ceil[2]);
        assertThat(ceil[0]).isLessThan(floor[0]);
    }

    @Test
    void unseenWallsStayASilhouette() {
        float[] rgb = new float[3];
        ExplorePaint.tint(nsWall(0, 1.4, 0), false, rgb);
        assertThat(rgb[0]).isCloseTo(0.09f, within(0.001f));
        ExplorePaint.tint(face(ExploreMesh.Face.FLOOR, 0, 0, 0), false, rgb);
        assertThat(rgb[0]).isEqualTo(ExplorePaint.SKY_R);
    }

    @Test
    void markersNameThePlace() {
        float[] rgb = new float[3];
        ExplorePaint.marker("ENTRANCE", rgb);
        assertThat(rgb[0]).isGreaterThan(rgb[2]);
        ExplorePaint.marker("BOSS", rgb);
        assertThat(rgb[0]).isGreaterThan(rgb[1]);
        ExplorePaint.marker("VAULT", rgb);
        assertThat(rgb[2]).isGreaterThan(rgb[0]);
    }

    @Test
    void badTargetsAreIgnored() {
        ExplorePaint.tint(nsWall(0, 1, 0), true, null);
        ExplorePaint.tint(nsWall(0, 1, 0), true, new float[2]);
        ExplorePaint.tint(null, true, new float[3]);
        ExplorePaint.marker("BOSS", null);
        ExplorePaint.marker("BOSS", new float[1]);
    }

    @Test
    void wainscotDarkensTheBoot() {
        float[] boot = new float[3];
        float[] high = new float[3];
        ExplorePaint.tint(nsWall(0, 0.2, 0), true, boot);
        ExplorePaint.tint(nsWall(0, 2.0, 0), true, high);
        assertThat(boot[0]).isLessThan(high[0]);
    }

    private static ExploreMesh.Triangle nsWall(double x, double y, double z) {
        return new ExploreMesh.Triangle(x, y, z, x + 1, y, z, x + 1, y + 0.4, z,
                ExploreMesh.Face.WALL, 2, 3);
    }

    private static ExploreMesh.Triangle ewWall(double x, double y, double z) {
        return new ExploreMesh.Triangle(x, y, z, x, y, z + 1, x, y + 0.4, z + 1,
                ExploreMesh.Face.WALL, 2, 3);
    }

    private static ExploreMesh.Triangle face(ExploreMesh.Face kind, double y, int tr, int tc) {
        return new ExploreMesh.Triangle(0, y, 0, 1, y, 0, 1, y, 1, kind, tr, tc);
    }
}
