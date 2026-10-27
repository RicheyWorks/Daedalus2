// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class GlyphLedgerTest {

    private static int[] naive(String s) {
        List<String> dict = new ArrayList<>();
        for (int c = 0; c < 256; c++) {
            dict.add(String.valueOf((char) c));
        }
        List<Integer> out = new ArrayList<>();
        int i = 0;
        while (i < s.length()) {
            int best = -1;
            int bestLen = 0;
            for (int d = 0; d < dict.size(); d++) {
                String p = dict.get(d);
                if (p.length() > bestLen && s.startsWith(p, i)) {
                    best = d;
                    bestLen = p.length();
                }
            }
            out.add(best);
            if (i + bestLen < s.length()) {
                dict.add(s.substring(i, i + bestLen + 1));
            }
            i += bestLen;
        }
        return out.stream().mapToInt(Integer::intValue).toArray();
    }

    @Test
    void matchesNaiveAndRoundTrips() {
        for (long seed = 0; seed < 300; seed++) {
            String s = GlyphLedger.ledger(seed, (int) (seed % 97));
            int[] codes = GlyphLedger.encode(s);
            assertThat(GlyphLedger.decode(codes)).isEqualTo(s);
            if (seed < 60) {
                assertThat(codes).containsExactly(naive(s));
            }
        }
        String big = GlyphLedger.ledger(7, 100_000);
        assertThat(GlyphLedger.decode(GlyphLedger.encode(big))).isEqualTo(big);
    }

    @Test
    void knownValues() {
        assertThat(GlyphLedger.encode("TOBEORNOTTOBEORTOBEORNOT"))
            .containsExactly(84, 79, 66, 69, 79, 82, 78, 79, 84, 256, 258, 260, 265, 259, 261, 263);
        assertThat(GlyphLedger.encode("aaaaaaa")).containsExactly(97, 256, 257, 97);
        assertThat(GlyphLedger.decode(new int[] {97, 256, 257, 97})).isEqualTo("aaaaaaa");
        assertThat(GlyphLedger.encode("")).isEmpty();
    }

    @Test
    void grades() {
        int[] c = GlyphLedger.encode("forge forge");
        assertThat(GlyphLedger.grade("forge forge", c)).isEqualTo(GlyphLedger.Grade.INTACT);
        assertThat(GlyphLedger.grade("forge forgf", c)).isEqualTo(GlyphLedger.Grade.SMUDGED);
        assertThat(GlyphLedger.grade("x", new int[] {999})).isEqualTo(GlyphLedger.Grade.SMUDGED);
        assertThat(GlyphLedger.forgemasterLine(GlyphLedger.Grade.INTACT)).contains("Forgemaster");
        assertThat(GlyphLedger.forgemasterLine(GlyphLedger.Grade.SMUDGED)).contains("smudged");
        assertThat(GlyphLedger.QUEST_ID).isEqualTo("q_glyph_ledger");
    }
}
