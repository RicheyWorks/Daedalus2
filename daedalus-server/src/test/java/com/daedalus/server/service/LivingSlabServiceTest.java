// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.MazeMutatedEvent;
import com.daedalus.plugin.events.WorldBlockEvent;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.WorldId;
import com.daedalus.world.auto.WorldOps;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.context.ApplicationEventPublisher;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.FileTime;
import java.util.ArrayList;
import java.util.List;
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
        assertThat(WorldOps.driveLine(worlds.inspect(WorldId.ZERO.value())))
                .startsWith("living.sync ");
        assertThat(worlds.inspect(WorldId.ZERO.value()).lastDriveActor()).isEqualTo("system");
        assertThat(WorldOps.atLine(worlds.inspect(WorldId.ZERO.value()))).isNotEmpty();
        assertThat(worlds.trace(WorldId.ZERO.value()).get(
                worlds.trace(WorldId.ZERO.value()).size() - 1).capability())
                .isEqualTo("living.sync");
        assertThat(worlds.syncSlab(WorldId.ZERO.value(), mazeId, next)).isZero();
        assertThat(worlds.syncSlab(WorldId.ZERO.value(), UUID.randomUUID(), next)).isZero();
    }

    @Test
    void aLivingWriteFiresAWorldBlockEvent() {
        List<WorldBlockEvent> seen = new ArrayList<>();
        ApplicationEventPublisher pub = event -> {
            if (event instanceof WorldBlockEvent block) {
                seen.add(block);
            }
        };
        WorldService worlds = new WorldService(tmp.resolve("live-slab-events.daew"), pub);
        LivingSlabService listener = new LivingSlabService(worlds);
        MazeGrid maze = new MazeGrid(2, 2);
        maze.carve(new Point(0, 0), new Point(0, 1));
        UUID mazeId = UUID.fromString("00000000-0000-4000-8000-000000000007");
        worlds.stamp(WorldId.ZERO.value(), new BlockCoordinate(4, 2, 8), maze, mazeId);
        seen.clear();
        MazeGrid next = maze.copy();
        next.carve(new Point(0, 0), new Point(1, 0));
        listener.onMazeMutated(new MazeMutatedEvent(this, mazeId, 1, 1, 0, false, next));
        assertThat(seen).extracting(WorldBlockEvent::kind)
                .contains(WorldBlockEvent.Kind.WORLD_REVISION_CHANGED)
                .containsAnyOf(WorldBlockEvent.Kind.BLOCK_PLACED,
                        WorldBlockEvent.Kind.BLOCK_REMOVED);
        WorldBlockEvent last = seen.get(seen.size() - 1);
        assertThat(last.x() + "," + last.y() + "," + last.z())
                .isEqualTo(WorldOps.atLine(worlds.inspect(WorldId.ZERO.value())));
    }

    @Test
    void aLivingWriteMovesTheStoreMtime() throws Exception {
        Path file = tmp.resolve("live-slab-mtime.daew");
        WorldService worlds = new WorldService(file);
        LivingSlabService listener = new LivingSlabService(worlds);
        MazeGrid maze = new MazeGrid(2, 2);
        maze.carve(new Point(0, 0), new Point(0, 1));
        UUID mazeId = UUID.fromString("00000000-0000-4000-8000-000000000007");
        assertThat(worlds.stamp(WorldId.ZERO.value(), new BlockCoordinate(4, 2, 8), maze, mazeId)
                .ok()).isTrue();
        long frozen = Files.getLastModifiedTime(file).toMillis() + 5_000;
        Files.setLastModifiedTime(file, FileTime.fromMillis(frozen));
        MazeGrid next = maze.copy();
        next.carve(new Point(0, 0), new Point(1, 0));
        listener.onMazeMutated(new MazeMutatedEvent(this, mazeId, 1, 1, 0, false, next));
        assertThat(Files.getLastModifiedTime(file).toMillis()).isGreaterThan(frozen);
        assertThat(worlds.inspectBlock(WorldId.ZERO.value(), 5, 3, 10)).isEqualTo(BlockType.AIR);
    }

    @Test
    void aBoundSlabSurvivesRestartAndStillSyncs() {
        Path file = tmp.resolve("live-slab-restart.daew");
        UUID mazeId = UUID.fromString("00000000-0000-4000-8000-000000000007");
        MazeGrid maze = new MazeGrid(2, 2);
        maze.carve(new Point(0, 0), new Point(0, 1));
        BlockCoordinate origin = new BlockCoordinate(4, 2, 8);
        WorldService live = new WorldService(file);
        assertThat(live.stamp(WorldId.ZERO.value(), origin, maze, mazeId).ok()).isTrue();
        assertThat(live.inspect("world-zero").parcels().get(0).mazeRef())
                .isEqualTo(mazeId.toString());

        WorldService restarted = new WorldService(file);
        MazeGrid next = maze.copy();
        next.carve(new Point(0, 0), new Point(1, 0));
        new LivingSlabService(restarted).onMazeMutated(
                new MazeMutatedEvent(this, mazeId, 1, 1, 0, false, next));
        assertThat(restarted.inspectBlock(WorldId.ZERO.value(), 5, 3, 10)).isEqualTo(BlockType.AIR);
    }

    @Test
    void aSecondPlotKeepsItsOwnLivingBind() {
        WorldService worlds = new WorldService(tmp.resolve("live-street.daew"));
        LivingSlabService listener = new LivingSlabService(worlds);
        MazeGrid maze = new MazeGrid(2, 2);
        maze.carve(new Point(0, 0), new Point(0, 1));
        UUID firstId = UUID.fromString("00000000-0000-4000-8000-000000000007");
        UUID secondId = UUID.fromString("00000000-0000-4000-8000-000000000008");
        BlockCoordinate origin = new BlockCoordinate(0, 0, 0);
        assertThat(worlds.stamp(WorldId.ZERO.value(), origin, maze, firstId).ok()).isTrue();
        assertThat(worlds.stamp(WorldId.ZERO.value(), origin, maze, secondId, true).ok()).isTrue();
        assertThat(worlds.inspect("world-zero").parcels()).hasSize(2);
        BlockCoordinate firstPost = new BlockCoordinate(1, 1, 2);
        BlockCoordinate secondPost = new BlockCoordinate(7, 1, 2);
        assertThat(worlds.inspectBlock(WorldId.ZERO.value(), firstPost.x(), firstPost.y(),
                firstPost.z())).isEqualTo(BlockType.STONE);
        assertThat(worlds.inspectBlock(WorldId.ZERO.value(), secondPost.x(), secondPost.y(),
                secondPost.z())).isEqualTo(BlockType.STONE);

        MazeGrid next = maze.copy();
        next.carve(new Point(0, 0), new Point(1, 0));
        listener.onMazeMutated(new MazeMutatedEvent(this, secondId, 1, 1, 0, false, next));

        assertThat(worlds.inspectBlock(WorldId.ZERO.value(), firstPost.x(), firstPost.y(),
                firstPost.z())).isEqualTo(BlockType.STONE);
        assertThat(worlds.inspectBlock(WorldId.ZERO.value(), secondPost.x(), secondPost.y(),
                secondPost.z())).isEqualTo(BlockType.AIR);
    }
}
