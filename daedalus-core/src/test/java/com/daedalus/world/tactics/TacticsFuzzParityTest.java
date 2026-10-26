// SPDX-License-Identifier: MIT

package com.daedalus.world.tactics;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.tactics.TacticalOrders.ParseResult;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HexFormat;
import org.junit.jupiter.api.Test;

/**
 * 600 mutated DTO 1 specs from tactics_core_test.cpp (odd whitespace, broken numbers, long lines, duplicated lines,
 * stray bars): Java's parser must accept exactly the ones C++ accepts, write them back to the same bytes, and refuse
 * the rest with the same message. Both parsers were rewritten for speed; this is what keeps them one grammar.
 */
class TacticsFuzzParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "tactics_parity.txt");

    @Test
    void javaAgreesWithCppOnEveryMutatedSpec() throws IOException {
        HexFormat hex = HexFormat.of();
        int cases = 0;
        int oks = 0;
        for (String line : Files.readAllLines(PARITY)) {
            if (!line.startsWith("fuzz\t")) {
                continue;
            }
            String[] p = line.split("\t", -1);
            String text = new String(hex.parseHex(p[1]), StandardCharsets.US_ASCII);
            ParseResult r = TacticalOrders.parse(text);
            if (p[2].equals("ok")) {
                assertThat(r.ok()).as("C++ accepted %s but Java said %s", p[1], r.error()).isTrue();
                assertThat(TacticalOrders.write(r.spec()))
                        .as(p[1]).isEqualTo(new String(hex.parseHex(p[3]), StandardCharsets.US_ASCII));
                oks++;
            } else {
                assertThat(r.ok()).as("C++ refused %s with '%s'", p[1], p[3]).isFalse();
                assertThat(r.error()).as(p[1]).isEqualTo(p[3]);
            }
            cases++;
        }
        assertThat(cases).isEqualTo(600);
        assertThat(oks).isGreaterThan(20);
    }
}
