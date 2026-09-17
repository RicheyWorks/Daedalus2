// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.World;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class WorldMeshTest {

    @Test
    void emptyWorldHasNoTriangles() {
        WorldMesh mesh = WorldMesh.of(World.zero());
        assertThat(mesh.triangles()).isEmpty();
        assertThat(mesh.blocked(0.2, 0.2, 0.2)).isFalse();
    }

    @Test
    void aLoneCubeExposesSixFacesAndBlocksItsInterior() {
        World world = World.zero();
        world.place(new BlockCoordinate(3, 1, -2), BlockType.STONE);
        WorldMesh mesh = WorldMesh.of(world);
        assertThat(mesh.triangles()).hasSize(36);
        assertThat(mesh.triangles().stream()
                .filter(t -> t.face() == WorldMesh.Face.POS_Z)
                .anyMatch(t -> (t.y1() + t.y2() + t.y3()) / 3.0 < t.at().y() + WorldMesh.BOOT_FRAC))
                .as("side faces split a boot so the cube sits")
                .isTrue();
        assertThat(mesh.triangles().stream()
                .filter(t -> t.face() == WorldMesh.Face.POS_Z)
                .anyMatch(t -> (t.y1() + t.y2() + t.y3()) / 3.0
                        > t.at().y() + 1.0 - WorldMesh.CROWN_FRAC))
                .as("side faces split a crown so the cube meets the lid")
                .isTrue();
        assertThat(mesh.triangles()).extracting(WorldMesh.Triangle::type)
                .containsOnly(BlockType.STONE);
        assertThat(mesh.triangles()).extracting(WorldMesh.Triangle::face)
                .contains(WorldMesh.Face.POS_X, WorldMesh.Face.NEG_X,
                        WorldMesh.Face.POS_Y, WorldMesh.Face.NEG_Y,
                        WorldMesh.Face.POS_Z, WorldMesh.Face.NEG_Z);
        assertThat(mesh.blocked(3.4, 1.2, -1.7)).isTrue();
        assertThat(mesh.blocked(4.0, 1.2, -1.7)).isFalse();
        assertThat(world.contains(new BlockCoordinate(3, 1, -2))).isTrue();
    }

    @Test
    void aSharedFaceBetweenNeighborsIsCulled() {
        World world = World.zero();
        world.place(new BlockCoordinate(0, 0, 0), BlockType.DIRT);
        world.place(new BlockCoordinate(1, 0, 0), BlockType.WOOD);
        WorldMesh mesh = WorldMesh.of(world);
        assertThat(mesh.triangles()).hasSize(60);
        long shared = mesh.triangles().stream()
                .filter(t -> t.at().equals(new BlockCoordinate(0, 0, 0))
                        && t.face() == WorldMesh.Face.POS_X)
                .count();
        assertThat(shared).isZero();
        assertThat(mesh.blocked(0.5, 0.5, 0.5)).isTrue();
        assertThat(mesh.blocked(1.5, 0.5, 0.5)).isTrue();
    }

    @Test
    void corridorMeshIsADifferentTypeAndStillSmokes() {
        MazeGrid grid = new MazeGrid(2, 2);
        grid.setStart(new Point(0, 0));
        grid.setGoal(new Point(0, 1));
        grid.carve(grid.cell(0, 0), Direction.EAST);
        ExploreMesh corridor = ExploreMesh.of(grid);
        assertThat(corridor.triangles()).isNotEmpty();
        assertThat(WorldMesh.class.getName()).isNotEqualTo(ExploreMesh.class.getName());
        assertThat(WorldMesh.of(World.zero()).triangles())
                .isNotSameAs(corridor.triangles());
    }
}
