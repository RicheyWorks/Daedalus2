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

class ExploreWalkTest {

    @Test
    void aClosedWallRefusesTheCellChange() {
        MazeGrid grid = new MazeGrid(2, 2);
        grid.carve(grid.cell(1, 0), Direction.EAST);
        ExploreMesh mesh = ExploreMesh.of(grid);
        ExploreBody body = ExploreBody.atCell(new Point(1, 0));
        ExploreWalk.Outcome out = ExploreWalk.step(mesh, body, 0, -2.2);
        assertThat(out.cellChanged()).isFalse();
        assertThat(body.cell()).isEqualTo(new Point(1, 0));
    }

    @Test
    void anOpeningAllowsTheCellChange() {
        MazeGrid grid = new MazeGrid(2, 1);
        grid.carve(grid.cell(0, 0), Direction.SOUTH);
        ExploreMesh mesh = ExploreMesh.of(grid);
        ExploreBody body = ExploreBody.atCell(new Point(0, 0));
        ExploreWalk.Outcome out = ExploreWalk.step(mesh, body, 0, 2.2);
        assertThat(out.moved()).isTrue();
        assertThat(out.cellChanged()).isTrue();
        assertThat(body.cell()).isEqualTo(new Point(1, 0));
    }

    @Test
    void aSlideAlongAWallKeepsTheOpenAxis() {
        MazeGrid grid = new MazeGrid(1, 3);
        grid.carve(grid.cell(0, 0), Direction.EAST);
        grid.carve(grid.cell(0, 1), Direction.EAST);
        ExploreMesh mesh = ExploreMesh.of(grid);
        ExploreBody body = ExploreBody.atCell(new Point(0, 1));
        double z = body.z();
        ExploreWalk.step(mesh, body, 0.4, -1.5);
        assertThat(body.cell()).isEqualTo(new Point(0, 1));
        assertThat(body.z()).isGreaterThan(z - 1.0);
        assertThat(body.x()).isGreaterThan(ExploreMesh.worldX(1));
    }

    @Test
    void legalCellStepMatchesOpenNeighbors() {
        MazeGrid grid = new MazeGrid(2, 2);
        grid.carve(grid.cell(0, 0), Direction.EAST);
        assertThat(ExploreWalk.legalCellStep(grid, new Point(0, 0), new Point(0, 1))).isTrue();
        assertThat(ExploreWalk.legalCellStep(grid, new Point(0, 0), new Point(1, 0))).isFalse();
        assertThat(ExploreWalk.legalCellStep(grid, new Point(0, 0), new Point(0, 0))).isTrue();
        assertThat(ExploreWalk.legalCellStep(null, new Point(0, 0), new Point(0, 1))).isFalse();
        assertThat(ExploreWalk.legalCellStep(grid, new Point(0, 0), new Point(9, 9))).isFalse();
        assertThat(ExploreWalk.step(null, ExploreBody.atCell(new Point(0, 0)), 1, 0).moved())
                .isFalse();
    }

    @Test
    void anOccupiedCubeRefusesTheBodyAndTheCorridorStillOpens() {
        MazeGrid grid = new MazeGrid(2, 5);
        grid.carve(grid.cell(1, 3), Direction.EAST);
        ExploreMesh mesh = ExploreMesh.of(grid);
        World volume = World.zero();
        volume.place(new BlockCoordinate(7, 0, 2), BlockType.STONE);
        WorldMesh cubes = WorldMesh.of(volume);
        ExploreBody open = ExploreBody.atCell(new Point(1, 3));
        ExploreWalk.step(mesh, null, open, 2.2, 0);
        assertThat(open.cell()).isEqualTo(new Point(1, 4));

        ExploreBody blocked = ExploreBody.atCell(new Point(1, 3));
        ExploreWalk.step(mesh, cubes, blocked, 2.2, 0);
        assertThat(ExploreWalk.cubeBlocked(cubes, blocked.x(), blocked.z())).isFalse();
        assertThat(blocked.x()).isLessThan(7.0);
        assertThat(blocked.cell()).isEqualTo(new Point(1, 3));
    }
}
