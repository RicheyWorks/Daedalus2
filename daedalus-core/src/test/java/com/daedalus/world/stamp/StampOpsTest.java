// SPDX-License-Identifier: MIT

package com.daedalus.world.stamp;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Door;
import com.daedalus.world.Portal;
import com.daedalus.world.Trap;
import com.daedalus.world.World;
import com.daedalus.world.WorldStore;
import com.daedalus.world.auto.WorldOps;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * W1.1: maze tiles become a stone slab; overlap is a named refusal; cubes survive restart.
 */
class StampOpsTest {

    @TempDir
    Path tmp;

    @Test
    void aOneByOneMazeWritesFloorAndWallPosts() {
        World world = World.zero();
        StampResult result = StampOps.apply(world, request(world, oneByOne(), 0, 0, 0, 1));

        assertThat(result.ok()).isTrue();
        assertThat(result.parcelId().value()).isEqualTo("parcel-1");
        assertThat(result.revision().value()).isGreaterThan(0);
        assertThat(world.parcels()).hasSize(1);

        // 3×3 tiles: walls occupy floorY..floorY+1; the GOAL cell is floor only.
        // (0,1,0) is door-zero — occupancy stays AIR, not this post.
        assertThat(world.get(new BlockCoordinate(0, 0, 0))).isEqualTo(BlockType.STONE);
        assertThat(world.get(new BlockCoordinate(0, 1, 2))).isEqualTo(BlockType.STONE);
        assertThat(world.get(new BlockCoordinate(1, 0, 1))).isEqualTo(BlockType.STONE);
        assertThat(world.get(new BlockCoordinate(1, 1, 1))).isEqualTo(BlockType.AIR);
        assertThat(world.get(new BlockCoordinate(2, 1, 2))).isEqualTo(BlockType.STONE);
        assertThat(world.get(new BlockCoordinate(3, 0, 0))).isEqualTo(BlockType.AIR);
        assertThat(world.get(new BlockCoordinate(-1, 0, 0))).isEqualTo(BlockType.AIR);
        assertThat(world.get(new BlockCoordinate(1, 0, 3))).isEqualTo(BlockType.AIR);
    }

    @Test
    void aStampKeepsOccupancyCubes() {
        World world = World.zero();
        StampOps.apply(world, request(world, oneByOne(), 0, 0, 0, 1));

        assertThat(world.get(Door.ZERO_AT)).isEqualTo(BlockType.AIR);
        assertThat(world.get(Trap.ZERO_AT)).isEqualTo(BlockType.AIR);
        assertThat(world.get(Portal.ZERO_AT)).isEqualTo(BlockType.AIR);
        assertThat(WorldOps.occupantAt(world, Door.ZERO_AT)).isEqualTo("door");
        assertThat(WorldOps.occupantAt(world, Trap.ZERO_AT)).isEqualTo("trap");
        assertThat(WorldOps.occupantAt(world, Portal.ZERO_AT)).isEqualTo("portal");
        assertThat(world.get(new BlockCoordinate(0, 0, 0))).isEqualTo(BlockType.STONE);
        assertThat(world.get(new BlockCoordinate(0, 1, 2))).isEqualTo(BlockType.STONE);
    }

    @Test
    void aCarvedPassageIsFloorOnly() {
        World world = World.zero();
        MazeGrid maze = new MazeGrid(2, 2);
        maze.carve(new Point(0, 0), new Point(0, 1));
        StampOps.apply(world, request(world, maze, 4, 2, 8, 1));

        // Cell (0,0) center is tile (1,1) → block (5, 2, 9); carved so floor only.
        assertThat(world.get(new BlockCoordinate(5, 2, 9))).isEqualTo(BlockType.STONE);
        assertThat(world.get(new BlockCoordinate(5, 3, 9))).isEqualTo(BlockType.AIR);
        // East opening between (0,0) and (0,1) is tile (1,2) → (6, 2, 9).
        assertThat(world.get(new BlockCoordinate(6, 2, 9))).isEqualTo(BlockType.STONE);
        assertThat(world.get(new BlockCoordinate(6, 3, 9))).isEqualTo(BlockType.AIR);
    }

