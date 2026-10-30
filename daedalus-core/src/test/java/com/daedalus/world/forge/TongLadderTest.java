// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.TongLadder.Grade;
import org.junit.jupiter.api.Test;

import java.util.OptionalLong;
import java.util.TreeMap;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class TongLadderTest {

    private static OptionalLong opt(Long v) {
        return v == null ? OptionalLong.empty() : OptionalLong.of(v);
    }

    @Test
    void matchesTreeMapOnSeededScripts() {
        for (long seed = 0; seed < 120; seed++) {
            TongLadder wall = new TongLadder(seed);
            TreeMap<Long, Long> oracle = new TreeMap<>();
            int max = 1 + (int) (seed % 60);
            long tag = 0;
            for (long op : TongLadder.script(seed, 400, max)) {
                if (op > 0) {
                    wall.put(op, tag);
                    oracle.put(op, tag);
                    tag++;
                } else {
                    assertThat(wall.remove(-op)).isEqualTo(oracle.remove(-op) != null);
                }
                assertThat(wall.size()).isEqualTo(oracle.size());
            }
            for (long k = 0; k <= max + 1; k++) {
                assertThat(wall.get(k)).as("seed %d get %d", seed, k).isEqualTo(opt(oracle.get(k)));
                assertThat(wall.floorKey(k)).as("seed %d floor %d", seed, k).isEqualTo(opt(oracle.floorKey(k)));
                assertThat(wall.ceilingKey(k)).as("seed %d ceil %d", seed, k).isEqualTo(opt(oracle.ceilingKey(k)));
            }
        }
    }

    @Test
    void knownWall() {
        TongLadder w = new TongLadder(1);
        w.put(10, 1);
        w.put(30, 3);
        w.put(20, 2);
        w.put(20, 9);
        assertThat(w.size()).isEqualTo(3);
        assertThat(w.get(20)).hasValue(9);
        assertThat(w.floorKey(25)).hasValue(20);
        assertThat(w.ceilingKey(25)).hasValue(30);
        assertThat(w.ceilingKey(31)).isEmpty();
        assertThat(w.floorKey(9)).isEmpty();
        assertThat(w.remove(20)).isTrue();
        assertThat(w.remove(20)).isFalse();
        for (int i = 0; i < 3000; i++) {
            w.put(i * 2L, i);
        }
        assertThat(w.ceilingKey(1001)).hasValue(1002);
    }

    @Test
    void gradesLinesAndReplay() {
        TongLadder w = new TongLadder(2);
        w.put(5, 0);
        assertThat(w.grade(3, OptionalLong.of(5))).isEqualTo(Grade.HUNG);
        assertThat(w.grade(6, OptionalLong.empty())).isEqualTo(Grade.HUNG);
        assertThat(w.grade(3, OptionalLong.of(3))).isEqualTo(Grade.DROPPED);
        for (Grade g : Grade.values()) {
            assertThat(TongLadder.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(TongLadder.QUEST_ID).isEqualTo("q_tong_ladder");
        assertThat(TongLadder.script(4, 9, 7)).containsExactly(TongLadder.script(4, 9, 7));
        assertThatThrownBy(() -> TongLadder.script(1, 3, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
