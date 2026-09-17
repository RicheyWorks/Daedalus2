// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.World;
import com.daedalus.world.WorldStore;
import com.daedalus.world.living.LivingSlab;
import com.daedalus.world.stamp.StampOps;
import com.daedalus.world.stamp.StampRequest;
import com.daedalus.world.stamp.StampResult;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;

class ExploreWorldTest {

    @Test
    void fogKeepsUnseenTilesDark() {
        ExploreFog fog = new ExploreFog();
        Point start = new Point(1, 1);
        fog.stand(start);
        assertThat(fog.tileVisible(3, 3)).isTrue();
        assertThat(fog.tileVisible(2, 3)).isTrue();
        assertThat(fog.tileVisible(2, 2)).isTrue();
        assertThat(fog.tileVisible(8, 8)).isFalse();
        assertThat(fog.stoodOn(start)).isTrue();
        assertThat(fog.stood()).containsExactly(start);
        assertThat(fog.memorySize()).isEqualTo(1);
    }

    @Test
    void spawnLooksDownAnOpening() {
        MazeGrid grid = new MazeGrid(1, 2);
        grid.carve(grid.cell(0, 0), Direction.EAST);
        ExploreWorld world = new ExploreWorld("test", 1L, grid);
        assertThat(world.body().yaw()).isEqualTo(ExploreWorld.yawToward(Direction.EAST));
        assertThat(ExploreWorld.yawToward(null)).isZero();
        assertThat(ExploreWorld.yawToward(Direction.NORTH)).isZero();
        assertThat(ExploreWorld.yawToward(Direction.SOUTH)).isEqualTo(Math.PI);
        assertThat(ExploreWorld.yawToward(Direction.WEST)).isEqualTo(-Math.PI / 2);
    }

    @Test
    void aDungeonHasEntranceVaultsAndBoss() {
        ExploreWorld world = ExploreWorld.dungeon(21, 31, 7L);
        assertThat(world.generatorId()).isEqualTo("dungeon");
        assertThat(world.markers()).isNotEmpty();
        assertThat(world.markers().getFirst().kind()).isEqualTo("ENTRANCE");
        assertThat(world.markers().getLast().kind()).isEqualTo("BOSS");
        assertThat(world.body().cell()).isEqualTo(world.grid().start());
        assertThat(world.fog().stoodOn(world.grid().start())).isTrue();
    }

    @Test
    void livingPulseRebuildsTheMesh() {
        MazeGrid tree = new RecursiveBacktrackerGenerator()
                .generate(11, 11, 7L, new MazeStats());
        int before = openCount(tree);
        ExploreWorld world = new ExploreWorld("recursive-backtracker", 7L, tree);
        world.pulseLive(7L, false);
        assertThat(openCount(world.grid())).isGreaterThanOrEqualTo(before);
        assertThat(world.mesh().grid()).isSameAs(world.grid());
        world.pulseLive(8L, true);
        assertThat(world.mesh().triangles()).isNotEmpty();
    }

    @Test
    void occupyBloomsCostOnTheCellUnderfoot() {
        MazeGrid grid = new MazeGrid(2, 2);
        grid.carve(grid.cell(0, 0), Direction.EAST);
        ExploreWorld world = new ExploreWorld("test", 1L, grid);
        world.occupyHere();
        assertThat(world.grid()).isInstanceOf(WeightedMazeGrid.class);
        assertThat(world.grid().weightOf(world.body().cell())).isGreaterThan(1.0);
    }

    @Test
    void walkingRecordsASessionStep() {
        MazeGrid grid = new MazeGrid(1, 2);
        grid.carve(grid.cell(0, 0), Direction.EAST);
        ExploreWorld world = new ExploreWorld("test", 1L, grid);
        AtomicReference<Point> movedTo = new AtomicReference<>();
        world.session().onStep((from, to) -> movedTo.set(to));
        ExploreWalk.Outcome out = world.apply(new ExploreInput.Intent(1, 0, 0, 0), 0.3);
        assertThat(out.cellChanged()).isTrue();
        assertThat(movedTo.get()).isEqualTo(new Point(0, 1));
        assertThat(world.session().steps()).hasSize(1);
        assertThat(world.session().moveJson(movedTo.get())).contains("\"row\":0");
        assertThat(world.fog().stoodOn(new Point(0, 1))).isTrue();
    }

    @Test
    void storyExportNamesTheBoss() {
        ExploreWorld world = ExploreWorld.dungeon(11, 11, 7L);
        String json = ExploreStory.export(world);
        assertThat(json).contains("\"generator\":\"dungeon\"");
        assertThat(json).contains("\"kind\":\"BOSS\"");
        assertThat(json).contains("\"pose\":");
        assertThat(ExploreStory.escape("a\"b")).isEqualTo("a\\\"b");
        assertThat(ExploreStory.export((ExploreWorld) null)).isEqualTo("{}");
    }

