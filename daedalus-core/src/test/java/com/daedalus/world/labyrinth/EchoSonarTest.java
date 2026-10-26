// SPDX-License-Identifier: MIT
package com.daedalus.world.labyrinth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import java.util.List;
import org.junit.jupiter.api.Test;

class EchoSonarTest {
    /** Ring at every cell and step toward the silence: always the BFS-shortest route. */
    @Test void followingTheSilenceIsAlwaysShortest() {
        for (long seed = 0; seed < 120; seed++) {
            EchoSonar s = EchoSonar.seeded(6 + (int) (seed % 7), 6 + (int) (seed % 5), seed);
            int best = s.stepsToExit(s.start());
            EchoSonar.Walk w = s.new Walk(500);
            while (!w.out()) {
                List<EchoSonar.Echo> echoes = w.ping();
                List<EchoSonar.Echo> silent = echoes.stream().filter(EchoSonar.Echo::silent).toList();
                assertThat(silent).as("seed %d at %s", seed, w.at()).hasSize(1);
                assertThat(w.move(silent.get(0).dir())).isTrue();
            }
            assertThat(w.steps()).isEqualTo(best);
            assertThat(w.stars()).isEqualTo(3);
        }
    }

    @Test void deadEndsEchoByDepthWithBellPitches() {
        EchoSonar s = EchoSonar.seeded(10, 10, 42);
        int checked = 0;
        for (int r = 0; r < 10; r++) {
            for (int c = 0; c < 10; c++) {
                Point p = new Point(r, c);
                for (EchoSonar.Echo e : s.ping(p)) {
                    assertThat(e.hz()).isBetween(146.8, 220.0);
                    if (e.silent()) {
                        assertThat(e.echoMs()).isEqualTo(-1);
                        assertThat(e.gain()).isZero();
                    } else {
                        assertThat(e.depthCells()).isBetween(1, EchoSonar.MAX_DEPTH);
                        assertThat(e.echoMs()).isEqualTo(200 + 70 * e.depthCells());
                        assertThat(e.gain()).isEqualTo(EchoSonar.GAIN);
                        checked++;
                    }
                }
            }
        }
        assertThat(checked).isGreaterThan(50);
        assertThat(EchoSonar.hzOf(Direction.NORTH)).isLessThan(EchoSonar.hzOf(Direction.WEST));
    }

    @Test void exitCellHasNoSilentCorridorAndAOneCellDeadEndAnswersFast() {
        EchoSonar s = EchoSonar.seeded(8, 8, 7);
        Point exit = s.exit();
        assertThat(s.ping(exit)).noneMatch(EchoSonar.Echo::silent);
        boolean sawShort = false;
        for (int r = 0; r < 8; r++) {
            for (int c = 0; c < 8; c++) {
                for (EchoSonar.Echo e : s.ping(new Point(r, c))) {
                    sawShort |= !e.silent() && e.depthCells() == 1 && e.echoMs() == 270;
                }
            }
        }
        assertThat(sawShort).isTrue();
    }

    @Test void walkBudgetWallsAndStars() {
        EchoSonar s = EchoSonar.seeded(5, 5, 3);
        EchoSonar.Walk w = s.new Walk(1);
        w.ping();
        assertThat(w.pingsLeft()).isZero();
        assertThatThrownBy(w::ping).isInstanceOf(IllegalStateException.class);
        assertThat(w.stars()).isZero();
        boolean blocked = false;
        for (Direction d : Direction.values()) {
            if (!s.isOpen(new Point(0, 0), d)) {
                assertThat(w.move(d)).isFalse();
                blocked = true;
            }
        }
        assertThat(blocked).isTrue();
        assertThat(w.at()).isEqualTo(new Point(0, 0));
        assertThatThrownBy(() -> s.new Walk(-1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test void detourCostsStars() {
        EchoSonar s = EchoSonar.seeded(9, 9, 11);
        EchoSonar.Walk w = s.new Walk(1000);
        int best = s.stepsToExit(s.start());
        Direction back = null;
        boolean wandered = false;
        while (!w.out()) {
            List<EchoSonar.Echo> echoes = w.ping();
            EchoSonar.Echo dead = echoes.stream().filter(e -> !e.silent()).filter(e -> e.depthCells() >= 1).findFirst().orElse(null);
            if (!wandered && dead != null && w.at().equals(s.start())) {
                w.move(dead.dir());
                back = dead.dir().opposite();
                w.move(back);
                wandered = true;
                continue;
            }
            w.move(echoes.stream().filter(EchoSonar.Echo::silent).findFirst().orElseThrow().dir());
        }
        assertThat(w.steps()).isEqualTo(wandered ? best + 2 : best);
        assertThat(w.stars()).isEqualTo(wandered ? (best + 2) * 2 <= best * 3 ? 2 : 1 : 3);
    }

    @Test void seededIsRepeatableAndSizesAreChecked() {
        assertThat(EchoSonar.seeded(7, 7, 99).ping(new Point(3, 3))).isEqualTo(EchoSonar.seeded(7, 7, 99).ping(new Point(3, 3)));
        assertThatThrownBy(() -> EchoSonar.seeded(1, 5, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EchoSonar.seeded(5, 65, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EchoSonar.seeded(5, 5, 1).ping(new Point(9, 9))).isInstanceOf(IllegalArgumentException.class);
    }
}
