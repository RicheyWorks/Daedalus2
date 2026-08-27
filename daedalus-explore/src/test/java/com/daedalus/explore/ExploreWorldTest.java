// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

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
    void launcherStaysHeadlessWithoutTheFlag() {
        assertThat(ExploreLauncher.windowRequested(new String[] {})).isFalse();
        assertThat(ExploreLauncher.windowRequested(new String[] {ExploreLauncher.WINDOW_FLAG}))
                .isTrue();
        assertThat(ExploreLauncher.flag(new String[] {ExploreLauncher.SMOKE_FLAG},
                ExploreLauncher.SMOKE_FLAG)).isTrue();
        assertThat(ExploreLauncher.flag(null, ExploreLauncher.SMOKE_FLAG)).isFalse();
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
