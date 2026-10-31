// SPDX-License-Identifier: MIT

package com.daedalus.mazegame;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.model.Direction;
import com.daedalus.model.Point;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;

class MazeRulesTest {

    private static final MazeFactory FACTORY = new MazeFactory();

    @Test
    void goldenSeedsAreStable() throws IOException {
        List<String> lines;
        try (InputStream in = MazeRulesTest.class.getResourceAsStream("/maze-game/golden-seeds.csv")) {
            assertThat(in).isNotNull();
            lines = new String(in.readAllBytes(), StandardCharsets.UTF_8).lines()
                    .filter(l -> !l.isBlank() && !l.startsWith("#")).toList();
        }
        assertThat(lines).hasSizeGreaterThanOrEqualTo(8);
        for (String line : lines) {
            String[] f = line.split(",");
            MazeRun run = new MazeRun(Long.parseLong(f[0]), Difficulty.valueOf(f[1]), FACTORY);
            assertThat(run.mazeHash()).as(line).isEqualTo(f[2]);
            assertThat(run.par()).as(line).isEqualTo(Integer.parseInt(f[3]));
        }
    }

    @ParameterizedTest
    @EnumSource(Difficulty.class)
    void everyDifficultyIsSolvableAndSized(Difficulty d) {
        for (long seed = 0; seed < 5; seed++) {
            MazeRun run = new MazeRun(seed, d, FACTORY);
            assertThat(run.size()).isEqualTo(d.size());
            assertThat(run.par()).isGreaterThanOrEqualTo(2 * (d.size() - 1));
            List<Point> route = run.ghost("bfs");
            assertThat(route.get(0)).isEqualTo(new Point(0, 0));
            assertThat(route.get(route.size() - 1)).isEqualTo(run.exit());
        }
    }

    @Test
    void sameSeedSameMazeDifferentTierDifferentMaze() {
        assertThat(new MazeRun(42, Difficulty.EASY, FACTORY).mazeHash())
                .isEqualTo(new MazeRun(42, Difficulty.EASY, FACTORY).mazeHash());
        assertThat(MazeFactory.engineSeed(42, Difficulty.EASY)).isNotEqualTo(MazeFactory.engineSeed(42, Difficulty.NORMAL));
        assertThat(new MazeRun(1, Difficulty.EASY, FACTORY).mazeHash())
                .isNotEqualTo(new MazeRun(2, Difficulty.EASY, FACTORY).mazeHash());
    }

    @Test
    void walkingTheOptimalRouteWinsWithThreeStars() {
        MazeRun run = new MazeRun(7, Difficulty.NORMAL, FACTORY);
        walk(run, run.ghost("bfs"));
        assertThat(run.isWon()).isTrue();
        assertThat(run.moves()).isEqualTo(run.par());
        assertThat(run.stars(Scoring.parMillis(run.par()))).isEqualTo(3);
        assertThat(run.score(0)).isEqualTo(1000);
        for (Direction d : Direction.values()) {
            assertThat(run.move(d)).isFalse();
        }
        assertThat(run.moves()).isEqualTo(run.par());
    }

    @Test
    void wallsAreRefusedAndNotCounted() {
        MazeRun run = new MazeRun(3, Difficulty.EASY, FACTORY);
        assertThat(run.move(Direction.NORTH)).isFalse();
        assertThat(run.move(Direction.WEST)).isFalse();
        assertThat(run.moves()).isZero();
        assertThat(run.isWon()).isFalse();
    }

    @Test
    void hintsFollowTheRouteAndCost() {
        MazeRun run = new MazeRun(11, Difficulty.HARD, FACTORY);
        List<Point> hint = run.hint(5);
        assertThat(hint).hasSize(5).isEqualTo(run.ghost("bfs").subList(1, 6));
        assertThat(run.hints()).isEqualTo(1);
        walk(run, run.ghost("bfs"));
        assertThat(run.stars(0)).isEqualTo(2);
        assertThat(run.score(0)).isEqualTo(1000 - Scoring.HINT_COST);
        assertThat(run.hint(5)).isEmpty();
    }