    @Test
    void attachingBlocksDoesNotUnloadTheCorridor() {
        MazeGrid grid = new MazeGrid(1, 2);
        grid.carve(grid.cell(0, 0), Direction.EAST);
        ExploreWorld world = new ExploreWorld("test", 1L, grid);
        ExploreMesh corridor = world.mesh();
        World volume = World.zero();
        volume.place(new BlockCoordinate(0, 0, 0), BlockType.STONE);
        world.attachBlocks(volume);
        world.showBlocks(true);
        assertThat(world.showingBlocks()).isTrue();
        assertThat(world.mesh()).isSameAs(corridor);
        assertThat(world.blocks().triangles()).hasSize(44);
        world.attachBlocks(null);
        assertThat(world.showingBlocks()).isFalse();
        assertThat(world.mesh()).isSameAs(corridor);
    }

    @Test
    void aLivingSlabWriteRemeshesExposedCubes() {
        MazeGrid maze = new MazeGrid(2, 2);
        maze.carve(maze.cell(0, 0), Direction.EAST);
        ExploreWorld world = new ExploreWorld("test", 1L, maze);
        World volume = World.zero();
        StampRequest request = new StampRequest(volume.id(), new BlockCoordinate(4, 2, 8), maze, 2, 1);
        StampResult stamped = StampOps.apply(volume, request);
        world.attachBlocks(volume);
        world.showBlocks(true);
        BlockCoordinate post = new BlockCoordinate(5, 3, 10);
        assertThat(world.blocks().triangles()).anyMatch(t -> post.equals(t.at()));
        maze.carve(maze.cell(0, 0), Direction.SOUTH);
        assertThat(new LivingSlab(volume, request, stamped.bounds()).sync()).isGreaterThan(0);
        assertThat(world.blocks().triangles())
                .as("triangles stay stale until remesh")
                .anyMatch(t -> post.equals(t.at()));
        world.apply(ExploreInput.Intent.none(), 0.016);
        assertThat(world.blocks().triangles()).noneMatch(t -> post.equals(t.at()));
        assertThat(world.mesh().grid()).isSameAs(world.grid());
        world.syncBlocks();
        WorldMesh again = world.blocks();
        world.syncBlocks();
        assertThat(world.blocks()).isSameAs(again);
    }

    @Test
    void sampleBlocksSitBesideTheCorridor() {
        MazeGrid grid = new MazeGrid(1, 2);
        grid.carve(grid.cell(0, 0), Direction.EAST);
        ExploreWorld world = new ExploreWorld("test", 1L, grid);
        ExploreMesh corridor = world.mesh();
        world.attachSampleBlocks();
        assertThat(world.showingBlocks()).isTrue();
        assertThat(world.mesh()).isSameAs(corridor);
        assertThat(world.blocks().triangles()).isNotEmpty();
        assertThat(world.blocks().triangles()).extracting(WorldMesh.Triangle::type)
                .contains(BlockType.STONE, BlockType.DIRT, BlockType.WOOD, BlockType.GLASS);
        assertThat(world.blocks().world().parcels().get(0).placeName())
                .as("sample landmark wears the well street name")
                .isEqualTo(ExploreWorld.SAMPLE_PLACE);
    }

    @Test
    void aStoredWorldWalksInsteadOfTheSample(@TempDir Path tmp) throws Exception {
        MazeGrid grid = new MazeGrid(1, 2);
        grid.carve(grid.cell(0, 0), Direction.EAST);
        ExploreWorld world = new ExploreWorld("test", 1L, grid);
        World live = World.zero();
        live.place(new BlockCoordinate(2, 0, 2), BlockType.WOOD);
        Path file = tmp.resolve("world-zero.daew");
        WorldStore.save(live, file);
        world.attachStoredOrSample(file);
        assertThat(world.showingBlocks()).isTrue();
        assertThat(world.blocks().triangles()).extracting(WorldMesh.Triangle::type)
                .contains(BlockType.WOOD)
                .doesNotContain(BlockType.GLASS);
        world.attachStoredOrSample(tmp.resolve("missing.daew"));
        assertThat(world.blocks().world().parcels().get(0).placeName())
                .isEqualTo(ExploreWorld.SAMPLE_PLACE);
        world.attachStoredOrSample(null);
        assertThat(world.blocks().world().parcels().get(0).placeName())
                .isEqualTo(ExploreWorld.SAMPLE_PLACE);
    }

    @Test
    void launcherStaysHeadlessWithoutTheFlag() {
        assertThat(ExploreLauncher.windowRequested(new String[] {})).isFalse();
        assertThat(ExploreLauncher.windowRequested(new String[] {ExploreLauncher.WINDOW_FLAG}))
                .isTrue();
        assertThat(ExploreLauncher.flag(new String[] {ExploreLauncher.SMOKE_FLAG},
                ExploreLauncher.SMOKE_FLAG)).isTrue();
        assertThat(ExploreLauncher.flag(null, ExploreLauncher.SMOKE_FLAG)).isFalse();
        assertThat(ExploreLauncher.STORE_ENV).isEqualTo("DAEDALUS_WORLD_FILE");
        if (System.getenv(ExploreLauncher.STORE_ENV) == null) {
            assertThat(ExploreLauncher.storeFile().getFileName().toString())
                    .isEqualTo("world-zero.daew");
        }
    }

    private static int openCount(MazeGrid grid) {
        int n = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                n += grid.openNeighbors(new Point(r, c)).size();
            }
        }
        return n;
    }
}
