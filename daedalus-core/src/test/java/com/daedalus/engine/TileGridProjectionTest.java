// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.model.TileType;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The glyph projection is the single source every renderer trusts (web canvas, JavaFX
 * desktop, ASCII art, the REST tiles field) — so its honesty rules get pinned here, once,
 * instead of being re-implemented per consumer. Found because all three JVM-side consumers
 * showed the same polka-dot dungeon; the web UI had already patched it client-side, which
 * was the tell that the fix belonged at the source.
 */
class TileGridProjectionTest {

    @Test
    void uncarvedRockProjectsAsWallNotAsFloatingFloor() {
        MazeGrid dungeon = new DungeonGenerator().generate(15, 21, 7L, new MazeStats());
        TileType[][] tiles = dungeon.toTileGrid();

        int rockCells = 0;
        for (int r = 0; r < 15; r++) {
            for (int c = 0; c < 21; c++) {
                if (dungeon.openNeighbors(new Point(r, c)).isEmpty()) {
                    rockCells++;
                    assertThat(tiles[2 * r + 1][2 * c + 1])
                            .as("uncarved cell (%d,%d) must project as WALL", r, c)
                            .isEqualTo(TileType.WALL);
                }
            }
        }
        assertThat(rockCells).as("a dungeon this size has real rock to test with").isPositive();
    }

    @Test
    void roomInteriorPostsProjectAsFloor() {
        MazeGrid dungeon = new DungeonGenerator().generate(15, 21, 7L, new MazeStats());
        TileType[][] tiles = dungeon.toTileGrid();

        int interiorPosts = 0;
        for (int r = 2; r < tiles.length - 1; r += 2) {
            for (int c = 2; c < tiles[0].length - 1; c += 2) {
                boolean surrounded = tiles[r - 1][c] != TileType.WALL
                        && tiles[r + 1][c] != TileType.WALL
                        && tiles[r][c - 1] != TileType.WALL
                        && tiles[r][c + 1] != TileType.WALL;
                if (surrounded) {
                    interiorPosts++;
                    assertThat(tiles[r][c])
                            .as("post (%d,%d) inside a room must be floor", r, c)
                            .isNotEqualTo(TileType.WALL);
                }
            }
        }
        assertThat(interiorPosts).as("a dungeon this size has rooms with interior posts").isPositive();
    }

    @Test
    void perfectMazeProjectionIsUnchangedByTheHonestyRules() {
        // Spanning trees have no rock (every cell carved) and no open 2x2 (that's a cycle),
        // so both rules are no-ops there — every cell tile is floor and every post is wall.
        MazeGrid maze = new RecursiveBacktrackerGenerator().generate(12, 17, 5L, new MazeStats());
        TileType[][] tiles = maze.toTileGrid();

        for (int r = 0; r < 12; r++) {
            for (int c = 0; c < 17; c++) {
                assertThat(tiles[2 * r + 1][2 * c + 1]).isNotEqualTo(TileType.WALL);
            }
        }
        for (int r = 2; r < tiles.length - 1; r += 2) {
            for (int c = 2; c < tiles[0].length - 1; c += 2) {
                assertThat(tiles[r][c]).isEqualTo(TileType.WALL);
            }
        }
    }

    @Test
    void aSingleCellMazeIsStillItsOwnFloor() {
        // The one legitimate zero-open-sides cell: a 1x1 maze. It may carry the START glyph
        // (grids default their endpoints); the assertion is only that it is not rock.
        MazeGrid one = new MazeGrid(1, 1);
        assertThat(one.toTileGrid()[1][1]).isNotEqualTo(TileType.WALL);
    }
}
