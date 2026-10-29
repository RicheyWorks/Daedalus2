// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;

class RecamanRambleTest {

    @Test
    void matchesHashSetReference() {
        int n = 20_000;
        long[] a = RecamanRamble.terms(n);
        Set<Long> seen = new HashSet<>();
        Map<Long, Integer> first = new HashMap<>();
        long cur = 0;
        for (int i = 0; i < n; i++) {
            if (i > 0) {
                long back = cur - i;
                cur = back >= 0 && !seen.contains(back) ? back : cur + i;
            }
            seen.add(cur);
            first.putIfAbsent(cur, i);
            assertThat(a[i]).isEqualTo(cur);
            if (i % 997 == 0) {
                assertThat(RecamanRamble.distinct(i + 1)).isEqualTo(seen.size());
            }
        }
        for (long v = 0; v < 300; v++) {
            Integer f = first.get(v);
            assertThat(RecamanRamble.firstHit(v, n)).isEqualTo(f == null ? -1L : f.longValue());
        }
    }

    @Test
    void knownValues() {
        assertThat(RecamanRamble.terms(21))
            .containsExactly(0, 1, 3, 6, 2, 7, 13, 20, 12, 21, 11, 22, 10, 23, 9, 24, 8, 25, 43, 62, 42);
        assertThat(RecamanRamble.terms(25)[24]).isEqualTo(42);
        assertThat(RecamanRamble.firstHit(42, 100)).isEqualTo(20);
        assertThat(RecamanRamble.distinct(25)).isEqualTo(24);
        assertThat(RecamanRamble.firstHit(-3, 100)).isEqualTo(-1);
    }

    @Test
    void grades() {
        assertThat(RecamanRamble.grade(4, 2)).isEqualTo(RecamanRamble.Grade.ON_ROAD);
        assertThat(RecamanRamble.grade(4, 10)).isEqualTo(RecamanRamble.Grade.LOST);
        assertThat(RecamanRamble.forgemasterLine(RecamanRamble.Grade.ON_ROAD)).contains("Forgemaster");
        assertThat(RecamanRamble.forgemasterLine(RecamanRamble.Grade.LOST)).contains("lost");
        assertThat(RecamanRamble.QUEST_ID).isEqualTo("q_recaman_ramble");
    }
}
