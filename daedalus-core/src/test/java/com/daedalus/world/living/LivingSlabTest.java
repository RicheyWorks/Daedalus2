// SPDX-License-Identifier: MIT

package com.daedalus.world.living;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Door;
import com.daedalus.world.Portal;
import com.daedalus.world.Trap;
import com.daedalus.world.World;
import com.daedalus.world.auto.WorldOps;
import com.daedalus.world.stamp.StampOps;
import com.daedalus.world.stamp.StampRequest;
import com.daedalus.world.stamp.StampResult;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * W1.2: living stays on the maze; the slab writes only cubes that actually change.
 */
class LivingSlabTest {

    @Test
    void inspectDoesNotBumpRevision() {
        World world = World.zero();
        MazeGrid maze = corridor();
        StampRequest request = request(world, maze);
        StampResult stamped = StampOps.apply(world, request);
        LivingSlab slab = new LivingSlab(world, request, stamped.bounds());
        long revision = world.revision().value();

        assertThat(slab.inspect(new BlockCoordinate(5, 2, 9))).isEqualTo(BlockType.STONE);
        assertThat(world.get(new BlockCoordinate(5, 2, 9))).isEqualTo(BlockType.STONE);
        assertThat(world.revision().value()).isEqualTo(revision);
    }

    @Test
    void aQuietSyncWritesNothing() {
        World world = World.zero();
        MazeGrid maze = corridor();
        StampRequest request = request(world, maze);
        StampResult stamped = StampOps.apply(world, request);
        LivingSlab slab = new LivingSlab(world, request, stamped.bounds());
        long revision = world.revision().value();

        assertThat(slab.sync()).isZero();
        assertThat(world.revision().value()).isEqualTo(revision);
    }

    @Test
    void carvingAPassageDropsWallPosts() {
        World world = World.zero();
        MazeGrid maze = corridor();
        StampRequest request = request(world, maze);
        StampResult stamped = StampOps.apply(world, request);
        LivingSlab slab = new LivingSlab(world, request, stamped.bounds());

        // South opening of cell (0,0) is still rock: tile (2,1) → (5, *, 10)
        BlockCoordinate post = new BlockCoordinate(5, 3, 10);
        assertThat(world.get(post)).isEqualTo(BlockType.STONE);

        maze.carve(new Point(0, 0), new Point(1, 0));
        int written = slab.sync();

        assertThat(written).isGreaterThan(0);
        assertThat(slab.lastWritten()).isNotNull();
        assertThat(slab.lastWrittenNow()).isNotNull();
        assertThat(slab.lastWrittenPrevious()).isNotNull()
                .isNotEqualTo(slab.lastWrittenNow());
        assertThat(world.get(new BlockCoordinate(5, 2, 10))).isEqualTo(BlockType.STONE);
        assertThat(world.get(post)).isEqualTo(BlockType.AIR);
        assertThat(slab.sync()).isZero();
    }

    @Test
    void aSyncKeepsOccupancyCubes() {
        World world = World.zero();
        MazeGrid maze = new MazeGrid(1, 1);
        StampRequest request = new StampRequest(world.id(), new BlockCoordinate(0, 0, 0),
                maze, 0, 1);
        StampResult stamped = StampOps.apply(world, request);
        LivingSlab slab = new LivingSlab(world, request, stamped.bounds());

        assertThat(world.get(Door.ZERO_AT)).isEqualTo(BlockType.AIR);
        assertThat(slab.sync()).isZero();
        assertThat(world.get(Door.ZERO_AT)).isEqualTo(BlockType.AIR);
        assertThat(world.get(Trap.ZERO_AT)).isEqualTo(BlockType.AIR);
        assertThat(world.get(Portal.ZERO_AT)).isEqualTo(BlockType.AIR);
        assertThat(WorldOps.occupantAt(world, Door.ZERO_AT)).isEqualTo("door");
        assertThat(WorldOps.occupantAt(world, Trap.ZERO_AT)).isEqualTo("trap");
        assertThat(WorldOps.occupantAt(world, Portal.ZERO_AT)).isEqualTo("portal");
    }

    @Test
    void aSyncStaysInsideTheStampedBounds() {
        World world = World.zero();
        MazeGrid small = new MazeGrid(1, 1);
        StampRequest stampedReq = new StampRequest(world.id(), new BlockCoordinate(4, 2, 8),
                small, 2, 1);
        StampResult stamped = StampOps.apply(world, stampedReq);
        MazeGrid wide = new MazeGrid(2, 2);
        StampRequest wideReq = new StampRequest(world.id(), new BlockCoordinate(4, 2, 8),
                wide, 2, 1);
        LivingSlab slab = new LivingSlab(world, wideReq, stamped.bounds());
        BlockCoordinate outside = new BlockCoordinate(8, 2, 8);

        assertThat(stamped.bounds().contains(outside)).isFalse();
        assertThat(world.get(outside)).isEqualTo(BlockType.AIR);
        slab.sync();
        assertThat(world.get(outside)).isEqualTo(BlockType.AIR);
        if (slab.lastWritten() != null) {
            assertThat(stamped.bounds().contains(slab.lastWritten())).isTrue();
        }
    }

    @Test
    void aSyncClearsCubesOutsideTheMazeGrid() {
        World world = World.zero();
        MazeGrid wide = corridor();
        StampRequest wideReq = request(world, wide);
        StampResult stamped = StampOps.apply(world, wideReq);
        BlockCoordinate leftover = new BlockCoordinate(8, 2, 8);
        assertThat(stamped.bounds().contains(leftover)).isTrue();
        assertThat(world.get(leftover)).isEqualTo(BlockType.STONE);

        MazeGrid small = new MazeGrid(1, 1);
        StampRequest smallReq = new StampRequest(world.id(), new BlockCoordinate(4, 2, 8),
                small, 2, 1);
        LivingSlab slab = new LivingSlab(world, smallReq, stamped.bounds());
        assertThat(slab.sync()).isGreaterThan(0);
        assertThat(world.get(leftover)).isEqualTo(BlockType.AIR);
        assertThat(world.get(new BlockCoordinate(5, 2, 9))).isEqualTo(BlockType.STONE);
        assertThat(stamped.bounds().contains(slab.lastWritten())).isTrue();
    }

    @Test
    void sealingAPassageRestoresWallPosts() {
        World world = World.zero();
        MazeGrid maze = corridor();
        maze.carve(new Point(0, 0), new Point(1, 0));
        StampRequest request = request(world, maze);
        StampResult stamped = StampOps.apply(world, request);
        LivingSlab slab = new LivingSlab(world, request, stamped.bounds());

        BlockCoordinate post = new BlockCoordinate(5, 3, 10);
        assertThat(world.get(post)).isEqualTo(BlockType.AIR);

        maze.seal(new Point(0, 0), new Point(1, 0));
        assertThat(slab.sync()).isGreaterThan(0);
        assertThat(world.get(post)).isEqualTo(BlockType.STONE);
    }

    private static MazeGrid corridor() {
        MazeGrid maze = new MazeGrid(2, 2);
        maze.carve(new Point(0, 0), new Point(0, 1));
        return maze;
    }

    private static StampRequest request(World world, MazeGrid maze) {
        return new StampRequest(world.id(), new BlockCoordinate(4, 2, 8), maze, 2, 1);
    }
}
