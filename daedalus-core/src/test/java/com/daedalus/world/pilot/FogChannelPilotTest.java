// SPDX-License-Identifier: MIT

package com.daedalus.world.pilot;

import static org.assertj.core.api.Assertions.assertThat;

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
}
