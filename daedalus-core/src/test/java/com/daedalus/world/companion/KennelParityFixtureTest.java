// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;

/**
 * Contest gap G84: the Java kennel rules (G37 bond, G61 training odds, G65 growth) written as a parity table that the
 * header-only C++ twin {@code DaedalusKennelCore.h} replays in {@code engines/unreal/core-test/kennel_core_test.cpp}.
 * The table is regenerated into target/ every run and must match the committed copy byte for byte.
 */
class KennelParityFixtureTest {
    static final String[] COMMANDS = {"come", "stay", "fetch", "guard", "rescue"};

    static List<String> table() {
        List<String> out = new ArrayList<>();
        out.add("KENNEL 1");
        KennelBond.Rules r = KennelBond.Rules.defaults();
        for (int b = 0; b <= 100; b += 5) {
            out.add("tier " + b + " " + KennelBond.Tier.of(b));
            for (String c : COMMANDS) {
                out.add("odds " + b + " " + c + " " + KennelTraining.successPct(b, c) + " "
                    + (KennelBond.obeys(b, c) ? 1 : 0));
            }
        }
        int[] bonds = {0, 3, 24, 50, 79, 95, 100};
        for (int b : bonds) {
            for (int mask = 0; mask < 8; mask++) {
                for (int catches : new int[] {0, 2, 9}) {
                    KennelBond.Care c = new KennelBond.Care((mask & 1) != 0, (mask & 2) != 0, (mask & 4) != 0, catches);
                    out.add("step " + b + " " + (mask & 1) + " " + ((mask >> 1) & 1) + " " + ((mask >> 2) & 1) + " "
                        + catches + " " + KennelBond.step(b, c, r));
                }
            }
        }
        for (int d = 0; d <= 70; d++) {
            out.add("stage " + d + " " + KennelGrowth.Stage.of(d));
        }
        for (int care : new int[] {0, 2, 9, 20, 59}) {
            for (int mask = 0; mask < 8; mask++) {
                for (int roll : new int[] {0, 14, 15, 99}) {
                    KennelBond.Care c = new KennelBond.Care((mask & 1) != 0, (mask & 2) != 0, (mask & 4) != 0, 0);
                    KennelGrowth.Day day = KennelGrowth.day(new KennelGrowth.Pup("p", care, care, 40, 0), c, roll);
                    out.add("grow " + care + " " + (mask & 1) + " " + ((mask >> 1) & 1) + " " + ((mask >> 2) & 1) + " "
                        + roll + " " + day.after().careDays() + " " + day.after().bond());
                }
            }
        }
        return out;
    }

    @Test
    void committedParityTableMatchesJava() throws Exception {
        String want = String.join("\n", table()) + "\n";
        Path target = Path.of("target", "kennel_parity.txt");
        Files.createDirectories(target.getParent());
        Files.writeString(target, want, StandardCharsets.UTF_8);
        Path committed = Path.of("..", "engines", "unreal", "core-test", "kennel_parity.txt");
        assertThat(Files.exists(committed)).as("committed kennel_parity.txt").isTrue();
        assertThat(Files.readString(committed, StandardCharsets.UTF_8).replace("\r\n", "\n")).isEqualTo(want);
    }
}