    @Test
    void overlappingStampDoesNotMutate() {
        World world = World.zero();
        StampOps.apply(world, request(world, oneByOne(), 0, 0, 0, 1));
        long revision = world.revision().value();
        int chunks = world.chunkCount();
        BlockType corner = world.get(new BlockCoordinate(0, 0, 0));

        StampResult overlap = StampOps.apply(world, request(world, oneByOne(), 1, 0, 1, 1));

        assertThat(overlap.ok()).isFalse();
        assertThat(overlap.reason()).isEqualTo(StampResult.PARCEL_OVERLAP);
        assertThat(world.revision().value()).isEqualTo(revision);
        assertThat(world.chunkCount()).isEqualTo(chunks);
        assertThat(world.get(new BlockCoordinate(0, 0, 0))).isEqualTo(corner);
        assertThat(world.parcels()).hasSize(1);
    }

    @Test
    void stampSurvivesWorldStoreRestart() throws Exception {
        World live = World.zero();
        StampResult stamped = StampOps.apply(live, request(live, oneByOne(), 0, 0, 0, 1));
        Path file = tmp.resolve("stamped.daew");
        WorldStore.save(live, file);

        World reloaded = WorldStore.load(file);
        assertThat(reloaded.get(new BlockCoordinate(0, 0, 0))).isEqualTo(BlockType.STONE);
        assertThat(reloaded.get(new BlockCoordinate(1, 0, 1))).isEqualTo(BlockType.STONE);
        assertThat(reloaded.get(new BlockCoordinate(1, 1, 1))).isEqualTo(BlockType.AIR);
        assertThat(reloaded.parcels()).hasSize(1);
        assertThat(reloaded.parcels().get(0).id()).isEqualTo(stamped.parcelId());
        assertThat(reloaded.revision()).isEqualTo(live.revision());

        StampResult overlap = StampOps.apply(reloaded, request(reloaded, oneByOne(), 0, 0, 0, 1));
        assertThat(overlap.reason()).isEqualTo(StampResult.PARCEL_OVERLAP);
        assertThat(reloaded.revision()).isEqualTo(live.revision());
    }

    @Test
    void nextOriginWalksEastPastAnOccupiedSlab() {
        World world = World.zero();
        StampOps.apply(world, request(world, oneByOne(), 0, 0, 0, 1));
        BlockCoordinate next = StampOps.nextOrigin(world, oneByOne(),
                new BlockCoordinate(0, 0, 0), 1);
        assertThat(next).isEqualTo(new BlockCoordinate(4, 0, 0));
        StampResult second = StampOps.apply(world, request(world, oneByOne(),
                next.x(), next.y(), next.z(), 1));
        assertThat(second.ok()).isTrue();
        assertThat(world.parcels()).hasSize(2);
        assertThat(StampOps.nextOrigin(world, oneByOne(), new BlockCoordinate(0, 0, 0), 1)
                .x()).isGreaterThan(next.x());
    }

    @Test
    void adjacentNonOverlappingStampIsAllowed() {
        World world = World.zero();
        StampOps.apply(world, request(world, oneByOne(), 0, 0, 0, 1));
        StampResult second = StampOps.apply(world, request(world, oneByOne(), 3, 0, 3, 1));
        assertThat(second.ok()).isTrue();
        assertThat(second.parcelId().value()).isEqualTo("parcel-2");
        assertThat(world.parcels()).hasSize(2);
    }

    private static MazeGrid oneByOne() {
        return new MazeGrid(1, 1);
    }

    private static StampRequest request(World world, MazeGrid maze, int x, int y, int z, int wallHeight) {
        return new StampRequest(world.id(), new BlockCoordinate(x, y, z), maze, y, wallHeight);
    }
}
