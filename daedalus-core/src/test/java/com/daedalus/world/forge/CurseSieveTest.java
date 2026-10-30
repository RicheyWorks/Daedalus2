// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.CurseSieve.Grade;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class CurseSieveTest {

    @Test
    void countsAndFirstHitMatchNaiveScan() {
        for (long seed = 0; seed < 250; seed++) {
            int k = 1 + (int) (seed % 4);
            String text = CurseSieve.inscription(seed, (int) (seed % 60), k);
            List<String> curses = new ArrayList<>();
            int m = 1 + (int) (seed % 6);
            for (int w = 0; w < m; w++) {
                curses.add(CurseSieve.inscription(seed * 31 + w, 1 + (int) ((seed + w) % 4), k));
            }
            CurseSieve sieve = new CurseSieve(curses);
            long[] want = new long[m];
            int first = -1;
            int firstEnd = Integer.MAX_VALUE;
            for (int w = 0; w < m; w++) {
                String c = curses.get(w);
                for (int i = text.indexOf(c); i >= 0; i = text.indexOf(c, i + 1)) {
                    want[w]++;
                    int end = i + c.length();
                    if (end < firstEnd || (end == firstEnd && i < first)) {
                        firstEnd = end;
                        first = i;
                    }
                }
            }
            assertThat(sieve.counts(text)).as("seed %d", seed).containsExactly(want);
            assertThat(sieve.firstHit(text)).as("seed %d first", seed).isEqualTo(first);
            assertThat(sieve.grade(text, want)).isEqualTo(Grade.PURGED);
        }
    }

    @Test
    void knownInscriptions() {
        CurseSieve s = new CurseSieve(List.of("he", "she", "his", "hers"));
        assertThat(s.counts("ushers")).containsExactly(1, 1, 0, 1);
        assertThat(s.firstHit("ushers")).isEqualTo(1);
        assertThat(new CurseSieve(List.of("aa")).counts("aaaa")).containsExactly(3);
        assertThat(new CurseSieve(List.of("x")).firstHit("fuaf")).isEqualTo(-1);
        assertThatThrownBy(() -> new CurseSieve(List.of(""))).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        CurseSieve s = new CurseSieve(List.of("fu", "ux"));
        assertThat(s.grade("fux", new long[] {1, 1})).isEqualTo(Grade.PURGED);
        assertThat(s.grade("fux", new long[] {1, 0})).isEqualTo(Grade.CURSED);
        for (Grade g : Grade.values()) {
            assertThat(CurseSieve.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(CurseSieve.QUEST_ID).isEqualTo("q_curse_sieve");
        assertThat(CurseSieve.inscription(9, 12, 3)).isEqualTo(CurseSieve.inscription(9, 12, 3)).hasSize(12);
        assertThatThrownBy(() -> CurseSieve.inscription(1, 3, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
