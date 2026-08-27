// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import java.util.List;

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
    void brickTextureHasMortarLines() {
        byte[] brick = ExplorePaint.brickRgba();
        byte[] floor = ExplorePaint.floorRgba();
        byte[] ceil = ExplorePaint.ceilingRgba();
        assertThat(brick).hasSize(ExplorePaint.TEX * ExplorePaint.TEX * 4);
        assertThat(floor).hasSize(brick.length);
        assertThat(ceil).hasSize(brick.length);
        int mortar = Byte.toUnsignedInt(brick[0]);
        int face = Byte.toUnsignedInt(brick[(2 * ExplorePaint.TEX + 2) * 4]);
        assertThat(face).isGreaterThan(mortar);
        assertThat(Byte.toUnsignedInt(floor[0])).isNotEqualTo(Byte.toUnsignedInt(brick[0]));
    }

    @Test
    void wallUvRunsAlongTheFace() {
        float[] uv = new float[2];
        ExplorePaint.uv(nsWall(0, 1.4, 0), 0, 1.4, 0, uv);
        assertThat(uv[0]).isZero();
        assertThat(uv[1]).isCloseTo(1.4f / (float) ExploreMesh.WALL_HEIGHT, within(0.001f));
        ExplorePaint.uv(face(ExploreMesh.Face.FLOOR, 0, 1, 1), 2, 0, 4, uv);
        assertThat(uv[0]).isCloseTo(2f / (float) ExploreMesh.TILE, within(0.001f));
        ExplorePaint.uv(null, 0, 0, 0, uv);
        ExplorePaint.uv(nsWall(0, 1, 0), 0, 1, 0, null);
    }

    @Test
    void torchPrefersWhatYouLookAt() {
        float[] ahead = new float[3];
        float[] behind = new float[3];
        ExplorePaint.tint(nsWall(0, 1.4, -3), true, ahead, 0, 0, 0);
        ExplorePaint.tint(nsWall(0, 1.4, 3), true, behind, 0, 0, 0);
        assertThat(ahead[0]).isGreaterThan(behind[0]);
    }

    @Test
    void automapKeepsUnseenTilesOffThePage() {
        MazeGrid grid = new MazeGrid(1, 2);
        grid.carve(grid.cell(0, 0), Direction.EAST);
        ExploreMesh mesh = ExploreMesh.of(grid);
        ExploreFog fog = new ExploreFog();
        assertThat(ExplorePaint.automap(null, mesh, null, null)).isEmpty();
        assertThat(ExplorePaint.automap(fog, mesh, null, null)).isEmpty();
        fog.stand(new Point(0, 0));
        List<ExplorePaint.MapDot> dots = ExplorePaint.automap(fog, mesh,
                ExploreBody.atCell(new Point(0, 0)),
                List.of(new ExploreMarker("door", new Point(0, 0), 0, "ENTRANCE")));
        assertThat(dots.stream().anyMatch(d -> d.kind() == ExplorePaint.MapKind.HERE)).isTrue();
        assertThat(dots.stream().anyMatch(d -> d.kind() == ExplorePaint.MapKind.WALL)).isTrue();
        assertThat(dots.stream().anyMatch(d -> d.kind() == ExplorePaint.MapKind.MARK)).isTrue();
    }

    @Test
    void wainscotDarkensTheBoot() {
        float[] boot = new float[3];
        float[] high = new float[3];
        ExplorePaint.tint(nsWall(0, 0.2, 0), true, boot);
        ExplorePaint.tint(nsWall(0, 2.0, 0), true, high);
        assertThat(boot[0]).isLessThan(high[0]);
    }

    @Test
    void skyAndFaceRastersFillTheAtlas() {
        byte[] sky = ExplorePaint.skyRgba();
        byte[] calm = ExplorePaint.faceRgba(0);
        byte[] grim = ExplorePaint.faceRgba(2);
        assertThat(sky).hasSize(ExplorePaint.TEX * ExplorePaint.TEX * 4);
        assertThat(calm).hasSize(sky.length);
        assertThat(Byte.toUnsignedInt(sky[0])).isNotEqualTo(0);
        int mouth = (44 * ExplorePaint.TEX + 28) * 4;
        assertThat(Byte.toUnsignedInt(grim[mouth]))
                .isLessThan(Byte.toUnsignedInt(calm[mouth]));
    }

    @Test
    void skyUvScrollsWithYaw() {
        float[] a = new float[2];
        float[] b = new float[2];
        ExplorePaint.skyUv(0, 0, 0.25f, 0.5f, a);
        ExplorePaint.skyUv(Math.PI, 0, 0.25f, 0.5f, b);
        assertThat(b[0]).isGreaterThan(a[0]);
        ExplorePaint.skyUv(0, 0, 0, 0, null);
        ExplorePaint.skyUv(0, 0, 0, 0, new float[1]);
    }

    @Test
    void statusNamesTheNearestVisibleMark() {
        ExploreFog fog = new ExploreFog();
        fog.stand(new Point(0, 0));
        ExploreBody body = ExploreBody.atCell(new Point(0, 0));
        ExplorePaint.Status hall = ExplorePaint.status(fog, body, List.of());
        assertThat(hall.place()).isEqualTo("HALL");
        assertThat(hall.facing()).isEqualTo("N");
        assertThat(ExplorePaint.caption(hall)).contains("HALL").contains("N");
        List<ExploreMarker> marks = List.of(
                new ExploreMarker("door", new Point(0, 0), 0, "ENTRANCE"),
                new ExploreMarker("boss", new Point(0, 1), 0, "BOSS"));
        ExplorePaint.Status near = ExplorePaint.status(fog, body, marks);
        assertThat(near.place()).isEqualTo("ENTRANCE");
        assertThat(near.marks()).isGreaterThanOrEqualTo(1);
        assertThat(ExplorePaint.status(null, null, null).place()).isEqualTo("HALL");
        assertThat(ExplorePaint.caption(null)).isEqualTo("HALL");
    }

    @Test
    void facingCompassFollowsYaw() {
        assertThat(ExplorePaint.facing(0)).isEqualTo("N");
        assertThat(ExplorePaint.facing(Math.PI / 2)).isEqualTo("E");
        assertThat(ExplorePaint.facing(Math.PI)).isEqualTo("S");
        assertThat(ExplorePaint.facing(-Math.PI / 2)).isEqualTo("W");
    }

    @Test
    void glyphsPaintLettersUsedOnTheStrip() {
        assertThat(ExplorePaint.glyphDot('H', 0, 0)).isTrue();
        assertThat(ExplorePaint.glyphDot('A', 2, 0)).isTrue();
        assertThat(ExplorePaint.glyphDot(' ', 0, 0)).isFalse();
        assertThat(ExplorePaint.glyphDot('H', -1, 0)).isFalse();
        assertThat(ExplorePaint.glyphDot('H', 0, 9)).isFalse();
        assertThat(ExplorePaint.glyphDot('1', 2, 0)).isTrue();
    }

    @Test
    void aimSitsAboveTheStatusStrip() {
        assertThat(ExplorePaint.aimY()).isGreaterThan(0f);
        assertThat(ExplorePaint.aimY()).isEqualTo(ExplorePaint.STATUS_H * 0.5f);
    }

    @Test
    void keyTintMarksBossAndVaultApart() {
        float[] rgb = new float[3];
        ExplorePaint.keyTint(0, 1, 2, rgb);
        assertThat(rgb[0]).isGreaterThan(rgb[1]);
        ExplorePaint.keyTint(0, 1, 1, rgb);
        assertThat(rgb[2]).isGreaterThan(rgb[0]);
        ExplorePaint.keyTint(0, 2, 0, rgb);
        assertThat(rgb[0]).isGreaterThan(rgb[2]);
        ExplorePaint.keyTint(0, 1, 0, null);
        ExplorePaint.keyTint(0, 1, 0, new float[1]);
    }

    @Test
    void torchHandSitsAboveTheStripAndBobs() {
        List<ExplorePaint.HandTri> a = ExplorePaint.handMesh(1.6, 0);
        List<ExplorePaint.HandTri> b = ExplorePaint.handMesh(1.6, ExplorePaint.handBob(0.3));
        assertThat(a).isNotEmpty();
        assertThat(a.stream().anyMatch(t -> t.part() == ExplorePaint.HandPart.FLAME)).isTrue();
        assertThat(a.get(0).y1()).isGreaterThan(-1f + ExplorePaint.STATUS_H - 0.001f);
        assertThat(b.get(0).y1()).isNotEqualTo(a.get(0).y1());
        float[] calm = new float[3];
        float[] hot = new float[3];
        ExplorePaint.handTint(ExplorePaint.HandPart.FLAME, 0, calm);
        ExplorePaint.handTint(ExplorePaint.HandPart.FLAME, 2, hot);
        assertThat(hot[1]).isLessThan(calm[1]);
        assertThat(hot[2]).isLessThan(calm[2]);
        ExplorePaint.handTint(null, 0, calm);
        ExplorePaint.handTint(ExplorePaint.HandPart.GRIP, 0, null);
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
