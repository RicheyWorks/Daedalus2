// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.MazeMutatedEvent;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.WorldId;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * A living tick on a stamped lab maze rewrites only dirty cubes.
 */
class LivingSlabServiceTest {

    @TempDir
    Path tmp;

    @Test
    void aMutationEventDropsWallPostsOnTheStampedSlab() {
        WorldService worlds = new WorldService(tmp.resolve("live-slab.daew"));
        LivingSlabService listener = new LivingSlabService(worlds);
        MazeGrid maze = new MazeGrid(2, 2);
        maze.carve(new Point(0, 0), new Point(0, 1));
        UUID mazeId = UUID.fromString("00000000-0000-4000-8000-000000000007");
        BlockCoordinate origin = new BlockCoordinate(4, 2, 8);
        assertThat(worlds.stamp(WorldId.ZERO.value(), origin, maze, mazeId).ok()).isTrue();
        BlockCoordinate post = new BlockCoordinate(5, 3, 10);
        assertThat(worlds.inspectBlock(WorldId.ZERO.value(), 5, 3, 10)).isEqualTo(BlockType.STONE);

        MazeGrid next = maze.copy();
        next.carve(new Point(0, 0), new Point(1, 0));
        listener.onMazeMutated(new MazeMutatedEvent(this, mazeId, 1, 1, 0, false, next));

        assertThat(worlds.inspectBlock(WorldId.ZERO.value(), 5, 2, 10)).isEqualTo(BlockType.STONE);
        assertThat(worlds.inspectBlock(WorldId.ZERO.value(), post.x(), post.y(), post.z()))
                .isEqualTo(BlockType.AIR);
        assertThat(worlds.syncSlab(WorldId.ZERO.value(), mazeId, next)).isZero();
        assertThat(worlds.syncSlab(WorldId.ZERO.value(), UUID.randomUUID(), next)).isZero();
    }
}
