// SPDX-License-Identifier: MIT

package com.daedalus.world.pilot;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.IntStream;
import org.junit.jupiter.api.Test;

class FogChannelPilotTest {

    private static final int SEEDS = 300;
    private static final int PARITY_SEEDS = 60;
    private static final Path CORE_TEST = Path.of("..", "engines", "unreal", "core-test");
    private static final String PARITY = "pilot_fog_channel_parity.txt";
    private static final String JUDGE_PARITY = "pilot_fog_channel_judge_parity.txt";
    private static final int JUDGE_SEEDS = 40;

    private static int bruteForce(FogChannelPilot.Harbour h) {
        int s = h.channels();
        int t = h.blasts();
        int bestCost = Integer.MAX_VALUE;
        int[] lanes = new int[t];
        int total = (int) Math.pow(s, t);
        for (int code = 0; code < total; code++) {
            int c = code;
            for (int k = 0; k < t; k++) {
                lanes[k] = c % s;
                c /= s;
            }
            bestCost = Math.min(bestCost, FogChannelPilot.cost(h, lanes));
        }
        return bestCost;
    }

    @Test
    void viterbiMatchesBruteForceOverEveryTrack() {
        for (int s = 1; s <= SEEDS; s++) {
            FogChannelPilot.Harbour h = FogChannelPilot.harbour("fog-" + s);
            FogChannelPilot.Track b = FogChannelPilot.best(h);
            assertThat(b.cost()).as("seed %d", s).isEqualTo(bruteForce(h));
            assertThat(FogChannelPilot.cost(h, b.lanes())).isEqualTo(b.cost());
        }
    }

    @Test
    void trustingEachEchoLosesOnAMeaningfulShareOfSeeds() {
        int losses = 0;
        for (int s = 1; s <= SEEDS; s++) {
            FogChannelPilot.Harbour h = FogChannelPilot.harbour("fog-" + s);
            int greedy = FogChannelPilot.loudestEcho(h).cost();
            int best = FogChannelPilot.best(h).cost();
            assertThat(greedy).isGreaterThanOrEqualTo(best);
            if (greedy > best) {
                losses++;
            }
        }
        System.out.println("G586 loudestEcho loses on " + losses + "/" + SEEDS + " seeds");
        assertThat(losses).isGreaterThanOrEqualTo(SEEDS / 5);
    }

    @Test
    void questAcceptsOnlyTheBestReading() {
        FogChannelPilot.Harbour h = FogChannelPilot.harbour("fog-7");
        assertThat(FogChannelPilot.quest(h, FogChannelPilot.best(h).lanes())).isTrue();
        assertThat(FogChannelPilot.cost(h, new int[] {9})).isEqualTo(FogChannelPilot.INVALID);
        assertThat(FogChannelPilot.cost(h, new int[h.blasts() + 1])).isEqualTo(FogChannelPilot.INVALID);
    }

    @Test
    void harbourIsSeededLikeCpython() {
        // Pinned from python3: r = random.Random("fog-1"); the same draw order as FogChannelPilot.harbour.
        FogChannelPilot.Harbour expected = new FogChannelPilot.Harbour(new int[] {1, 4, 1, 2},
                new int[][] {{2, 7, 9, 5}, {4, 1, 6, 8}, {4, 2, 1, 4}, {3, 9, 8, 0}},
                new int[][] {{1, 4, 0}, {4, 2, 3}, {0, 2, 4}, {0, 6, 4}}, new int[] {0, 0, 2, 1, 2});
        assertThat(FogChannelPilot.harbour("fog-1")).isEqualTo(expected);
        assertThat(FogChannelPilot.harbour("fog-2")).isNotEqualTo(expected);
    }

    static String join(int[] a) {
        if (a.length == 0) {
            return "-";
        }
        StringBuilder b = new StringBuilder();
        for (int v : a) {
            b.append(b.length() == 0 ? "" : ",").append(v);
        }
        return b.toString();
    }

