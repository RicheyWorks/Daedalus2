// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.BilletRanks.Grade;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class BilletRanksTest {

    @Test
    void matchesSortedListOracleOnSeededScripts() {
        for (long seed = 0; seed < 120; seed++) {
            BilletRanks rack = new BilletRanks(seed);
            List<Long> oracle = new ArrayList<>();
            for (long op : BilletRanks.script(seed, 300, 1 + (int) (seed % 50))) {
                if (op > 0) {
                    rack.add(op);
                    int at = Collections.binarySearch(oracle, op);
                    oracle.add(at < 0 ? -at - 1 : at, op);
                } else {
                    boolean had = oracle.remove(Long.valueOf(-op));
                    assertThat(rack.remove(-op)).as("seed %d remove %d", seed, -op).isEqualTo(had);
                }
                assertThat(rack.size()).isEqualTo(oracle.size());
            }
            for (int k = 0; k < oracle.size(); k++) {
                assertThat(rack.kth(k)).as("seed %d k %d", seed, k).isEqualTo(oracle.get(k));
            }
            for (long w = 0; w <= 52; w++) {
                int want = 0;
                for (long x : oracle) {
                    want += x < w ? 1 : 0;
                }
                assertThat(rack.rank(w)).as("seed %d rank %d", seed, w).isEqualTo(want);
            }
        }
    }

    @Test
    void knownRack() {
        BilletRanks r = new BilletRanks(1);
        for (long w : new long[] {5, 3, 8, 3, 1}) {
            r.add(w);
        }
        assertThat(r.kth(0)).isEqualTo(1);
        assertThat(r.kth(2)).isEqualTo(3);
        assertThat(r.rank(4)).isEqualTo(3);
        assertThat(r.remove(3)).isTrue();
        assertThat(r.remove(4)).isFalse();
        assertThat(r.size()).isEqualTo(4);
        assertThatThrownBy(() -> r.kth(4)).isInstanceOf(IndexOutOfBoundsException.class);
        BilletRanks big = new BilletRanks(2);
        for (int i = 0; i < 5000; i++) {
            big.add(i);
        }
        assertThat(big.kth(4321)).isEqualTo(4321);
    }

    @Test
    void gradesLinesAndReplay() {
        BilletRanks r = new BilletRanks(3);
        r.add(10);
        r.add(20);
        assertThat(r.grade(1, 20)).isEqualTo(Grade.RACKED);
        assertThat(r.grade(0, 20)).isEqualTo(Grade.JUMBLED);
        assertThat(r.grade(5, 20)).isEqualTo(Grade.JUMBLED);
        for (Grade g : Grade.values()) {
            assertThat(BilletRanks.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(BilletRanks.QUEST_ID).isEqualTo("q_billet_ranks");
        assertThat(BilletRanks.script(4, 9, 7)).containsExactly(BilletRanks.script(4, 9, 7));
        assertThatThrownBy(() -> BilletRanks.script(1, 3, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
