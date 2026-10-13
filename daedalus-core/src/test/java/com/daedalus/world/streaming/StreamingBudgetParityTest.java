// SPDX-License-Identifier: MIT

package com.daedalus.world.streaming;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.streaming.StreamingBudget.Manifest;
import com.daedalus.world.streaming.StreamingBudget.ParseResult;
import com.daedalus.world.streaming.StreamingBudget.PickResult;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import org.junit.jupiter.api.Test;

/** DSB 1 and the resident-set picker: the Java port must agree with the Unreal plugin's C++ byte for byte. */
class StreamingBudgetParityTest {

    /** Written by engines/unreal/core-test/streaming_budget_core_test.cpp --write. */
    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "streaming_budget_parity.txt");

    private static String unescape(String s) {
        return s.replace("\\r", "\r").replace("\\t", "\t").replace("\\n", "\n");
    }

    private static boolean[] flags(String bits) {
        boolean[] b = new boolean[bits.length()];
        for (int i = 0; i < b.length; i++) {
            b[i] = bits.charAt(i) == '1';
        }
        return b;
    }

    private static final String GOOD = "# from the island census\nDSB 1\r\nisland Iz_B x 1000 y 0 ram 300 disk 900\n\n"
            + "island Ia_A  x 0 y 0 ram 500 disk 2000\nisland Ic_C x -4000 y 3000 ram 400 disk 100\n";

    @Test
    void matchesTheCppOn40Manifests240PicksAndEveryRefusal() throws IOException {
        List<String> lines = Files.readAllLines(PARITY);
        int cases = 0;
        int picks = 0;
        int bads = 0;
        Manifest m = null;
        for (String line : lines) {
            if (line.startsWith("raw\t")) {
                ParseResult r = StreamingBudget.parse(unescape(line.substring(4)));
                assertThat(r.ok()).as(r.error()).isTrue();
                m = r.manifest();
            } else if (line.startsWith("canon\t")) {
                String want = unescape(line.substring(6));
                assertThat(StreamingBudget.write(m)).isEqualTo(want);
                assertThat(StreamingBudget.write(StreamingBudget.parse(want).manifest())).isEqualTo(want);
                cases++;
            } else if (line.startsWith("pick ")) {
                String[] halves = line.split(" = ");
                String[] p = halves[0].split(" ");
                PickResult r = StreamingBudget.pick(m, Long.parseLong(p[1]), Long.parseLong(p[2]), Long.parseLong(p[3]),
                        Long.parseLong(p[4]), Long.parseLong(p[5]), flags(p[6]));
                assertThat(r.ram() + " " + r.disk() + " " + r.count() + " " + r.bits()).as(line).isEqualTo(halves[1]);
                picks++;
            } else if (line.startsWith("bad\t")) {
                String[] p = line.split("\t");
                ParseResult r = StreamingBudget.parse(unescape(p[1]));
                assertThat(r.ok()).isFalse();
                assertThat(r.error()).as(p[1]).isEqualTo(p[2]);
                assertThat(r.manifest()).isNull();
                bads++;
            }
        }
        assertThat(cases).isEqualTo(40);
        assertThat(picks).isEqualTo(240);
        assertThat(bads).isEqualTo(17);
    }

    @Test
    void canonicalWriteSortsById() {
        ParseResult r = StreamingBudget.parse(GOOD);
        assertThat(r.ok()).isTrue();
        assertThat(StreamingBudget.write(r.manifest())).isEqualTo("DSB 1\nisland Ia_A x 0 y 0 ram 500 disk 2000\n"
                + "island Ic_C x -4000 y 3000 ram 400 disk 100\nisland Iz_B x 1000 y 0 ram 300 disk 900\n");
    }

    @Test
    void hysteresisKeepsEdgeIslandsAndBudgetSkipsWhatDoesNotFit() {
        Manifest m = StreamingBudget.parse(GOOD).manifest();
        assertThat(StreamingBudget.pick(m, 0, 0, 2000, 6000, 10000, null).bits()).isEqualTo("110");
        assertThat(StreamingBudget.pick(m, 0, 0, 2000, 6000, 10000, new boolean[] {false, false, true}).bits())
                .isEqualTo("111");
        assertThat(StreamingBudget.pick(m, 0, 0, 2000, 4999, 10000, new boolean[] {false, false, true}).bits())
                .isEqualTo("110");
        PickResult tight = StreamingBudget.pick(m, 0, 0, 6000, 6000, 450, null);
        assertThat(tight.bits()).isEqualTo("100");
        assertThat(tight.ram()).isEqualTo(300);
        assertThat(StreamingBudget.pick(m, 0, 0, 6000, 6000, 0, new boolean[] {true, true, true}).count()).isZero();
    }

    @Test
    void extremeCoordinatesDoNotOverflow() {
        long c = StreamingBudget.MAX_CM;
        Manifest far = new Manifest(List.of(new StreamingBudget.Island("F1", c, c, 1, 1),
                new StreamingBudget.Island("F2", -c, -c, 1, 1)));
        assertThat(StreamingBudget.pick(far, -c, -c, c, c, 10, null).bits()).isEqualTo("01");
    }
}