    @Test
    void ghostWorksForOtherSolvers() {
        MazeRun run = new MazeRun(5, Difficulty.EASY, FACTORY);
        assertThat(run.ghost("astar")).hasSize(run.par() + 1);
        List<Point> tremaux = run.ghost("tremaux");
        assertThat(tremaux.get(tremaux.size() - 1)).isEqualTo(run.exit());
    }

    @Test
    void fogHidesFarCellsUntilSeen() {
        MazeRun run = new MazeRun(9, Difficulty.BRUTAL, FACTORY);
        assertThat(run.isVisible(0, 0)).isTrue();
        assertThat(run.isVisible(3, 3)).isTrue();
        assertThat(run.isVisible(4, 0)).isFalse();
        assertThat(run.isVisible(60, 60)).isFalse();
        MazeRun clear = new MazeRun(9, Difficulty.EASY, FACTORY);
        assertThat(clear.isVisible(14, 14)).isTrue();
    }

    @Test
    void scoringTiers() {
        assertThat(Scoring.stars(10, 10, 4000, 0)).isEqualTo(3);
        assertThat(Scoring.stars(10, 10, 4001, 0)).isEqualTo(2);
        assertThat(Scoring.stars(10, 15, 0, 0)).isEqualTo(2);
        assertThat(Scoring.stars(10, 16, 0, 0)).isEqualTo(1);
        assertThat(Scoring.score(10, 20, 0, 0)).isEqualTo(500);
        assertThat(Scoring.score(10, 10, 14_000, 0)).isEqualTo(990);
        assertThat(Scoring.score(10, 10, 0, 20)).isZero();
        assertThat(Scoring.score(10, 0, 0, 0)).isZero();
    }

    @Test
    void dailySeedRollsOverAtUtcMidnight() {
        assertThat(DailySeed.of(LocalDate.of(2026, 10, 31))).isEqualTo(20261031L);
        Clock lateLa = Clock.fixed(Instant.parse("2026-11-01T06:30:00Z"), ZoneId.of("America/Los_Angeles"));
        assertThat(DailySeed.today(lateLa)).isEqualTo(20261101L);
        Clock beforeMidnight = Clock.fixed(Instant.parse("2026-10-31T23:59:59Z"), ZoneId.of("UTC"));
        assertThat(DailySeed.today(beforeMidnight)).isEqualTo(20261031L);
    }

    @Test
    void shareCodeRoundTrips() {
        for (Difficulty d : Difficulty.values()) {
            for (long seed : new long[] {0L, 1L, 20261031L, Long.MAX_VALUE}) {
                ShareCode code = new ShareCode(seed, d);
                ShareCode back = ShareCode.parse(code.encode().toLowerCase(java.util.Locale.ROOT));
                assertThat(back.seed()).isEqualTo(seed);
                assertThat(back.difficulty()).isEqualTo(d);
                assertThat(back.toString()).isEqualTo(code.encode());
            }
        }
        assertThat(new ShareCode(35, Difficulty.HARD).encode()).isEqualTo("LR-H-Z");
        assertThatThrownBy(() -> ShareCode.parse("XX-H-1")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ShareCode.parse("LR-Q-1")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ShareCode.parse("LR-HX1")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ShareCode(-1, Difficulty.EASY)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void difficultyParsesNamesAndLetters() {
        assertThat(Difficulty.parse("brutal")).isEqualTo(Difficulty.BRUTAL);
        assertThat(Difficulty.parse(" n ")).isEqualTo(Difficulty.NORMAL);
        assertThat(Difficulty.BRUTAL.fog()).isTrue();
        assertThat(Difficulty.EASY.fog()).isFalse();
        assertThatThrownBy(() -> Difficulty.parse("x")).isInstanceOf(IllegalArgumentException.class);
    }

    static void walk(MazeRun run, List<Point> route) {
        for (int i = 1; i < route.size(); i++) {
            Point a = route.get(i - 1);
            Point b = route.get(i);
            Direction d = com.daedalus.engine.MazeGrid.directionBetween(a, b);
            assertThat(run.move(d)).isTrue();
        }
    }
}