    static String rows(int[][] a) {
        StringBuilder b = new StringBuilder();
        for (int[] r : a) {
            b.append(b.length() == 0 ? "" : "/").append(join(r));
        }
        return b.toString();
    }

    static List<String> parityLines() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= PARITY_SEEDS; s++) {
            FogChannelPilot.Harbour h = FogChannelPilot.harbour("fog-" + s);
            FogChannelPilot.Track b = FogChannelPilot.best(h);
            FogChannelPilot.Track g = FogChannelPilot.loudestEcho(h);
            out.add("seed=fog-" + s + " open=" + join(h.open()) + " drift=" + rows(h.drift()) + " echo=" + rows(h.echo()) + " heard="
                    + join(h.heard()) + " best=" + b.cost() + ":" + join(b.lanes()) + " loudest=" + g.cost() + ":" + join(g.lanes()));
        }
        return out;
    }

    @Test
    void parityFileMatchesCpp() throws IOException {
        Path path = CORE_TEST.resolve(PARITY);
        List<String> actual = parityLines();
        if (Boolean.getBoolean("pilot.parity.write")) {
            List<String> body = new ArrayList<>();
            body.add("# G586 FogChannelPilot parity: written by FogChannelPilotTest.java, replayed by pilot_fog_channel_core_test.cpp."
                    + " Seeds fog-1..fog-" + PARITY_SEEDS + " via random.Random(str).");
            body.addAll(actual);
            Files.write(path, body, StandardCharsets.UTF_8);
        }
        List<String> expected = Files.readAllLines(path, StandardCharsets.UTF_8).stream()
                .filter(l -> !l.startsWith("#") && !l.isBlank()).toList();
        assertThat(expected).hasSize(PARITY_SEEDS);
        IntStream.range(0, PARITY_SEEDS).forEach(i -> assertThat(actual.get(i)).as("%s line %d", PARITY, i).isEqualTo(expected.get(i)));
    }

    @Test
    void badHarboursAreRefused() {
        int[][] d2 = {{0, 3}, {3, 0}};
        int[][] e2 = {{1, 2, 3}, {3, 2, 1}};
        assertThatThrownBy(() -> new FogChannelPilot.Harbour(new int[0], new int[0][], new int[0][], new int[0]))
                .hasMessageContaining("bad harbour");
        assertThatThrownBy(() -> new FogChannelPilot.Harbour(new int[5], new int[5][5], new int[5][3], new int[0]))
                .hasMessageContaining("bad harbour");
        assertThatThrownBy(() -> new FogChannelPilot.Harbour(new int[2], d2, e2, new int[9])).hasMessageContaining("bad harbour");
        assertThatThrownBy(() -> new FogChannelPilot.Harbour(new int[] {-1, 0}, d2, e2, new int[1])).hasMessageContaining("bad channel");
        assertThatThrownBy(() -> new FogChannelPilot.Harbour(new int[2], new int[][] {{0, -1}, {3, 0}}, e2, new int[1]))
                .hasMessageContaining("negative drift");
        assertThatThrownBy(() -> new FogChannelPilot.Harbour(new int[2], d2, new int[][] {{1, 2}, {3, 2, 1}}, new int[1]))
                .hasMessageContaining("bad channel");
        assertThatThrownBy(() -> new FogChannelPilot.Harbour(new int[2], d2, new int[][] {{1, -2, 3}, {3, 2, 1}}, new int[1]))
                .hasMessageContaining("negative echo");
        assertThatThrownBy(() -> new FogChannelPilot.Harbour(new int[2], d2, e2, new int[] {4})).hasMessageContaining("unknown echo");
    }

    @Test
    void edgeHarboursStillHaveAnAnswer() {
        FogChannelPilot.Harbour silent = new FogChannelPilot.Harbour(new int[] {2, 0}, new int[][] {{0, 3}, {3, 0}},
                new int[][] {{1, 2, 3}, {3, 2, 1}}, new int[0]);
        assertThat(FogChannelPilot.best(silent)).isEqualTo(new FogChannelPilot.Track(0, new int[0]));
        assertThat(FogChannelPilot.loudestEcho(silent).cost()).isZero();
        assertThat(FogChannelPilot.judge(silent, new int[0]).stars()).isEqualTo(3);
        assertThat(FogChannelPilot.explainText(silent)).isEmpty();
        FogChannelPilot.Harbour one = new FogChannelPilot.Harbour(new int[] {4}, new int[][] {{1}}, new int[][] {{0, 5, 2}},
                new int[] {1, 2, 0});
        assertThat(FogChannelPilot.best(one)).isEqualTo(new FogChannelPilot.Track(4 + 5 + 1 + 2 + 1 + 0, new int[] {0, 0, 0}));
    }

    @Test
    void judgeGivesStarsAgainstPar() {
        for (int s = 1; s <= SEEDS; s++) {
            FogChannelPilot.Harbour h = FogChannelPilot.harbour("fog-" + s);
            FogChannelPilot.Judgement best = FogChannelPilot.judge(h, FogChannelPilot.best(h).lanes());
            assertThat(best.stars()).isEqualTo(3);
            assertThat(best.questDone()).isEqualTo(FogChannelPilot.quest(h, FogChannelPilot.best(h).lanes()));
            FogChannelPilot.Judgement greedy = FogChannelPilot.judge(h, FogChannelPilot.loudestEcho(h).lanes());
            int gap = greedy.cost() - greedy.par();
            assertThat(greedy.stars()).isEqualTo(gap == 0 ? 3 : gap <= FogChannelPilot.PAR_SLACK ? 2 : 1);
        }
        FogChannelPilot.Harbour h = FogChannelPilot.harbour("fog-7");
        assertThat(FogChannelPilot.judge(h, new int[] {9})).isEqualTo(new FogChannelPilot.Judgement(FogChannelPilot.INVALID,
                FogChannelPilot.par(h), 0, false));
    }

    @Test
    void explanationAddsUpToTheBestCost() {
        for (int s = 1; s <= SEEDS; s++) {
            FogChannelPilot.Harbour h = FogChannelPilot.harbour("fog-" + s);
            List<FogChannelPilot.Step> steps = FogChannelPilot.explain(h);
            assertThat(steps.stream().mapToInt(t -> t.moveCost() + t.echoCost()).sum()).isEqualTo(FogChannelPilot.best(h).cost());
            assertThat(FogChannelPilot.explainText(h)).hasSize(h.blasts());
        }
        assertThat(FogChannelPilot.explainText(FogChannelPilot.harbour("fog-1")).get(0))
                .isEqualTo("blast 1: heard dull, open lane 3 (+2 open, +0 echo); the echo alone says lane 2");
    }

    static List<String> judgeParityLines() {
        List<String> out = new ArrayList<>();
        for (int s = 1; s <= JUDGE_SEEDS; s++) {
            FogChannelPilot.Harbour h = FogChannelPilot.harbour("fog-" + s);
            FogChannelPilot.Judgement g = FogChannelPilot.judge(h, FogChannelPilot.loudestEcho(h).lanes());
            out.add("seed=fog-" + s + " par=" + g.par() + " loudest_stars=" + g.stars() + " why=" + String.join(" | ",
                    FogChannelPilot.explainText(h)));
        }
        return out;
    }

    @Test
    void judgeParityFileMatchesCpp() throws IOException {
        Path path = CORE_TEST.resolve(JUDGE_PARITY);
        List<String> actual = judgeParityLines();
        if (Boolean.getBoolean("pilot.parity.write")) {
            List<String> body = new ArrayList<>();
            body.add("# G586 FogChannelPilot judge + explain parity: written by FogChannelPilotTest.java, replayed by"
                    + " pilot_fog_channel_core_test.cpp. Seeds fog-1..fog-" + JUDGE_SEEDS + ".");
            body.addAll(actual);
            Files.write(path, body, StandardCharsets.UTF_8);
        }
        assertThat(Files.readAllLines(path, StandardCharsets.UTF_8).stream().filter(l -> !l.startsWith("#") && !l.isBlank()).toList())
                .isEqualTo(actual);
    }
}
