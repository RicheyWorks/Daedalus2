// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class ChartIndexTest {

    private static ChartIndex harbour() {
        ChartIndex ix = new ChartIndex();
        ix.visit("Port Ash", 5);
        ix.visit("Port Brine", 9);
        ix.visit("Portal", 5);
        ix.visit("Pyre", 2);
        ix.visit("Ash", 7);
        ix.visit("port ash", 1);
        return ix;
    }

    @Test
    void prefixCountsAndTopK() {
        ChartIndex ix = harbour();
        assertThat(ix.size()).isEqualTo(5);
        assertThat(ix.countPrefix("port")).isEqualTo(3);
        assertThat(ix.countPrefix("P")).isEqualTo(4);
        assertThat(ix.countPrefix("q")).isZero();
        assertThat(ix.countPrefix("")).isEqualTo(5);
        assertThat(ix.visits("PORT ASH")).isEqualTo(6);
        assertThat(ix.suggest("port", 2)).containsExactly(
            new ChartIndex.Port("port brine", 9), new ChartIndex.Port("port ash", 6));
        assertThat(ix.suggest("port", 10)).extracting(ChartIndex.Port::name)
            .containsExactly("port brine", "port ash", "portal");
        assertThat(ix.suggest("zz", 3)).isEmpty();
        assertThat(ix.contains("por")).isFalse();
    }

    @Test
    void matchesBruteForceScan() {
        SplittableRandom rnd = new SplittableRandom(252);
        ChartIndex ix = new ChartIndex();
        Map<String, Long> truth = new HashMap<>();
        for (int i = 0; i < 400; i++) {
            StringBuilder sb = new StringBuilder();
            int len = 1 + rnd.nextInt(5);
            for (int j = 0; j < len; j++) {
                sb.append((char) ('a' + rnd.nextInt(3)));
            }
            long v = rnd.nextInt(10);
            ix.visit(sb.toString(), v);
            truth.merge(sb.toString(), v, Long::sum);
        }
        assertThat(ix.size()).isEqualTo(truth.size());
        for (String p : List.of("", "a", "b", "ab", "cca", "abcab")) {
            List<ChartIndex.Port> all = new ArrayList<>();
            truth.forEach((k, v) -> {
                if (k.startsWith(p)) {
                    all.add(new ChartIndex.Port(k, v));
                }
            });
            all.sort(Comparator.comparingLong(ChartIndex.Port::visits).reversed()
                .thenComparing(ChartIndex.Port::name));
            assertThat(ix.countPrefix(p)).isEqualTo(all.size());
            assertThat(ix.suggest(p, 7)).isEqualTo(all.subList(0, Math.min(7, all.size())));
        }
    }

    @Test
    void questAndBadInput() {
        ChartIndex ix = harbour();
        assertThat(ChartIndex.quest(ix, "p", 3, List.of("port brine", "port ash", "portal"))).isTrue();
        assertThat(ChartIndex.quest(ix, "p", 3, List.of("portal", "port ash", "port brine"))).isFalse();
        assertThat(ChartIndex.QUEST_ID).isEqualTo("q_chart_index");
        assertThatThrownBy(() -> ix.visit(" ", 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ix.visit("x", -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ix.suggest("p", -1)).isInstanceOf(IllegalArgumentException.class);
    }
}
