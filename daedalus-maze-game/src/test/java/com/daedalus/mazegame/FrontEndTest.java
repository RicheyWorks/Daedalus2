// SPDX-License-Identifier: MIT

package com.daedalus.mazegame;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class FrontEndTest {

    private static final MazeFactory FACTORY = new MazeFactory();
    private static final Clock HALLOWEEN = Clock.fixed(Instant.parse("2026-10-31T21:00:00Z"), ZoneOffset.UTC);

    @Test
    void headlessCheckPassesEveryTier() {
        ByteArrayOutputStream buf = new ByteArrayOutputStream();
        int failures = HeadlessCheck.run(20261031L, FACTORY, new PrintStream(buf, true, StandardCharsets.UTF_8));
        String out = buf.toString(StandardCharsets.UTF_8);
        assertThat(failures).isZero();
        assertThat(out).contains("ALL TIERS SOLVABLE").contains("LR-B-").contains("c6a3d8e497600003");
    }

    @Test
    void mainHeadlessAndHelpAndBadArgs() throws IOException {
        assertThat(main(new String[] {"--headless", "--seed", "1"}, "")).contains("ALL TIERS SOLVABLE");
        assertThat(main(new String[] {"--headless"}, "")).contains("seed 20261031");
        assertThat(main(new String[] {"--help"}, "")).contains("Usage:");
        assertThat(main(new String[] {"--bogus"}, "")).contains("Unknown option");
        assertThat(main(new String[] {"--seed"}, "")).contains("Missing value");
        assertThat(main(new String[] {"--seed", "x"}, "")).contains("whole number");
        assertThat(main(new String[] {"--seed", "-3"}, "")).contains("non-negative");
    }

    @Test
    void parseHandlesCodesTiersAndDaily() {
        LabyrinthRun.Options o = LabyrinthRun.parse(new String[] {"--code", "lr-h-z"}, HALLOWEEN);
        assertThat(o.seed).isEqualTo(35L);
        assertThat(o.difficulty).isEqualTo(Difficulty.HARD);
        o = LabyrinthRun.parse(new String[] {"--seed", "5", "--daily", "--difficulty", "brutal", "--text"}, HALLOWEEN);
        assertThat(o.seed).isEqualTo(20261031L);
        assertThat(o.difficulty).isEqualTo(Difficulty.BRUTAL);
        assertThat(o.mode).isEqualTo("text");
        assertThat(LabyrinthRun.parse(new String[] {"--swing"}, HALLOWEEN).mode).isEqualTo("swing");
    }

    @Test
    void textModeQuitsAndPlaysToAWin(@TempDir Path home) throws IOException {
        String old = System.getProperty("user.home");
        System.setProperty("user.home", home.toString());
        try {
            assertThat(main(new String[] {"--text", "--seed", "3", "--difficulty", "easy"}, "x\nh\nq\n"))
                    .contains("@@").contains("hints 1").contains("Quit. Share code LR-E-3");
            MazeRun probe = new MazeRun(3, Difficulty.EASY, FACTORY);
            String keys = keys(probe.ghost("bfs"));
            String out = main(new String[] {"--text", "--seed", "3", "--difficulty", "easy"}, keys + "\n");
            assertThat(out).contains("ESCAPED! ").contains("New local best saved.");
            assertThat(main(new String[] {"--text", "--seed", "3", "--difficulty", "e"}, keys + "\n"))
                    .contains("Local best stands.");
            assertThat(Files.exists(home.resolve(".labyrinth-run/best-scores.properties"))).isTrue();
            assertThat(main(new String[] {"--seed", "3"}, "")).contains("@@").doesNotContain("ESCAPED");
        } finally {
            System.setProperty("user.home", old);
        }
    }

    @Test
    void textRenderShowsFogAndTrail() throws IOException {
        MazeRun brutal = new MazeRun(1, Difficulty.BRUTAL, FACTORY);
        String board = TextGame.render(brutal, brutal.hint(3));
        assertThat(board).contains("??").contains("@@").contains("..").doesNotContain("XX");
        MazeRun easy = new MazeRun(1, Difficulty.EASY, FACTORY);
        assertThat(TextGame.render(easy, List.of())).contains("XX");
        assertThat(TextGame.hud(easy, 1500)).contains("LR-E-1").contains("1.5s");
        assertThat(TextGame.play(easy, new BufferedReader(new StringReader("")), new PrintStream(new ByteArrayOutputStream(),
                true, StandardCharsets.UTF_8), () -> 0L)).isEqualTo(-1L);
    }

    @Test
    void bestScoresKeepTheHighest(@TempDir Path dir) throws IOException {
        Path f = dir.resolve("sub/best.properties");
        BestScores b = new BestScores(f);
        assertThat(b.best("LR-E-1")).isEmpty();
        assertThat(b.record("LR-E-1", 500, 2, 40, 9000)).isTrue();
        assertThat(b.record("LR-E-1", 400, 1, 50, 9000)).isFalse();
        assertThat(b.record("LR-E-1", 900, 3, 30, 3000)).isTrue();
        BestScores again = new BestScores(f);
        assertThat(again.best("LR-E-1")).contains(900);
        assertThat(again.file()).isEqualTo(f);
        Files.writeString(f, "LR-E-2=oops\n");
        assertThat(new BestScores(f).best("LR-E-2")).isEmpty();
        assertThat(BestScores.defaultFile().toString()).contains(".labyrinth-run");
    }

    @Test
    void skinsCycle() {
        assertThat(Skin.LUMEN_SLATE.next()).isEqualTo(Skin.EMBER_FACET);
        assertThat(Skin.MOSS_GLASS.next()).isEqualTo(Skin.LUMEN_SLATE);
        for (Skin s : Skin.values()) {
            assertThat(s.label()).isNotBlank();
            assertThat(s.floor()).isNotEqualTo(s.wall());
            assertThat(s.runner() | s.exit() | s.hint() | s.fog()).isPositive();
        }
    }

    private static String keys(List<Point> route) {
        StringBuilder sb = new StringBuilder();
        for (int i = 1; i < route.size(); i++) {
            Direction d = MazeGrid.directionBetween(route.get(i - 1), route.get(i));
            sb.append(switch (d) {
                case NORTH -> 'w';
                case SOUTH -> 's';
                case WEST -> 'a';
                case EAST -> 'd';
            });
        }
        return sb.toString();
    }

    private static String main(String[] args, String stdin) throws IOException {
        ByteArrayOutputStream buf = new ByteArrayOutputStream();
        LabyrinthRun.run(args, new ByteArrayInputStream(stdin.getBytes(StandardCharsets.UTF_8)),
                new PrintStream(buf, true, StandardCharsets.UTF_8), HALLOWEEN, true);
        return buf.toString(StandardCharsets.UTF_8);
    }
}
