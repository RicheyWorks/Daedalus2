// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import com.daedalus.model.TileType;
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
    void startAndGoalFloorsNameTheEnds() {
        float[] passage = new float[3];
        float[] gate = new float[3];
        float[] exit = new float[3];
        ExplorePaint.tint(face(ExploreMesh.Face.FLOOR, 0, 3, 3), true, passage);
        ExplorePaint.tint(endFloor(TileType.START), true, gate);
        ExplorePaint.tint(endFloor(TileType.GOAL), true, exit);
        assertThat(ExplorePaint.FLOOR_END_WEIGHT).isEqualTo(0.42f);
        assertThat(gate[1]).as("start floor lifts toward well mint").isGreaterThan(passage[1]);
        assertThat(exit[0]).as("goal floor lifts toward well coral").isGreaterThan(passage[0]);
        assertThat(gate[1]).isGreaterThan(gate[0]);
    }

    @Test
    void unseenWallsStayASilhouette() {
        float[] rgb = new float[3];
        ExplorePaint.tint(nsWall(0, 1.4, 0), false, rgb);
        assertThat(rgb[0]).isEqualTo(ExplorePaint.UNSEEN_R);
        assertThat(rgb[1]).isEqualTo(ExplorePaint.UNSEEN_G);
        assertThat(rgb[2]).isEqualTo(ExplorePaint.UNSEEN_B);
        assertThat(ExplorePaint.UNSEEN_R).isGreaterThan(ExplorePaint.UNSEEN_B);
        ExplorePaint.tint(face(ExploreMesh.Face.FLOOR, 0, 0, 0), false, rgb);
        assertThat(rgb[0]).isEqualTo(ExplorePaint.UNSEEN_R);
        ExplorePaint.tint(face(ExploreMesh.Face.CEILING, 2.8, 3, 3), false, rgb);
        assertThat(rgb[0]).isEqualTo(ExplorePaint.UNSEEN_R);
        assertThat(ExplorePaint.UNSEEN_R).isNotEqualTo(ExplorePaint.SKY_R);
        assertThat(ExplorePaint.FOG_R).isEqualTo(ExplorePaint.UNSEEN_R);
        assertThat(ExplorePaint.FOG_G).isEqualTo(ExplorePaint.UNSEEN_G);
        assertThat(ExplorePaint.FOG_B).isEqualTo(ExplorePaint.UNSEEN_B);
        assertThat(ExplorePaint.FOG_R).isNotEqualTo(ExplorePaint.SKY_R);
        assertThat(ExplorePaint.WINDOW_ICON_R).isEqualTo(12);
        assertThat(ExplorePaint.WINDOW_ICON_G).isEqualTo(9);
        assertThat(ExplorePaint.WINDOW_ICON_B).isEqualTo(8);
        assertThat(ExplorePaint.WINDOW_ICON_LIP_R).isEqualTo(184);
        assertThat(ExplorePaint.WINDOW_ICON_LIP_G).isEqualTo(133);
        assertThat(ExplorePaint.WINDOW_ICON_LIP_B).isEqualTo(56);
        byte[] icon = ExplorePaint.windowIconRgba();
        assertThat(icon).hasSize(ExplorePaint.WINDOW_ICON_SIZE * ExplorePaint.WINDOW_ICON_SIZE * 4);
        assertThat(icon[0] & 0xFF).isEqualTo(ExplorePaint.WINDOW_ICON_LIP_R);
        assertThat(icon[1] & 0xFF).isEqualTo(ExplorePaint.WINDOW_ICON_LIP_G);
        assertThat(icon[2] & 0xFF).isEqualTo(ExplorePaint.WINDOW_ICON_LIP_B);
        assertThat(icon[3] & 0xFF).isEqualTo(255);
        int mid = (ExplorePaint.WINDOW_ICON_SIZE / 2 * ExplorePaint.WINDOW_ICON_SIZE
                + ExplorePaint.WINDOW_ICON_SIZE / 2) * 4;
        assertThat(icon[mid] & 0xFF)
                .as("idle maze floors sit at the icon center")
                .isEqualTo(ExplorePaint.WINDOW_ICON_FLOOR_R);
        assertThat(icon[mid + 1] & 0xFF).isEqualTo(ExplorePaint.WINDOW_ICON_FLOOR_G);
        assertThat(icon[mid + 2] & 0xFF).isEqualTo(ExplorePaint.WINDOW_ICON_FLOOR_B);
        int start = (11 * ExplorePaint.WINDOW_ICON_SIZE + 7) * 4;
        assertThat(icon[start] & 0xFF)
                .as("start mint sits on the idle gate cell")
                .isEqualTo(ExplorePaint.WINDOW_ICON_START_R);
        int goal = (19 * ExplorePaint.WINDOW_ICON_SIZE + 23) * 4;
        assertThat(icon[goal] & 0xFF)
                .as("exit coral sits on the idle goal cell")
                .isEqualTo(ExplorePaint.WINDOW_ICON_GOAL_R);
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
        float[] pad = new float[3];
        ExplorePaint.placePadTint(rgb, pad);
        assertThat(pad[2]).isLessThan(rgb[2]);
        assertThat(ExplorePaint.PLACE_PAD_R).isGreaterThan(0.3f);
        assertThat(ExplorePaint.PLACE_PAD_SEGS).isGreaterThanOrEqualTo(8);
        assertThat(ExplorePaint.PLACE_PAD_BREATH_MS).isEqualTo(ExplorePaint.MAP_HERE_BREATH_MS);
        assertThat(ExplorePaint.placePadDim(0.1))
                .isNotEqualTo(ExplorePaint.placePadDim(0.8));
        ExplorePaint.placePadTint(null, pad);
        ExplorePaint.placePadTint(rgb, null);
        List<ExplorePaint.PillarTri> mesh = ExplorePaint.pillarMesh(0, 0);
        assertThat(mesh).isNotEmpty();
        assertThat(mesh.stream().anyMatch(ExplorePaint.PillarTri::boot)).isTrue();
        assertThat(mesh.stream().anyMatch(t -> !t.boot())).isTrue();
        assertThat(ExplorePaint.PILLAR_BOOT_FRAC).isEqualTo((float) ExplorePaint.CONTACT_BOOT_FRAC);
        float[] boot = new float[3];
        float[] shaft = new float[3];
        ExplorePaint.pillarTint(rgb, true, boot);
        ExplorePaint.pillarTint(rgb, false, shaft);
        assertThat(boot[0]).isLessThan(shaft[0]);
        ExplorePaint.pillarTint(null, true, boot);
        ExplorePaint.pillarTint(rgb, false, null);
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
        int brickShine = Byte.toUnsignedInt(brick[(1 * ExplorePaint.TEX + 2) * 4]);
        assertThat(face).isGreaterThan(mortar);
        assertThat(brickShine).isGreaterThan(face);
        assertThat(ExplorePaint.BRICK_TEX_HI_R).isGreaterThan(170);
        assertThat(ExplorePaint.BRICK_TEX_HI_R).isGreaterThan(ExplorePaint.BRICK_TEX_HI_B);
        assertThat(Byte.toUnsignedInt(floor[0])).isNotEqualTo(Byte.toUnsignedInt(brick[0]));
        int ceilR = Byte.toUnsignedInt(ceil[0]);
        int ceilB = Byte.toUnsignedInt(ceil[2]);
        assertThat(ceilR).isGreaterThan(ceilB);
        assertThat(ceilR).isGreaterThanOrEqualTo(ExplorePaint.CEILING_TEX_R);
        assertThat(ExplorePaint.CEILING_TEX_R).isGreaterThan(ExplorePaint.CEILING_TEX_B);
        assertThat(ExplorePaint.CEILING_TEX_R).isLessThan(92);
        int ceilShine = Byte.toUnsignedInt(ceil[(1 * ExplorePaint.TEX + 2) * 4]);
        int ceilBody = Byte.toUnsignedInt(ceil[(4 * ExplorePaint.TEX + 2) * 4]);
        assertThat(ceilShine).isGreaterThan(ceilBody);
        assertThat(ExplorePaint.CEILING_TEX_HI_R).isGreaterThan(ExplorePaint.CEILING_TEX_R);
        assertThat(ExplorePaint.CEILING_TEX_HI_R).isGreaterThan(ExplorePaint.CEILING_TEX_HI_B);
        int shine = Byte.toUnsignedInt(floor[(1 * ExplorePaint.TEX + 2) * 4]);
        int body = Byte.toUnsignedInt(floor[(4 * ExplorePaint.TEX + 2) * 4]);
        assertThat(shine).isGreaterThan(body);
        assertThat(ExplorePaint.FLOOR_TEX_HI_R).isGreaterThan(92);
        assertThat(ExplorePaint.FLOOR_TEX_HI_R).isGreaterThan(ExplorePaint.FLOOR_TEX_HI_B);
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
        float[] early = new float[3];
        float[] late = new float[3];
        ExplorePaint.tint(nsWall(0, 1.4, -3), true, early, 0, 0, 0, 0.05);
        ExplorePaint.tint(nsWall(0, 1.4, -3), true, late, 0, 0, 0, 0.18);
        assertThat(early[0]).isNotEqualTo(late[0]);
        assertThat(ExplorePaint.torchBreath(0.1))
                .isGreaterThan(ExplorePaint.TORCH_BREATH_BASE);
        assertThat(ExplorePaint.TORCH_BREATH_SPAN).isLessThan(0.2f);
        assertThat(ExplorePaint.TORCH_FLOOR_WARM_WEIGHT).isEqualTo(0.28f);
        assertThat(ExplorePaint.TORCH_WALL_WARM_WEIGHT).isEqualTo(0.45f);
        assertThat(ExplorePaint.TORCH_CEILING_WARM_WEIGHT).isEqualTo(0.36f);
        assertThat(ExplorePaint.TORCH_FLOOR_WARM_R).isEqualTo(0x5c / 255f);
        assertThat(ExplorePaint.TORCH_WALL_WARM_R).isEqualTo(0x2a / 255f);
        assertThat(ExplorePaint.CEILING_R).isGreaterThan(ExplorePaint.CEILING_B);
        assertThat(ExplorePaint.CEILING_R).isLessThan(0.34f);
        // Lit stone shifts toward torch-brown — R share drops vs a dim cold wall.
        float aheadShare = ahead[0] / Math.max(1e-6f, ahead[0] + ahead[1] + ahead[2]);
        float behindShare = behind[0] / Math.max(1e-6f, behind[0] + behind[1] + behind[2]);
        assertThat(aheadShare).isLessThan(behindShare);
        float[] lidAhead = new float[3];
        float[] lidBehind = new float[3];
        ExplorePaint.tint(ceilingAt(-3), true, lidAhead, 0, 0, 0);
        ExplorePaint.tint(ceilingAt(3), true, lidBehind, 0, 0, 0);
        assertThat(lidAhead[0]).isGreaterThan(lidBehind[0]);
        float lidShare = lidAhead[0] / Math.max(1e-6f, lidAhead[0] + lidAhead[1] + lidAhead[2]);
        assertThat(lidShare).isGreaterThan(0.40f);
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
        assertThat(dots.stream().anyMatch(d -> d.kind() == ExplorePaint.MapKind.START))
                .as("earned map names the revealed start mint")
                .isTrue();
        assertThat(dots.stream().anyMatch(d -> d.kind() == ExplorePaint.MapKind.GOAL))
                .as("earned map names the revealed goal coral")
                .isTrue();
        float[] gate = new float[3];
        ExplorePaint.mapEndTint(ExplorePaint.MapKind.START, gate);
        assertThat(gate[1]).isGreaterThan(gate[0]);
        assertThat(ExplorePaint.MAP_START_G).isEqualTo(0xe0 / 255f);
        float[] exit = new float[3];
        ExplorePaint.mapEndTint(ExplorePaint.MapKind.GOAL, exit);
        assertThat(exit[0]).isGreaterThan(exit[1]);
        assertThat(ExplorePaint.MAP_GOAL_R).isEqualTo(1f);
        float[] gateSoft = new float[3];
        ExplorePaint.mapEndSoftTint(ExplorePaint.MapKind.START, gateSoft);
        assertThat(gateSoft[1]).isLessThan(gate[1]);
        assertThat(ExplorePaint.MAP_END_HALO).isEqualTo(ExplorePaint.MAP_MARK_HALO);
        assertThat(ExplorePaint.mapEndHalo(0.1))
                .isNotEqualTo(ExplorePaint.mapEndHalo(0.8));
        ExplorePaint.mapEndTint(ExplorePaint.MapKind.START, null);
        ExplorePaint.mapEndSoftTint(ExplorePaint.MapKind.GOAL, null);
        assertThat(dots.stream().filter(d -> d.kind() == ExplorePaint.MapKind.MARK)
                .map(ExplorePaint.MapDot::story))
                .as("automap diamonds keep the story kind so vault teal is not leftover red")
                .containsExactly("ENTRANCE");
        float[] vault = new float[3];
        ExplorePaint.mapMarkTint("VAULT", vault);
        assertThat(vault[2]).isGreaterThan(vault[0]);
        float[] boss = new float[3];
        ExplorePaint.mapMarkTint("BOSS", boss);
        assertThat(boss[0]).isGreaterThan(boss[2]);
        float[] soft = new float[3];
        ExplorePaint.mapMarkSoftTint("VAULT", soft);
        assertThat(soft[2]).isLessThan(vault[2]);
        assertThat(ExplorePaint.MAP_MARK_SOFT_WEIGHT).isEqualTo(0.58f);
        assertThat(ExplorePaint.MAP_HERE_HALO)
                .as("HERE wears a soft pad wider than the cell")
                .isGreaterThan(0.5f);
        assertThat(ExplorePaint.MAP_HERE_R).isGreaterThan(ExplorePaint.MAP_HERE_SOFT_R);
        assertThat(ExplorePaint.mapHereHalo(0.1))
                .isNotEqualTo(ExplorePaint.mapHereHalo(0.8));
        assertThat(ExplorePaint.MAP_HERE_BREATH_MS).isEqualTo(2800f);
        assertThat(ExplorePaint.MAP_MARK_HALO)
                .as("story marks wear a soft pad like HERE")
                .isGreaterThan(0.4f);
        assertThat(ExplorePaint.mapMarkHalo(0.1))
                .isNotEqualTo(ExplorePaint.mapMarkHalo(0.8));
        assertThat(ExplorePaint.MAP_MARK_BREATH_MS).isEqualTo(ExplorePaint.MAP_HERE_BREATH_MS);
        assertThat(ExplorePaint.MAP_MARK_R).isGreaterThan(ExplorePaint.MAP_MARK_SOFT_R);
        assertThat(ExplorePaint.HUD_VOID_R).isEqualTo(0.12f);
        assertThat(ExplorePaint.HUD_VOID_G).isEqualTo(0.08f);
        assertThat(ExplorePaint.HUD_VOID_B).isEqualTo(0.06f);
        assertThat(ExplorePaint.MAP_POCKET_R).isLessThan(ExplorePaint.HUD_VOID_R);
        assertThat(ExplorePaint.MAP_POCKET_G).isLessThan(ExplorePaint.HUD_VOID_G);
        assertThat(ExplorePaint.MAP_POCKET_B).isLessThan(ExplorePaint.HUD_VOID_B);
        assertThat(ExplorePaint.MAP_POCKET_R).isGreaterThan(ExplorePaint.MAP_POCKET_B);
        assertThat(ExplorePaint.MAP_FRAME_OUT).isGreaterThan(ExplorePaint.MAP_FRAME_IN);
        assertThat(ExplorePaint.MAP_FRAME_BREATH_MS).isEqualTo(ExplorePaint.MAP_HERE_BREATH_MS);
        assertThat(ExplorePaint.mapFrameOut(0.1))
                .isNotEqualTo(ExplorePaint.mapFrameOut(0.8));
        assertThat(ExplorePaint.mapFrameIn(0.1))
                .isNotEqualTo(ExplorePaint.mapFrameIn(0.8));
    }

    @Test
    void automapStoneMatchesCorridorAndBreathes() {
        assertThat(ExplorePaint.MAP_FLOOR_R).isEqualTo(0.34f);
        assertThat(ExplorePaint.MAP_FLOOR_G).isEqualTo(0.24f);
        assertThat(ExplorePaint.MAP_FLOOR_B).isEqualTo(0.14f);
        assertThat(ExplorePaint.MAP_WALL_R).isEqualTo(0.64f);
        assertThat(ExplorePaint.MAP_WALL_G).isEqualTo(0.40f);
        assertThat(ExplorePaint.MAP_WALL_B).isEqualTo(0.22f);
        assertThat(ExplorePaint.MAP_STONE_BREATH_MS).isEqualTo(ExplorePaint.MAP_HERE_BREATH_MS);
        assertThat(ExplorePaint.mapStoneBreath(0.1))
                .isNotEqualTo(ExplorePaint.mapStoneBreath(0.8));
        float[] floor = new float[3];
        float[] wall = new float[3];
        ExplorePaint.mapStoneTint(ExplorePaint.MapKind.FLOOR, 0, floor);
        ExplorePaint.mapStoneTint(ExplorePaint.MapKind.WALL, 0, wall);
        assertThat(wall[0]).isGreaterThan(floor[0]);
        assertThat(floor[0]).isGreaterThan(floor[2]);
        float[] later = new float[3];
        ExplorePaint.mapStoneTint(ExplorePaint.MapKind.FLOOR, 0.7, later);
        assertThat(later[0]).isNotEqualTo(floor[0]);
        ExplorePaint.mapStoneTint(ExplorePaint.MapKind.WALL, 0, null);
    }

    @Test
    void wainscotDarkensTheBoot() {
        float[] boot = new float[3];
        float[] high = new float[3];
        ExplorePaint.tint(nsWall(0, 0.2, 0), true, boot);
        ExplorePaint.tint(nsWall(0, 2.0, 0), true, high);
        assertThat(boot[0]).isLessThan(high[0]);
        assertThat(ExplorePaint.CONTACT_BOOT_FRAC).isEqualTo(0.28);
        assertThat(ExplorePaint.CONTACT_BOOT_MIN).isEqualTo(0.55f);
        assertThat(ExplorePaint.wallContactShade(0))
                .isEqualTo(ExplorePaint.CONTACT_BOOT_MIN);
        assertThat(ExplorePaint.wallContactShade(ExploreMesh.WALL_HEIGHT * 0.5))
                .isEqualTo(1f);
        assertThat(ExplorePaint.wallContactShade(ExploreMesh.WALL_HEIGHT))
                .isEqualTo(ExplorePaint.CONTACT_CROWN_MIN);
        assertThat(ExplorePaint.wallContactShade(ExploreMesh.WALL_HEIGHT * 0.1))
                .isLessThan(ExplorePaint.wallContactShade(ExploreMesh.WALL_HEIGHT * 0.25));
        assertThat(ExplorePaint.wallContactShade(ExploreMesh.WALL_HEIGHT * 0.95))
                .isLessThan(ExplorePaint.wallContactShade(ExploreMesh.WALL_HEIGHT * 0.7));
    }

    @Test
    void crownDarkensTheLid() {
        float[] mid = new float[3];
        float[] crown = new float[3];
        ExplorePaint.tint(nsWall(0, ExploreMesh.WALL_HEIGHT * 0.5, 0), true, mid);
        ExplorePaint.tint(nsWall(0, ExploreMesh.WALL_HEIGHT * 0.95, 0), true, crown);
        assertThat(crown[0]).isLessThan(mid[0]);
        assertThat(ExplorePaint.CONTACT_CROWN_FRAC).isEqualTo(ExplorePaint.CONTACT_BOOT_FRAC);
        assertThat(ExplorePaint.CONTACT_CROWN_MIN).isEqualTo(ExplorePaint.CONTACT_BOOT_MIN);
    }

    @Test
    void ceilingCrownDarkensTowardTheRim() {
        assertThat(ExplorePaint.CEILING_CONTACT_DIM).isEqualTo(ExplorePaint.FLOOR_CONTACT_DIM);
        assertThat(ExplorePaint.CEILING_CONTACT_START).isEqualTo(ExplorePaint.FLOOR_CONTACT_START);
        ExploreMesh.Triangle center = new ExploreMesh.Triangle(
                -0.2, ExploreMesh.WALL_HEIGHT, -0.2,
                0.2, ExploreMesh.WALL_HEIGHT, -0.2,
                0.2, ExploreMesh.WALL_HEIGHT, 0.2,
                ExploreMesh.Face.CEILING, 1, 1);
        ExploreMesh.Triangle rim = new ExploreMesh.Triangle(
                0.7, ExploreMesh.WALL_HEIGHT, -0.2,
                0.95, ExploreMesh.WALL_HEIGHT, -0.2,
                0.95, ExploreMesh.WALL_HEIGHT, 0.2,
                ExploreMesh.Face.CEILING, 1, 1);
        assertThat(ExplorePaint.ceilingContactShade(center)).isEqualTo(1f);
        assertThat(ExplorePaint.ceilingContactShade(rim))
                .isLessThan(ExplorePaint.ceilingContactShade(center));
        float[] mid = new float[3];
        float[] edge = new float[3];
        ExplorePaint.tint(center, true, mid);
        ExplorePaint.tint(rim, true, edge);
        assertThat(edge[0]).isLessThan(mid[0]);
    }

    @Test
    void floorSkirtingDarkensTowardTheRim() {
        assertThat(ExplorePaint.FLOOR_CONTACT_DIM).isEqualTo(0.16f);
        assertThat(ExplorePaint.FLOOR_CONTACT_START).isEqualTo(0.55f);
        // Tile (1,1) center is world (0,0); a center triangle stays bright.
        ExploreMesh.Triangle center = new ExploreMesh.Triangle(
                -0.2, 0, -0.2, 0.2, 0, -0.2, 0.2, 0, 0.2,
                ExploreMesh.Face.FLOOR, 1, 1);
        // Same tile, centroid near the east rim.
        ExploreMesh.Triangle rim = new ExploreMesh.Triangle(
                0.7, 0, -0.2, 0.95, 0, -0.2, 0.95, 0, 0.2,
                ExploreMesh.Face.FLOOR, 1, 1);
        assertThat(ExplorePaint.floorContactShade(center)).isEqualTo(1f);
        assertThat(ExplorePaint.floorContactShade(rim))
                .isLessThan(ExplorePaint.floorContactShade(center));
        float[] mid = new float[3];
        float[] edge = new float[3];
        ExplorePaint.tint(center, true, mid);
        ExplorePaint.tint(rim, true, edge);
        assertThat(edge[0]).isLessThan(mid[0]);
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
        float[] early = new float[2];
        float[] late = new float[2];
        ExplorePaint.skyUv(0, 0, 0, 0.5f, early, 0);
        ExplorePaint.skyUv(0, 0, 0, 0.5f, late, 10);
        assertThat(late[0]).isGreaterThan(early[0]);
        assertThat(ExplorePaint.SKY_DRIFT).isGreaterThan(0f);
        assertThat(ExplorePaint.skyTwinkle(0.1)).isGreaterThan(0.85f);
        assertThat(ExplorePaint.skyTwinkle(0.1)).isNotEqualTo(ExplorePaint.skyTwinkle(0.4));
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
        assertThat(ExplorePaint.captionPlace(hall)).isEqualTo("HALL");
        assertThat(ExplorePaint.captionMeta(hall)).contains("N");
        assertThat(ExplorePaint.CAPTION_PLACE_CELL)
                .as("place glyphs lead the strip")
                .isGreaterThan(ExplorePaint.CAPTION_META_CELL);
        assertThat(ExplorePaint.AIM_BRIGHT_R).isGreaterThan(ExplorePaint.CAPTION_META_R);
        assertThat(ExplorePaint.captionWidth("AB", 0.02f, 0.008f))
                .isGreaterThan(ExplorePaint.captionAdvance(0.02f, 0.008f));
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
        assertThat(ExplorePaint.STATUS_GOLD_R).isEqualTo(0.72f);
        assertThat(ExplorePaint.STATUS_GOLD_G).isEqualTo(0.52f);
        assertThat(ExplorePaint.STATUS_GOLD_B).isEqualTo(0.22f);
        assertThat(ExplorePaint.STATUS_GOLD_H)
                .as("gold lip sits inside the under-brown band")
                .isLessThan(ExplorePaint.STATUS_GOLD_UNDER_H);
        assertThat(ExplorePaint.STATUS_BREATH_MS).isEqualTo(ExplorePaint.MAP_HERE_BREATH_MS);
        assertThat(ExplorePaint.statusGoldH(0.1))
                .isNotEqualTo(ExplorePaint.statusGoldH(0.8));
        assertThat(ExplorePaint.statusGoldUnderH(0.1))
                .isNotEqualTo(ExplorePaint.statusGoldUnderH(0.8));
        assertThat(ExplorePaint.VIGNETTE_INSET).isGreaterThan(0f);
        assertThat(ExplorePaint.VIGNETTE_ALPHA).isGreaterThan(0f);
        assertThat(ExplorePaint.VIGNETTE_BREATH_MS).isEqualTo(ExplorePaint.MAP_HERE_BREATH_MS);
        assertThat(ExplorePaint.vignetteAlpha(0.1))
                .isNotEqualTo(ExplorePaint.vignetteAlpha(0.8));
        assertThat(ExplorePaint.vignetteAlpha(0.1))
                .isGreaterThan(ExplorePaint.VIGNETTE_ALPHA * 0.85f);
        assertThat(ExplorePaint.AIM_SOFT_ARM)
                .as("soft underglow is wider than the bright arm")
                .isGreaterThan(ExplorePaint.AIM_ARM);
        assertThat(ExplorePaint.AIM_BREATH_MS).isEqualTo(ExplorePaint.MAP_HERE_BREATH_MS);
        assertThat(ExplorePaint.aimSoftArm(0.1))
                .isNotEqualTo(ExplorePaint.aimSoftArm(0.8));
        assertThat(ExplorePaint.aimSoftThick(0.1))
                .isNotEqualTo(ExplorePaint.aimSoftThick(0.8));
        assertThat(ExplorePaint.AIM_BRIGHT_R).isGreaterThan(ExplorePaint.AIM_SOFT_R);
        assertThat(ExplorePaint.CAPTION_SOFT_PAD).isGreaterThan(0f);
        assertThat(ExplorePaint.CAPTION_BREATH_MS).isEqualTo(ExplorePaint.MAP_HERE_BREATH_MS);
        assertThat(ExplorePaint.captionSoftPad(0.1))
                .isNotEqualTo(ExplorePaint.captionSoftPad(0.8));
        assertThat(ExplorePaint.AIM_BRIGHT_R).isGreaterThan(ExplorePaint.CAPTION_SOFT_R);
        assertThat(ExplorePaint.KEY_SOFT_PAD)
                .as("key soft pad is larger than the bright diamond")
                .isGreaterThan(1f);
        assertThat(ExplorePaint.KEY_BREATH_MS).isEqualTo(ExplorePaint.MAP_HERE_BREATH_MS);
        assertThat(ExplorePaint.keySoftPad(0.1))
                .isNotEqualTo(ExplorePaint.keySoftPad(0.8));
        assertThat(ExplorePaint.keySoftPad(0.1))
                .isGreaterThan(ExplorePaint.KEY_SOFT_PAD * 0.85f);
        assertThat(ExplorePaint.FACE_LIP).isGreaterThan(ExplorePaint.FACE_LIP_CORE);
        assertThat(ExplorePaint.FACE_BREATH_MS).isEqualTo(ExplorePaint.MAP_HERE_BREATH_MS);
        assertThat(ExplorePaint.faceLip(0.1))
                .isNotEqualTo(ExplorePaint.faceLip(0.8));
        assertThat(ExplorePaint.faceLipCore(0.1))
                .isNotEqualTo(ExplorePaint.faceLipCore(0.8));
        assertThat(ExplorePaint.KEY_SOFT_R).isEqualTo(ExplorePaint.CAPTION_SOFT_R);
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
        float idle = Math.abs(ExplorePaint.handBob(0.4));
        float walk = Math.abs(ExplorePaint.handBob(0.4, 1));
        assertThat(walk).isGreaterThan(idle);
        float[] calm = new float[3];
        float[] hot = new float[3];
        ExplorePaint.handTint(ExplorePaint.HandPart.FLAME, 0, calm);
        ExplorePaint.handTint(ExplorePaint.HandPart.FLAME, 2, hot);
        assertThat(hot[1]).isLessThan(calm[1]);
        assertThat(hot[2]).isLessThan(calm[2]);
        float bright = ExplorePaint.flameFlicker(0.1);
        float dim = ExplorePaint.flameFlicker(0.2);
        assertThat(bright).isGreaterThan(0.7f);
        assertThat(dim).isLessThan(1.15f);
        float[] flickA = new float[3];
        float[] flickB = new float[3];
        ExplorePaint.handTint(ExplorePaint.HandPart.FLAME, 0, flickA, 0.05);
        ExplorePaint.handTint(ExplorePaint.HandPart.FLAME, 0, flickB, 0.18);
        assertThat(flickA[0]).isNotEqualTo(flickB[0]);
        float[] gripA = new float[3];
        float[] gripB = new float[3];
        ExplorePaint.handTint(ExplorePaint.HandPart.GRIP, 0, gripA, 0.05);
        ExplorePaint.handTint(ExplorePaint.HandPart.GRIP, 0, gripB, 0.18);
        assertThat(gripA[0]).isNotEqualTo(gripB[0]);
        assertThat(ExplorePaint.GRIP_CATCH).isGreaterThan(ExplorePaint.SHAFT_CATCH);
        float[] shaft = new float[3];
        ExplorePaint.handTint(ExplorePaint.HandPart.SHAFT, 0, shaft, 0.05);
        assertThat(gripA[0]).isGreaterThan(shaft[0]);
        ExplorePaint.handTint(null, 0, calm);
        ExplorePaint.handTint(ExplorePaint.HandPart.GRIP, 0, null);
    }

    @Test
    void torchDustLoftsInTheBeam() {
        assertThat(ExplorePaint.DUST_COUNT).isEqualTo(8);
        assertThat(ExplorePaint.DUST_HALF).isEqualTo(0.006f);
        List<ExplorePaint.DustMote> a = ExplorePaint.dustMotes(1.6, 0, 0);
        List<ExplorePaint.DustMote> b = ExplorePaint.dustMotes(1.6, 0, 2);
        assertThat(a).hasSize(ExplorePaint.DUST_COUNT);
        float strip = -1f + ExplorePaint.STATUS_H;
        float meanY = 0;
        for (ExplorePaint.DustMote mote : a) {
            assertThat(mote.y()).isGreaterThan(strip);
            assertThat(mote.a()).isBetween(0.08f, 0.45f);
            meanY += mote.y();
        }
        meanY /= a.size();
        float oy = -1f + ExplorePaint.STATUS_H + 0.06f;
        assertThat(meanY).isGreaterThan(oy + 0.22f);
        assertThat(meanY).isLessThan(oy + 0.55f);
        assertThat(a.get(0).x()).isNotEqualTo(b.get(0).x());
        assertThat(a.get(3).a()).isNotEqualTo(ExplorePaint.dustMotes(1.6, 0, 0.18).get(3).a());
    }

    @Test
    void torchBloomWashesBehindTheFlame() {
        ExplorePaint.TorchBloom bloom = ExplorePaint.torchBloom(1.6, 0, 0.1);
        float strip = -1f + ExplorePaint.STATUS_H;
        assertThat(bloom.y() - bloom.ry()).isGreaterThan(strip);
        assertThat(bloom.rx()).isEqualTo(ExplorePaint.BLOOM_RX);
        assertThat(bloom.ry()).isEqualTo(ExplorePaint.BLOOM_RY);
        assertThat(bloom.a()).isBetween(0.06f, 0.28f);
        ExplorePaint.TorchBloom dim = ExplorePaint.torchBloom(1.6, 0, 0.2);
        assertThat(bloom.a()).isNotEqualTo(dim.a());
        ExplorePaint.TorchBloom bobbed = ExplorePaint.torchBloom(1.6, 0.02f, 0.1);
        assertThat(bobbed.y()).isGreaterThan(bloom.y());
        assertThat(ExplorePaint.BLOOM_R).isGreaterThan(ExplorePaint.BLOOM_G);
        assertThat(ExplorePaint.BLOOM_G).isGreaterThan(ExplorePaint.BLOOM_B);
        List<ExplorePaint.TorchBloom> wash = ExplorePaint.torchBloomWash(1.6, 0, 0.1);
        assertThat(wash).hasSize(ExplorePaint.BLOOM_RINGS);
        assertThat(wash.get(0).rx()).isGreaterThan(wash.get(2).rx());
        assertThat(wash.get(0).a()).isLessThan(wash.get(2).a());
        assertThat(wash.get(0).y() - wash.get(0).ry()).isGreaterThan(strip - 0.02f);
        assertThat(wash.get(0).a()).isNotEqualTo(ExplorePaint.torchBloomWash(1.6, 0, 0.2).get(0).a());
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

    private static ExploreMesh.Triangle endFloor(TileType tile) {
        return new ExploreMesh.Triangle(0, 0, 0, 1, 0, 0, 1, 0, 1,
                ExploreMesh.Face.FLOOR, 3, 3, tile);
    }

    private static ExploreMesh.Triangle ceilingAt(double z) {
        return new ExploreMesh.Triangle(0, 2.8, z, 1, 2.8, z, 1, 2.8, z + 1,
                ExploreMesh.Face.CEILING, 3, 3);
    }
}
