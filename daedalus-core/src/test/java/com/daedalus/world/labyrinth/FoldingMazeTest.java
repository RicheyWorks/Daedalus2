// SPDX-License-Identifier: MIT

package com.daedalus.world.labyrinth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.generators.GrowingTreeGenerator;
import com.daedalus.engine.generators.KruskalsGenerator;
import com.daedalus.model.Point;
import com.daedalus.world.labyrinth.FoldingMaze.Fold;

import java.util.SplittableRandom;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/** LAB08 Folding Maze boss: walls fold on a schedule and the exit is never lost. */
class FoldingMazeTest {

    static FoldingMaze maze(long seed) {
        return FoldingMaze.create(new KruskalsGenerator(), 16, 16, seed, 40);
    }

    /** A wandering player: one random open step per fold, so reachability is checked from many cells. */
    static Point wander(FoldingMaze m, Point p, SplittableRandom r) {
        Point[] steps = {p.translate(1, 0), p.translate(-1, 0), p.translate(0, 1), p.translate(0, -1)};
        Point s = steps[r.nextInt(4)];
        return s.row() >= 0 && s.col() >= 0 && s.row() < m.rows() && s.col() < m.cols() && m.passable(p, s) ? s : p;
    }

    @ParameterizedTest
    @ValueSource(longs = {1, 2, 3, 7, 99})
    void theExitStaysReachableThrough300BackgroundFolds(long seed) {
        FoldingMaze m = maze(seed);
        SplittableRandom r = new SplittableRandom(seed);
        Point p = m.start();
        int changed = 0;
        for (int t = 0; t < 300; t++) {
            Fold f = m.fold(p);
            assertThat(m.exitReachable(p)).as("fold %d", t).isTrue();
            assertThat(f.routeLength()).isEqualTo(m.routeLength(p)).isPositive();
            changed += f.opened().size() + f.closed().size();
            p = wander(m, p, r);
        }
        assertThat(changed).as("the maze really moves").isGreaterThan(300);
    }

    @ParameterizedTest
    @ValueSource(longs = {1, 2, 3, 7, 99})
    void theBossNeverTrapsThePlayerEither(long seed) {
        FoldingMaze m = maze(seed);
        SplittableRandom r = new SplittableRandom(seed);
        Point p = m.start();
        for (int t = 0; t < 150; t++) {
            m.bossFold(p);
            assertThat(m.exitReachable(p)).as("boss fold %d", t).isTrue();
            p = wander(m, p, r);
        }
    }

    @Test
    void closesThatWouldTrapThePlayerAreVetoed() {
        int vetoes = 0;
        for (long seed = 1; seed <= 10; seed++) {
            FoldingMaze m = maze(seed);
            for (int t = 0; t < 50; t++) {
                vetoes += m.fold(m.start()).vetoed().size();
            }
        }
        assertThat(vetoes).as("passage mimics sometimes hold the only route").isPositive();
    }

    @Test
    void theBossLengthensTheRoute() {
        long bossTotal = 0, backgroundTotal = 0;
        for (long seed = 1; seed <= 8; seed++) {
            FoldingMaze boss = maze(seed), calm = maze(seed);
            for (int t = 0; t < 20; t++) {
                bossTotal += boss.bossFold(boss.start()).routeLength();
                backgroundTotal += calm.fold(calm.start()).routeLength();
            }
        }
        assertThat(bossTotal).isGreaterThan(backgroundTotal);
    }

    @Test
    void halfTheMimicsStartAsPassages_halfAsWalls() {
        FoldingMaze m = maze(5);
        assertThat(m.mimics()).hasSize(40);
        int open = 0;
        for (int i = 0; i < 40; i++) {
            open += m.isOpen(i) ? 1 : 0;
            assertThat(m.passable(m.mimics().get(i).a(), m.mimics().get(i).b())).isEqualTo(m.isOpen(i));
        }
        assertThat(open).isEqualTo(20);
        assertThat(m.exitReachable(m.start())).isTrue();
    }

    @Test
    void deterministicForTheSameGeneratorSizeAndSeed() {
        FoldingMaze a = maze(11), b = maze(11);
        for (int t = 0; t < 40; t++) {
            assertThat(a.fold(a.start())).isEqualTo(b.fold(b.start()));
        }
        assertThat(a.mimics()).isEqualTo(b.mimics());
        assertThat(maze(12).mimics()).isNotEqualTo(a.mimics());
    }

    @Test
    void worksWithAnyEngineGenerator() {
        MazeGenerator g = new GrowingTreeGenerator();
        FoldingMaze m = FoldingMaze.create(g, 12, 20, 3, 30);
        for (int t = 0; t < 100; t++) {
            m.fold(new Point(6, 10));
            assertThat(m.exitReachable(new Point(6, 10))).isTrue();
        }
    }

    @Test
    void refusesBadInput() {
        assertThatThrownBy(() -> FoldingMaze.create(new KruskalsGenerator(), 1, 8, 1, 4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FoldingMaze.create(new KruskalsGenerator(), 8, 65, 1, 4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FoldingMaze.create(new KruskalsGenerator(), 8, 8, 1, 257)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FoldingMaze.create(null, 8, 8, 1, 4)).isInstanceOf(IllegalArgumentException.class);
        FoldingMaze m = maze(1);
        assertThatThrownBy(() -> m.fold(new Point(99, 0))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new FoldingMaze.Wall(new Point(0, 0), new Point(2, 0))).isInstanceOf(IllegalArgumentException.class);
    }
}