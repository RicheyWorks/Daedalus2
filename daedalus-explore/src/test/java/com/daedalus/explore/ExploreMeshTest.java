// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.model.TileType;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class ExploreMeshTest {

    @Test
    void aClosedNorthWallBlocksMinusZ() {
        MazeGrid grid = eastOnlyAtSouth();
        ExploreMesh mesh = ExploreMesh.of(grid);
        double x = ExploreMesh.worldX(0);
        double z = ExploreMesh.worldZ(1);
        assertThat(mesh.solidTile(2, 1))
                .as("tile (2,1) is the NORTH segment of cell (1,0)")
                .isTrue();
        assertThat(mesh.blocked(x, z - 1.05, ExploreMesh.PLAYER_RADIUS))
                .as("closed NORTH must block a step toward -Z")
                .isTrue();
        assertThat(mesh.blocked(x, z, ExploreMesh.PLAYER_RADIUS)).isFalse();
    }

    @Test
    void anOpeningDoesNotBlock() {
        MazeGrid grid = eastOnlyAtSouth();
        grid.carve(grid.cell(1, 0), Direction.NORTH);
        ExploreMesh mesh = ExploreMesh.of(grid);
        assertThat(mesh.solidTile(2, 1)).isFalse();
        double x = ExploreMesh.worldX(0);
        assertThat(mesh.blocked(x, ExploreMesh.worldZ(1) - 1.0, ExploreMesh.PLAYER_RADIUS))
                .isFalse();
    }

    @Test
    void dungeonRockMatchesToTileGrid() {
        MazeGrid grid = new DungeonGenerator().generate(11, 11, 7L, new MazeStats());
        ExploreMesh mesh = ExploreMesh.of(grid);
        TileType[][] tiles = grid.toTileGrid();
        for (int tr = 0; tr < tiles.length; tr++) {
            for (int tc = 0; tc < tiles[tr].length; tc++) {
                assertThat(mesh.solidTile(tr, tc))
                        .as("tile %d,%d", tr, tc)
                        .isEqualTo(tiles[tr][tc] == TileType.WALL);
            }
        }
        assertThat(mesh.triangles()).isNotEmpty();
        assertThat(mesh.hulls()).isNotEmpty();
    }

    @Test
    void roomInteriorPostsAreFloor() {
        MazeGrid room = new MazeGrid(3, 3);
        for (int r = 0; r < 3; r++) {
            for (int c = 0; c < 3; c++) {
                if (c < 2) {
                    room.carve(room.cell(r, c), Direction.EAST);
                }
                if (r < 2) {
                    room.carve(room.cell(r, c), Direction.SOUTH);
                }
            }
        }
        ExploreMesh mesh = ExploreMesh.of(room);
        assertThat(mesh.solidTile(2, 2))
                .as("interior post with four open segments is passage")
                .isFalse();
    }

    @Test
    void cellCentersMapToWorld() {
        assertThat(ExploreMesh.worldX(3)).isEqualTo(6.0);
        assertThat(ExploreMesh.worldZ(2)).isEqualTo(4.0);
        assertThat(ExploreMesh.cellCol(6.2)).isEqualTo(3);
        assertThat(ExploreMesh.cellRow(3.6)).isEqualTo(2);
        Point start = new Point(1, 2);
        ExploreBody body = ExploreBody.atCell(start);
        assertThat(body.cell()).isEqualTo(start);
        assertThat(body.x()).isEqualTo(ExploreMesh.worldX(2));
        assertThat(body.z()).isEqualTo(ExploreMesh.worldZ(1));
    }

    /** Cell (1,0) is habitable via EAST; its NORTH wall stays closed. */
    private static MazeGrid eastOnlyAtSouth() {
        MazeGrid grid = new MazeGrid(2, 2);
        grid.setStart(new Point(1, 0));
        grid.setGoal(new Point(1, 1));
        grid.carve(grid.cell(1, 0), Direction.EAST);
        return grid;
    }
}
