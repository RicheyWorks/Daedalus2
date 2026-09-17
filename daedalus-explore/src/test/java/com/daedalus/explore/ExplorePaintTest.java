// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import com.daedalus.model.TileType;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Parcel;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.World;
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
        float[] mid = new float[3];
        float[] rim = new float[3];
        ExplorePaint.tint(nsWall(0, 1.4, 0), true, mid,
                Double.NaN, Double.NaN, 0, 0, 0);
        ExplorePaint.tint(nsWall(0, 1.4, 0), true, rim,
                Double.NaN, Double.NaN, 0, 0, 1);
        assertThat(rim[0] + rim[1] + rim[2])
                .as("corridor wall falls off toward unseen at the board rim")
                .isLessThan(mid[0] + mid[1] + mid[2]);
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
        float[] mid = new float[3];
        float[] rim = new float[3];
        ExplorePaint.tint(face(ExploreMesh.Face.FLOOR, 0, 3, 3), true, mid,
                Double.NaN, Double.NaN, 0, 0, 0);
        ExplorePaint.tint(face(ExploreMesh.Face.FLOOR, 0, 3, 3), true, rim,
                Double.NaN, Double.NaN, 0, 0, 1);
        assertThat(rim[0] + rim[1] + rim[2])
                .as("corridor floor falls off toward floor-dim at the board rim")
                .isLessThan(mid[0] + mid[1] + mid[2]);
        float[] lidMid = new float[3];
        float[] lidRim = new float[3];
        ExplorePaint.tint(face(ExploreMesh.Face.CEILING, 2.8, 3, 3), true, lidMid,
                Double.NaN, Double.NaN, 0, 0, 0);
        ExplorePaint.tint(face(ExploreMesh.Face.CEILING, 2.8, 3, 3), true, lidRim,
                Double.NaN, Double.NaN, 0, 0, 1);
        assertThat(lidRim[0] + lidRim[1] + lidRim[2])
                .as("corridor lid falls off toward floor-dim at the board rim")
                .isLessThan(lidMid[0] + lidMid[1] + lidMid[2]);
    }

    @Test
    void occupiedCubesWearTorchMaterialsNotIce() {
        float[] stone = new float[3];
        float[] dirt = new float[3];
        float[] wood = new float[3];
        float[] glass = new float[3];
        float[] lid = new float[3];
        float[] boot = new float[3];
        ExplorePaint.blockTint(BlockType.STONE, WorldMesh.Face.POS_Z, stone);
        ExplorePaint.blockTint(BlockType.DIRT, WorldMesh.Face.POS_Z, dirt);
        ExplorePaint.blockTint(BlockType.WOOD, WorldMesh.Face.POS_Z, wood);
        ExplorePaint.blockTint(BlockType.GLASS, WorldMesh.Face.POS_Z, glass);
        ExplorePaint.blockTint(BlockType.STONE, WorldMesh.Face.POS_Y, lid);
        ExplorePaint.blockTint(BlockType.STONE, WorldMesh.Face.NEG_Y, boot);
        assertThat(wood[0]).as("wood is warmer than stone").isGreaterThan(stone[0]);
        assertThat(dirt[0]).isGreaterThan(stone[0]);
        assertThat(glass[1]).as("glass stays lamp-green, not leftover well ice")
                .isGreaterThan(glass[2]);
        assertThat(glass[2]).isLessThan(0.72f);
        assertThat(lid[0]).as("top face reads the lamp").isGreaterThan(boot[0]);
        float[] near = new float[3];
        float[] far = new float[3];
        WorldMesh.Triangle woodFace = new WorldMesh.Triangle(
                0, 0, 1, 1, 0, 1, 1, 1, 1,
                WorldMesh.Face.POS_Z, BlockType.WOOD, new BlockCoordinate(0, 0, 1));
        ExplorePaint.blockTint(woodFace, near, 0.5, 0.2, Math.PI, 0);
        ExplorePaint.blockTint(woodFace, far, 0.5, 20, Math.PI, 0);
        float[] midBoard = new float[3];
        float[] rimBoard = new float[3];
        ExplorePaint.blockTint(woodFace, midBoard, Double.NaN, Double.NaN, 0, 0, 0);
        ExplorePaint.blockTint(woodFace, rimBoard, Double.NaN, Double.NaN, 0, 0, 1);
        assertThat(rimBoard[0] + rimBoard[1] + rimBoard[2])
                .as("cube face falls off toward floor-dim at the board rim")
                .isLessThan(midBoard[0] + midBoard[1] + midBoard[2]);
        assertThat(near[0]).as("near cube keeps wood under the lamp").isGreaterThan(far[0]);
        assertThat(near[0]).isGreaterThan(near[2]);
        BlockCoordinate at = new BlockCoordinate(0, 0, 1);
        WorldMesh.Triangle bootFace = new WorldMesh.Triangle(
                0, 0, 1, 1, 0, 1, 1, WorldMesh.BOOT_FRAC, 1,
                WorldMesh.Face.POS_Z, BlockType.WOOD, at);
        WorldMesh.Triangle shaftFace = new WorldMesh.Triangle(
                0, WorldMesh.BOOT_FRAC, 1, 1, WorldMesh.BOOT_FRAC, 1,
                1, 1.0 - WorldMesh.CROWN_FRAC, 1,
                WorldMesh.Face.POS_Z, BlockType.WOOD, at);
        WorldMesh.Triangle crownFace = new WorldMesh.Triangle(
                0, 1.0 - WorldMesh.CROWN_FRAC, 1, 1, 1.0 - WorldMesh.CROWN_FRAC, 1,
                1, 1, 1,
                WorldMesh.Face.POS_Z, BlockType.WOOD, at);
        float[] bootInk = new float[3];
        float[] shaftInk = new float[3];
        float[] crownInk = new float[3];
        ExplorePaint.blockTint(bootFace, bootInk, Double.NaN, Double.NaN, 0, 0);
        ExplorePaint.blockTint(shaftFace, shaftInk, Double.NaN, Double.NaN, 0, 0);
        ExplorePaint.blockTint(crownFace, crownInk, Double.NaN, Double.NaN, 0, 0);
        assertThat(bootInk[0]).as("cube boot is darker skirting, not leftover even wood")
                .isLessThan(shaftInk[0]);
        assertThat(crownInk[0]).as("cube crown is darker lid contact, not leftover even wood")
                .isLessThan(shaftInk[0]);
        assertThat(ExplorePaint.blockContactShade(bootFace))
                .isLessThan(ExplorePaint.blockContactShade(shaftFace));
        assertThat(ExplorePaint.blockContactShade(crownFace))
                .isLessThan(ExplorePaint.blockContactShade(shaftFace));
        assertThat(ExplorePaint.blockContactShade(null)).isEqualTo(1f);
        BlockCoordinate lidAt = new BlockCoordinate(0, 0, 0);
        WorldMesh.Triangle lidMid = new WorldMesh.Triangle(
                0.28, 1, 0.28, 0.72, 1, 0.28, 0.72, 1, 0.72,
                WorldMesh.Face.POS_Y, BlockType.WOOD, lidAt);
        WorldMesh.Triangle lidRim = new WorldMesh.Triangle(
                0, 1, 0, 1, 1, 0, 1, 1, 0.28,
                WorldMesh.Face.POS_Y, BlockType.WOOD, lidAt);
        assertThat(ExplorePaint.blockLidContactShade(lidRim))
                .as("cube lid rim is darker contact, not leftover even wood")
                .isLessThan(ExplorePaint.blockLidContactShade(lidMid));
        assertThat(ExplorePaint.blockContactShade(lidRim))
                .isLessThan(ExplorePaint.blockContactShade(lidMid));
        WorldMesh.Triangle bootMid = new WorldMesh.Triangle(
                0.28, 0, 0.28, 0.72, 0, 0.28, 0.72, 0, 0.72,
                WorldMesh.Face.NEG_Y, BlockType.WOOD, lidAt);
        WorldMesh.Triangle bootRim = new WorldMesh.Triangle(
                0, 0, 0, 1, 0, 0, 1, 0, 0.28,
                WorldMesh.Face.NEG_Y, BlockType.WOOD, lidAt);
        assertThat(ExplorePaint.blockLidContactShade(bootRim))
                .as("cube boot rim is darker contact, not leftover even wood")
                .isLessThan(ExplorePaint.blockLidContactShade(bootMid));
    }

    @Test
    void occupiedCubesSitOnATorchFloorPad() {
        assertThat(ExplorePaint.BLOCK_PAD_R)
                .as("pad spills past a 1x1 cube onto the corridor")
                .isGreaterThan(0.5f);
        assertThat(ExplorePaint.blockPlaces(null)).isEmpty();
        World volume = World.zero();
        volume.place(new BlockCoordinate(4, 0, 2), BlockType.WOOD);
        volume.place(new BlockCoordinate(8, 0, 8), BlockType.STONE);
        volume.place(new BlockCoordinate(8, 1, 8), BlockType.GLASS);
        List<ExplorePaint.BlockPlace> pads = ExplorePaint.blockPlaces(WorldMesh.of(volume));
        assertThat(pads).hasSize(2);
        assertThat(pads.stream().map(ExplorePaint.BlockPlace::type))
                .containsExactlyInAnyOrder(BlockType.WOOD, BlockType.STONE);
        ExplorePaint.BlockPlace wood = pads.stream()
                .filter(p -> p.type() == BlockType.WOOD).findFirst().orElseThrow();
        assertThat(wood.x()).isEqualTo(4.5);
        assertThat(wood.z()).isEqualTo(2.5);
        assertThat(wood.tileRow()).isEqualTo(3);
        assertThat(wood.tileCol()).isEqualTo(5);
        float[] woodInk = new float[3];
        float[] stoneInk = new float[3];
        float[] gold = new float[3];
        ExplorePaint.blockPlaceTint(BlockType.WOOD, woodInk);
        ExplorePaint.blockPlaceTint(BlockType.STONE, stoneInk);
        ExplorePaint.blockPlaceTint(null, stoneInk);
        ExplorePaint.captionPlaceTint("HALL", gold);
        assertThat(woodInk[0]).as("WOOD pad wears torch wood, not leftover gold")
                .isGreaterThan(gold[2]);
        assertThat(woodInk[2]).isLessThan(woodInk[0]);
        float[] woodPad = new float[3];
        float[] woodRim = new float[3];
        ExplorePaint.placePadTint(woodInk, woodPad, 0, 0);
        ExplorePaint.placePadTint(woodInk, woodRim, 0, 1);
        assertThat(woodRim[0] + woodRim[1] + woodRim[2])
                .as("cube pad falls off toward floor-dim at the board rim")
                .isLessThan(woodPad[0] + woodPad[1] + woodPad[2]);
        ExplorePaint.blockPlaceTint(BlockType.WOOD, null);
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
        float[] litGate = new float[3];
        float[] litHall = new float[3];
        ExplorePaint.tint(endFloor(TileType.START), true, litGate, 0.67, 2.0, 0);
        ExplorePaint.tint(face(ExploreMesh.Face.FLOOR, 0, 3, 3), true, litHall, 0.67, 2.0, 0);
        assertThat(litGate[1]).as("start floor stays mint under the lamp, not leftover torch brown")
                .isGreaterThan(litHall[1]);
        assertThat(litGate[1]).isGreaterThan(litGate[0]);
    }

    @Test
    void startAndGoalCeilingsNameTheEnds() {
        float[] passage = new float[3];
        float[] gate = new float[3];
        float[] exit = new float[3];
        ExplorePaint.tint(face(ExploreMesh.Face.CEILING, 2.8, 3, 3), true, passage);
        ExplorePaint.tint(endCeiling(TileType.START), true, gate);
        ExplorePaint.tint(endCeiling(TileType.GOAL), true, exit);
        assertThat(ExplorePaint.CEILING_END_WEIGHT).isEqualTo(ExplorePaint.FLOOR_END_WEIGHT);
        assertThat(gate[1]).as("start lid lifts toward well mint").isGreaterThan(passage[1]);
        assertThat(exit[0]).as("goal lid lifts toward well coral").isGreaterThan(passage[0]);
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
        int[] midFloor = ExplorePaint.windowIconFloorRgb(3, 5);
        assertThat(icon[mid] & 0xFF)
                .as("idle maze floors sit at the icon center")
                .isEqualTo(midFloor[0]);
        assertThat(icon[mid + 1] & 0xFF).isEqualTo(midFloor[1]);
        assertThat(icon[mid + 2] & 0xFF).isEqualTo(midFloor[2]);
        int rimFloor = (11 * ExplorePaint.WINDOW_ICON_SIZE + 23) * 4;
        assertThat(icon[rimFloor] & 0xFF)
                .as("idle icon rim slate falls off like the live well")
                .isEqualTo(ExplorePaint.windowIconFloorRgb(1, 9)[0])
                .isNotEqualTo(icon[mid] & 0xFF);
        int start = (11 * ExplorePaint.WINDOW_ICON_SIZE + 7) * 4;
        assertThat(icon[start] & 0xFF)
                .as("start mint sits on the idle gate cell")
                .isEqualTo(ExplorePaint.WINDOW_ICON_START_R);
        int goal = (19 * ExplorePaint.WINDOW_ICON_SIZE + 23) * 4;
        assertThat(icon[goal] & 0xFF)
                .as("exit coral sits on the idle goal cell")
                .isEqualTo(ExplorePaint.WINDOW_ICON_GOAL_R);
        int rim = (9 * ExplorePaint.WINDOW_ICON_SIZE + 5) * 4;
        int midWall = (13 * ExplorePaint.WINDOW_ICON_SIZE + 13) * 4;
        assertThat(icon[rim] & 0xFF)
                .as("idle icon rim posts fall off toward unseen")
                .isEqualTo(ExplorePaint.windowIconWallRgb(0, 0)[0])
                .isNotEqualTo(icon[midWall] & 0xFF);
        assertThat(icon[midWall] & 0xFF)
                .isEqualTo(ExplorePaint.windowIconWallRgb(2, 4)[0]);
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
        float[] rim = new float[3];
        ExplorePaint.placePadTint(rgb, rim, 0, 1);
        assertThat(rim[0] + rim[1] + rim[2])
                .as("story pad falls off toward floor-dim at the board rim")
                .isLessThan(pad[0] + pad[1] + pad[2]);
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
        assertThat(mesh.stream().anyMatch(ExplorePaint.PillarTri::crown)).isTrue();
        assertThat(mesh.stream().anyMatch(t -> !t.boot() && !t.crown())).isTrue();
        assertThat(ExplorePaint.PILLAR_BOOT_FRAC).isEqualTo((float) ExplorePaint.CONTACT_BOOT_FRAC);
        assertThat(ExplorePaint.PILLAR_CROWN_FRAC).isEqualTo(ExplorePaint.PILLAR_BOOT_FRAC);
        float[] boot = new float[3];
        float[] shaft = new float[3];
        float[] crown = new float[3];
        ExplorePaint.pillarTint(rgb, true, boot);
        ExplorePaint.pillarTint(rgb, false, shaft);
        ExplorePaint.pillarTint(rgb, false, true, crown);
        assertThat(boot[0]).isLessThan(shaft[0]);
        assertThat(crown[0]).as("pillar crown is darker lid contact, not leftover even wood")
                .isLessThan(shaft[0]);
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
        int ceilMid = Byte.toUnsignedInt(ceil[(3 * ExplorePaint.TEX + 3) * 4]);
        assertThat(ceilMid).isGreaterThanOrEqualTo(ExplorePaint.CEILING_TEX_R);
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
        assertThat(ExplorePaint.FLOOR_TEX_EDGE_DIM).isEqualTo(0.22f);
        assertThat(ExplorePaint.floorTexShade(0, 3))
                .as("floor tile rim falls off like live halls")
                .isLessThan(ExplorePaint.floorTexShade(3, 3));
        assertThat(ExplorePaint.CEILING_TEX_EDGE_DIM).isEqualTo(0.22f);
        assertThat(ExplorePaint.ceilingTexShade(0, 3))
                .as("ceiling tile rim falls off like floor tiles")
                .isLessThan(ExplorePaint.ceilingTexShade(3, 3));
        assertThat(ExplorePaint.BRICK_TEX_EDGE_DIM).isEqualTo(0.22f);
        assertThat(ExplorePaint.brickTexShade(1, 3))
                .as("brick face rim falls off toward grout")
                .isLessThan(ExplorePaint.brickTexShade(8, 4));
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
        assertThat(dots.stream()
                .filter(d -> d.kind() == ExplorePaint.MapKind.HERE)
                .mapToDouble(ExplorePaint.MapDot::edge)
                .findFirst().orElse(-1))
                .as("HERE carries pocket-rim falloff")
                .isBetween(0.0, 1.0);
        assertThat(dots.stream().anyMatch(d -> d.kind() == ExplorePaint.MapKind.WALL)).isTrue();
        assertThat(dots.stream()
                .filter(d -> d.kind() == ExplorePaint.MapKind.WALL)
                .mapToDouble(ExplorePaint.MapDot::edge)
                .max().orElse(0))
                .as("earned walls carry pocket-rim falloff")
                .isGreaterThan(0);
        assertThat(dots.stream().anyMatch(d -> d.kind() == ExplorePaint.MapKind.MARK)).isTrue();
        assertThat(dots.stream()
                .filter(d -> d.kind() == ExplorePaint.MapKind.MARK)
                .mapToDouble(ExplorePaint.MapDot::edge)
                .findFirst().orElse(-1))
                .as("story marks carry pocket-rim falloff")
                .isBetween(0.0, 1.0);
        assertThat(ExplorePaint.MAP_MARK_EDGE_DIM).isEqualTo(0.22f);
        float[] markMid = new float[3];
        float[] markRim = new float[3];
        ExplorePaint.mapMarkTint("ENTRANCE", markMid);
        ExplorePaint.mapMarkTint("ENTRANCE", markRim, 1);
        assertThat(markRim[0]).as("story-mark rim falls off like live halls")
                .isLessThan(markMid[0]);
        assertThat(dots.stream().anyMatch(d -> d.kind() == ExplorePaint.MapKind.START))
                .as("earned map names the revealed start mint")
                .isTrue();
        assertThat(dots.stream().anyMatch(d -> d.kind() == ExplorePaint.MapKind.GOAL))
                .as("earned map names the revealed goal coral")
                .isTrue();
        float[] gate = new float[3];
        ExplorePaint.mapEndTint(ExplorePaint.MapKind.START, gate);
        assertThat(gate[1]).isGreaterThan(gate[0]);
        assertThat(ExplorePaint.MAP_END_EDGE_DIM).isEqualTo(0.22f);
        float[] gateRim = new float[3];
        ExplorePaint.mapEndTint(ExplorePaint.MapKind.START, gateRim, 1);
        assertThat(gateRim[1]).as("start gate rim falls off like live halls")
                .isLessThan(gate[1]);
        assertThat(dots.stream()
                .filter(d -> d.kind() == ExplorePaint.MapKind.START
                        || d.kind() == ExplorePaint.MapKind.GOAL)
                .mapToDouble(ExplorePaint.MapDot::edge)
                .allMatch(e -> e >= 0 && e <= 1))
                .as("earned gates carry pocket-rim falloff")
                .isTrue();
        World volume = World.zero();
        volume.place(new BlockCoordinate(2, 0, 0), BlockType.WOOD);
        List<ExplorePaint.MapDot> withBlocks = ExplorePaint.automap(fog, mesh,
                ExploreBody.atCell(new Point(0, 0)), null, WorldMesh.of(volume));
        assertThat(withBlocks.stream().anyMatch(d -> d.kind() == ExplorePaint.MapKind.BLOCK))
                .as("earned map names an occupied cube")
                .isTrue();
        float[] cube = new float[3];
        ExplorePaint.mapStoneTint(ExplorePaint.MapKind.BLOCK, 0, cube);
        assertThat(cube[0]).as("block ink is torch wood, not leftover ice")
                .isGreaterThan(ExplorePaint.MAP_FLOOR_R);
        assertThat(cube[2]).isLessThan(cube[0]);
        assertThat(ExplorePaint.MAP_BLOCK_HALO)
                .as("earned cubes wear a soft pad like story marks")
                .isEqualTo(ExplorePaint.MAP_MARK_HALO);
        float[] cubeSoft = new float[3];
        ExplorePaint.mapBlockSoftTint(cubeSoft);
        assertThat(cubeSoft[0]).isLessThan(cube[0]);
        float[] cubeSoftRim = new float[3];
        ExplorePaint.mapBlockSoftTint(1, cubeSoftRim);
        assertThat(cubeSoftRim[0]).as("rim cube pads fall off like the wood")
                .isLessThan(cubeSoft[0]);
        assertThat(ExplorePaint.mapBlockHalo(0.1))
                .isNotEqualTo(ExplorePaint.mapBlockHalo(0.8));
        ExplorePaint.mapBlockSoftTint(null);
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
        assertThat(ExplorePaint.endPlaces(null, mesh)).isEmpty();
        assertThat(ExplorePaint.endPlaces(new ExploreFog(), mesh)).isEmpty();
        List<ExplorePaint.EndPlace> pads = ExplorePaint.endPlaces(fog, mesh);
        assertThat(pads).hasSize(2);
        assertThat(pads.stream().map(ExplorePaint.EndPlace::kind))
                .containsExactlyInAnyOrder(ExplorePaint.MapKind.START, ExplorePaint.MapKind.GOAL);
        ExplorePaint.EndPlace gatePad = pads.stream()
                .filter(p -> p.kind() == ExplorePaint.MapKind.START).findFirst().orElseThrow();
        assertThat(gatePad.x()).isEqualTo(ExploreMesh.tileCenterX(1));
        assertThat(gatePad.z()).isEqualTo(ExploreMesh.tileCenterZ(1));
        assertThat(gatePad.tileRow()).isEqualTo(1);
        assertThat(gatePad.tileCol()).isEqualTo(1);
        float[] endPad = new float[3];
        float[] endRim = new float[3];
        ExplorePaint.placePadTint(gate, endPad, 0, 0);
        ExplorePaint.placePadTint(gate, endRim, 0, 1);
        assertThat(endRim[1])
                .as("start pad falls off toward floor-dim at the board rim")
                .isLessThan(endPad[1]);
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
        float[] hereHall = new float[3];
        float[] hereStart = new float[3];
        float[] hereGoal = new float[3];
        ExplorePaint.mapHereTint(ExploreBody.atCell(new Point(0, 0)), null, hereHall);
        ExplorePaint.mapHereTint(ExploreBody.atCell(new Point(0, 0)), mesh, hereStart);
        ExplorePaint.mapHereTint(ExploreBody.atCell(new Point(0, 1)), mesh, hereGoal);
        assertThat(hereHall[0]).isEqualTo(ExplorePaint.MAP_HERE_R);
        assertThat(ExplorePaint.MAP_HERE_EDGE_DIM).isEqualTo(0.22f);
        float[] hereRim = new float[3];
        ExplorePaint.mapHereTint(ExploreBody.atCell(new Point(0, 0)), null, null, hereRim, 1);
        assertThat(hereRim[0]).as("HERE rim falls off like live halls")
                .isLessThan(hereHall[0]);
        assertThat(hereStart[1]).as("HERE on start lifts toward well mint")
                .isGreaterThan(hereHall[1]);
        assertThat(hereGoal[0]).as("HERE on goal lifts toward well coral")
                .isGreaterThan(hereHall[0]);
        World street = World.zero();
        street.applyStamp(new ParcelBounds(8, 0, 8, 9, 1, 9), Parcel.SYSTEM_OWNER,
                List.of(new BlockCoordinate(8, 0, 8)), List.of(BlockType.WOOD));
        street.nameParcel(street.parcels().get(0).id(), "Willow Walk");
        float[] hereStreet = new float[3];
        ExplorePaint.mapHereTint(new ExploreBody(8.4, 8.4, 0, 0), mesh,
                WorldMesh.of(street), hereStreet);
        assertThat(hereStreet[0]).as("HERE on a named street lifts toward torch wood")
                .isGreaterThan(hereHall[2]);
        assertThat(hereStreet[2]).isLessThan(hereStreet[0]);
        ExplorePaint.mapHereTint(null, mesh, null);
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
        assertThat(ExplorePaint.HUD_VOID_RIM_R).isEqualTo(ExplorePaint.MAP_POCKET_R);
        assertThat(ExplorePaint.HUD_VOID_RIM_G).isEqualTo(ExplorePaint.MAP_POCKET_G);
        assertThat(ExplorePaint.HUD_VOID_RIM_B).isEqualTo(ExplorePaint.MAP_POCKET_B);
        float[] hudMid = new float[3];
        float[] hudRim = new float[3];
        ExplorePaint.hudVoidTint(0, hudMid);
        ExplorePaint.hudVoidTint(1, hudRim);
        assertThat(hudMid[0]).isEqualTo(ExplorePaint.HUD_VOID_R);
        assertThat(hudRim[0]).isEqualTo(ExplorePaint.HUD_VOID_RIM_R);
        assertThat(hudRim[0]).isLessThan(hudMid[0]);
        ExplorePaint.hudVoidTint(1, null);
        assertThat(ExplorePaint.MAP_POCKET_R).isLessThan(ExplorePaint.HUD_VOID_R);
        assertThat(ExplorePaint.MAP_POCKET_G).isLessThan(ExplorePaint.HUD_VOID_G);
        assertThat(ExplorePaint.MAP_POCKET_B).isLessThan(ExplorePaint.HUD_VOID_B);
        assertThat(ExplorePaint.MAP_POCKET_R).isGreaterThan(ExplorePaint.MAP_POCKET_B);
        float[] pocketMid = new float[3];
        float[] pocketRim = new float[3];
        ExplorePaint.mapPocketTint(0, pocketMid);
        ExplorePaint.mapPocketTint(1, pocketRim);
        assertThat(pocketMid[0]).isEqualTo(ExplorePaint.MAP_POCKET_R);
        assertThat(pocketMid[1]).isEqualTo(ExplorePaint.MAP_POCKET_G);
        assertThat(pocketMid[2]).isEqualTo(ExplorePaint.MAP_POCKET_B);
        assertThat(pocketRim[0]).isEqualTo(ExplorePaint.MAP_POCKET_RIM_R);
        assertThat(pocketRim[1]).isEqualTo(ExplorePaint.MAP_POCKET_RIM_G);
        assertThat(pocketRim[2]).isEqualTo(ExplorePaint.MAP_POCKET_RIM_B);
        assertThat(pocketRim[0]).isLessThan(pocketMid[0]);
        ExplorePaint.mapPocketTint(1, null);
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
        assertThat(ExplorePaint.MAP_WALL_EDGE_DIM).isEqualTo(0.28f);
        assertThat(ExplorePaint.mapEdge(0, 0, 0, 6, 0, 10))
                .as("a rim cell is farther from the pocket center than a mid post")
                .isGreaterThan(ExplorePaint.mapEdge(3, 5, 0, 6, 0, 10));
        float[] rim = new float[3];
        float[] mid = new float[3];
        ExplorePaint.mapStoneTint(ExplorePaint.MapKind.WALL, 0,
                ExplorePaint.mapEdge(0, 0, 0, 6, 0, 10), rim);
        ExplorePaint.mapStoneTint(ExplorePaint.MapKind.WALL, 0,
                ExplorePaint.mapEdge(3, 5, 0, 6, 0, 10), mid);
        assertThat(rim[0]).as("automap rim posts fall off toward unseen")
                .isLessThan(mid[0]);
        assertThat(ExplorePaint.MAP_FLOOR_EDGE_DIM).isEqualTo(0.22f);
        float[] rimHall = new float[3];
        float[] midHall = new float[3];
        ExplorePaint.mapStoneTint(ExplorePaint.MapKind.FLOOR, 0,
                ExplorePaint.mapEdge(0, 0, 0, 6, 0, 10), rimHall);
        ExplorePaint.mapStoneTint(ExplorePaint.MapKind.FLOOR, 0,
                ExplorePaint.mapEdge(3, 5, 0, 6, 0, 10), midHall);
        assertThat(rimHall[0]).as("automap rim slate falls off like the live well")
                .isLessThan(midHall[0]);
        assertThat(ExplorePaint.MAP_BLOCK_EDGE_DIM).isEqualTo(ExplorePaint.MAP_FLOOR_EDGE_DIM);
        float[] rimCube = new float[3];
        float[] midCube = new float[3];
        ExplorePaint.mapStoneTint(ExplorePaint.MapKind.BLOCK, 0, 1, rimCube);
        ExplorePaint.mapStoneTint(ExplorePaint.MapKind.BLOCK, 0, 0, midCube);
        assertThat(rimCube[0]).as("automap rim wood falls off like the halls")
                .isLessThan(midCube[0]);
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
        assertThat(ExplorePaint.SKY_TEX_EDGE_DIM).isEqualTo(0.22f);
        assertThat(ExplorePaint.skyTexShade(0, 28))
                .as("sky rim falls off like the well void pocket")
                .isLessThan(ExplorePaint.skyTexShade(32, 28));
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
        MazeGrid grid = new MazeGrid(1, 2);
        grid.carve(grid.cell(0, 0), Direction.EAST);
        ExploreMesh mesh = ExploreMesh.of(grid);
        assertThat(ExplorePaint.endPlaceName(body, mesh)).isEqualTo("START");
        assertThat(ExplorePaint.status(fog, body, List.of(), mesh).place())
                .as("stood-on start is START, not leftover HALL")
                .isEqualTo("START");
        ExploreBody atGoal = ExploreBody.atCell(new Point(0, 1));
        assertThat(ExplorePaint.endPlaceName(atGoal, mesh)).isEqualTo("GOAL");
        assertThat(ExplorePaint.status(fog, atGoal, List.of(), mesh).place())
                .isEqualTo("GOAL");
        assertThat(ExplorePaint.status(fog, body, marks, mesh).place())
                .as("a visible story mark still leads")
                .isEqualTo("ENTRANCE");
        assertThat(ExplorePaint.status(fog, body, List.of(), mesh).startSeen())
                .as("earned start sits on the HUD key")
                .isTrue();
        assertThat(ExplorePaint.status(fog, body, List.of(), mesh).goalSeen())
                .as("earned goal sits on the HUD key")
                .isTrue();
        assertThat(ExplorePaint.status(fog, body, List.of()).startSeen()).isFalse();
        assertThat(ExplorePaint.endSeen(fog, mesh, TileType.START)).isTrue();
        assertThat(ExplorePaint.endSeen(null, mesh, TileType.START)).isFalse();
        assertThat(ExplorePaint.endSeen(fog, mesh, TileType.WALL)).isFalse();
        assertThat(ExplorePaint.endPlaceName(body, null)).isEqualTo("HALL");
        float[] hallInk = new float[3];
        float[] startInk = new float[3];
        float[] goalInk = new float[3];
        ExplorePaint.captionPlaceTint("HALL", hallInk);
        ExplorePaint.captionPlaceTint("START", startInk);
        ExplorePaint.captionPlaceTint("GOAL", goalInk);
        assertThat(hallInk[0]).isEqualTo(ExplorePaint.AIM_BRIGHT_R);
        assertThat(startInk[1]).as("START glyphs lift toward well mint")
                .isGreaterThan(hallInk[1]);
        assertThat(goalInk[0]).as("GOAL glyphs lift toward well coral")
                .isGreaterThan(hallInk[0]);
        float[] startSoft = new float[3];
        ExplorePaint.captionPlaceSoftTint("START", startSoft);
        assertThat(startSoft[1]).as("START underglow lifts toward mint")
                .isGreaterThan(ExplorePaint.CAPTION_SOFT_G);
    }

    @Test
    void statusNamesTheLampFacingCube() {
        ExploreFog fog = new ExploreFog();
        fog.stand(new Point(0, 0));
        ExploreBody body = ExploreBody.atCell(new Point(0, 0));
        body.look(Math.PI, 0);
        World volume = World.zero();
        volume.place(new BlockCoordinate(0, 0, 2), BlockType.WOOD);
        volume.place(new BlockCoordinate(4, 0, 2), BlockType.WOOD);
        WorldMesh cubes = WorldMesh.of(volume);
        assertThat(ExplorePaint.blockPlaceName(cubes, body)).isEqualTo("WOOD");
        assertThat(ExplorePaint.blockPlaceName(null, body)).isNull();
        MazeGrid grid = new MazeGrid(1, 2);
        grid.carve(grid.cell(0, 0), Direction.EAST);
        ExploreMesh mesh = ExploreMesh.of(grid);
        assertThat(ExplorePaint.status(fog, body, List.of(), mesh, cubes).place())
                .as("stood-on start still leads")
                .isEqualTo("START");
        ExploreBody hall = new ExploreBody(4, 0, Math.PI, 0);
        assertThat(ExplorePaint.endPlaceName(hall, mesh)).isEqualTo("HALL");
        assertThat(ExplorePaint.status(fog, hall, List.of(), mesh, cubes).place())
                .as("a lamp-facing cube names the hall")
                .isEqualTo("WOOD");
        List<ExploreMarker> marks = List.of(
                new ExploreMarker("door", new Point(0, 1), 0, "ENTRANCE"));
        fog.stand(new Point(0, 1));
        assertThat(ExplorePaint.status(fog, hall, marks, mesh, cubes).place())
                .as("a visible story mark still leads")
                .isEqualTo("ENTRANCE");
        float[] wood = new float[3];
        float[] hallInk = new float[3];
        ExplorePaint.captionPlaceTint("WOOD", wood);
        ExplorePaint.captionPlaceTint("HALL", hallInk);
        assertThat(wood[0]).as("WOOD glyphs wear torch wood, not leftover gold")
                .isGreaterThan(hallInk[2]);
        assertThat(wood[2]).isLessThan(wood[0]);
        float[] woodSoft = new float[3];
        float[] hallSoft = new float[3];
        float[] streetSoft = new float[3];
        ExplorePaint.captionPlaceSoftTint("WOOD", woodSoft);
        ExplorePaint.captionPlaceSoftTint("HALL", hallSoft);
        ExplorePaint.captionPlaceSoftTint("Willow Walk", streetSoft);
        assertThat(woodSoft[0]).as("WOOD underglow lifts toward torch wood")
                .isGreaterThan(hallSoft[0]);
        assertThat(streetSoft[0]).as("a named street underglow lifts toward torch wood")
                .isGreaterThan(hallSoft[0]);
    }

    @Test
    void statusKeysAnEarnedOccupiedCube() {
        ExploreFog fog = new ExploreFog();
        fog.stand(new Point(0, 0));
        MazeGrid grid = new MazeGrid(1, 2);
        grid.carve(grid.cell(0, 0), Direction.EAST);
        ExploreMesh mesh = ExploreMesh.of(grid);
        World volume = World.zero();
        volume.place(new BlockCoordinate(2, 0, 0), BlockType.WOOD);
        WorldMesh cubes = WorldMesh.of(volume);
        assertThat(ExplorePaint.blockSeen(fog, cubes))
                .as("earned cube sits on the HUD key")
                .isTrue();
        assertThat(ExplorePaint.blockSeen(new ExploreFog(), cubes)).isFalse();
        assertThat(ExplorePaint.blockSeen(fog, null)).isFalse();
        assertThat(ExplorePaint.status(fog, ExploreBody.atCell(new Point(0, 0)),
                List.of(), mesh, cubes).blockSeen()).isTrue();
        assertThat(ExplorePaint.status(fog, ExploreBody.atCell(new Point(0, 0)),
                List.of(), mesh).blockSeen()).isFalse();
        float[] wood = new float[3];
        float[] soft = new float[3];
        ExplorePaint.keyBlockTint(wood);
        ExplorePaint.keyBlockSoftTint(soft);
        assertThat(wood[0]).as("cube key wears torch wood, not leftover gold")
                .isGreaterThan(ExplorePaint.MAP_FLOOR_R);
        assertThat(wood[2]).isLessThan(wood[0]);
        assertThat(soft[0]).isLessThan(wood[0]);
        ExplorePaint.keyBlockTint(null);
        ExplorePaint.keyBlockSoftTint(null);
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
        assertThat(ExplorePaint.glyphDot('S', 2, 0)).isTrue();
        assertThat(ExplorePaint.glyphDot('G', 2, 0))
                .as("GOAL can paint on the strip")
                .isTrue();
        assertThat(ExplorePaint.glyphDot('D', 0, 0))
                .as("WOOD and DIRT can paint on the strip")
                .isTrue();
        assertThat(ExplorePaint.glyphDot('I', 2, 0)).isTrue();
        assertThat(ExplorePaint.glyphDot('M', 0, 0)).isTrue();
        assertThat(ExplorePaint.glyphDot('P', 0, 0)).isTrue();
        assertThat(ExplorePaint.glyphDot('K', 0, 0)).isTrue();
        assertThat(ExplorePaint.glyphDot('W', 0, 0)).isTrue();
    }

    @Test
    void statusNamesTheParcelYouStandIn() {
        ExploreFog fog = new ExploreFog();
        fog.stand(new Point(0, 0));
        MazeGrid grid = new MazeGrid(1, 2);
        grid.carve(grid.cell(0, 0), Direction.EAST);
        ExploreMesh mesh = ExploreMesh.of(grid);
        World volume = World.zero();
        volume.applyStamp(new ParcelBounds(8, 0, 8, 9, 1, 9), Parcel.SYSTEM_OWNER,
                List.of(new BlockCoordinate(8, 0, 8)), List.of(BlockType.WOOD));
        volume.nameParcel(volume.parcels().get(0).id(), "Willow Walk");
        WorldMesh cubes = WorldMesh.of(volume);
        ExploreBody onStreet = new ExploreBody(8.4, 8.4, 0, 0);
        assertThat(ExplorePaint.parcelPlaceName(cubes, onStreet)).isEqualTo("Willow Walk");
        assertThat(ExplorePaint.parcelPlaceName(null, onStreet)).isNull();
        assertThat(ExplorePaint.status(fog, onStreet, List.of(), mesh, cubes).place())
                .as("a named street leads leftover HALL")
                .isEqualTo("Willow Walk");
        World rented = World.zero();
        rented.applyStamp(new ParcelBounds(8, 0, 8, 9, 1, 9), Parcel.SYSTEM_OWNER,
                List.of(new BlockCoordinate(8, 0, 8)), List.of(BlockType.WOOD));
        rented.leaseParcel(rented.parcels().get(0).id(), Parcel.SYSTEM_TENANT);
        WorldMesh leased = WorldMesh.of(rented);
        assertThat(ExplorePaint.parcelLeaseName(leased, onStreet)).isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(ExplorePaint.status(fog, onStreet, List.of(), mesh, leased).place())
                .as("a lease leads leftover HALL when the street is unnamed")
                .isEqualTo(Parcel.SYSTEM_TENANT);
        assertThat(ExplorePaint.parcelLeaseName(null, onStreet)).isNull();
        ExploreBody atStart = ExploreBody.atCell(new Point(0, 0));
        assertThat(ExplorePaint.status(fog, atStart, List.of(), mesh, cubes).place())
                .as("stood-on start still leads")
                .isEqualTo("START");
        List<ExploreMarker> marks = List.of(
                new ExploreMarker("door", new Point(0, 1), 0, "ENTRANCE"));
        fog.stand(new Point(0, 1));
        assertThat(ExplorePaint.status(fog, onStreet, marks, mesh, cubes).place())
                .as("a visible story mark still leads")
                .isEqualTo("ENTRANCE");
        MazeGrid hall = new MazeGrid(3, 3);
        hall.carve(hall.cell(0, 0), Direction.EAST);
        hall.carve(hall.cell(0, 1), Direction.SOUTH);
        ExploreMesh longHall = ExploreMesh.of(hall);
        ExploreBody offPlot = ExploreBody.atCell(new Point(0, 1));
        assertThat(ExplorePaint.lastParcelPlaceName(cubes)).isEqualTo("Willow Walk");
        assertThat(ExplorePaint.lastParcelPlaceName(null)).isNull();
        assertThat(ExplorePaint.status(fog, offPlot, List.of(), longHall, cubes).place())
                .as("newest street name leads leftover HALL off the slab")
                .isEqualTo("Willow Walk");
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

    private static ExploreMesh.Triangle endCeiling(TileType tile) {
        return new ExploreMesh.Triangle(0, 2.8, 0, 1, 2.8, 0, 1, 2.8, 1,
                ExploreMesh.Face.CEILING, 3, 3, tile);
    }

    private static ExploreMesh.Triangle ceilingAt(double z) {
        return new ExploreMesh.Triangle(0, 2.8, z, 1, 2.8, z, 1, 2.8, z + 1,
                ExploreMesh.Face.CEILING, 3, 3);
    }
}
