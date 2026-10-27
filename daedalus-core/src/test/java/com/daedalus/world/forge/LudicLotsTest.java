// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class LudicLotsTest {

    private static List<Integer> brute(int n) {
        List<Integer> out = new ArrayList<>();
        if (n < 1) {
            return out;
        }
        out.add(1);
        List<Integer> line = new ArrayList<>();
        for (int i = 2; i <= n; i++) {
            line.add(i);
        }
        while (!line.isEmpty()) {
            int x = line.get(0);
            out.add(x);
            List<Integer> keep = new ArrayList<>();
            for (int i = 0; i < line.size(); i++) {
                if (i % x != 0) {
                    keep.add(line.get(i));
                }
            }
            line = keep;
        }
        return out;
    }

    private static List<Integer> boxed(int[] a) {
        List<Integer> l = new ArrayList<>();
        for (int v : a) {
            l.add(v);
        }
        return l;
    }

    @Test
    void matchesListRemovalBruteForce() {
        List<Integer> want = brute(5000);
        assertThat(boxed(LudicLots.ludicUpTo(5000))).isEqualTo(want);
        for (int n = 0; n <= 400; n++) {
            assertThat(boxed(LudicLots.ludicUpTo(n))).as("n=%d", n).isEqualTo(brute(n));
        }
        Random r = new Random(485);
        for (int t = 0; t < 30; t++) {
            int n = 1 + r.nextInt(5000);
            List<Integer> pre = new ArrayList<>();
            for (int v : want) {
                if (v <= n) {
                    pre.add(v);
                }
            }
            assertThat(boxed(LudicLots.ludicUpTo(n))).as("n=%d", n).isEqualTo(pre);
        }
        for (int v = 1; v <= 5000; v++) {
            assertThat(LudicLots.isLudic(v)).as("v=%d", v).isEqualTo(want.contains(v));
        }
    }

    @Test
    void knownLudicLots() {
        assertThat(LudicLots.ludicUpTo(107)).containsExactly(1, 2, 3, 5, 7, 11, 13, 17, 23, 25, 29, 37, 41, 43, 47,
                53, 61, 67, 71, 77, 83, 89, 91, 97, 107);
        assertThat(LudicLots.ludicUpTo(1000)).hasSize(142);
        List<String> t = new ArrayList<>();
        for (int[] x : LudicLots.triplets(250)) {
            t.add(x[0] + "," + x[1] + "," + x[2]);
        }
        assertThat(t).containsExactly("1,3,7", "5,7,11", "11,13,17", "23,25,29", "41,43,47", "173,175,179",
                "221,223,227", "233,235,239");
    }

    @Test
    void fullLineIsConsistent() {
        int[] all = LudicLots.ludicUpTo(LudicLots.MAX_N);
        for (int i = 1; i < all.length; i++) {
            assertThat(all[i]).isGreaterThan(all[i - 1]);
        }
        int[] half = LudicLots.ludicUpTo(LudicLots.MAX_N / 2);
        for (int i = 0; i < half.length; i++) {
            assertThat(half[i]).isEqualTo(all[i]);
        }
        int count = 0;
        for (int v = 1; v <= LudicLots.MAX_N; v++) {
            count += LudicLots.isLudic(v) ? 1 : 0;
        }
        assertThat(count).isEqualTo(all.length);
        for (int[] x : LudicLots.triplets(LudicLots.MAX_N)) {
            assertThat(LudicLots.isLudic(x[0]) && LudicLots.isLudic(x[1]) && LudicLots.isLudic(x[2])).isTrue();
        }
    }

    @Test
    void edgesAndGuards() {
        assertThat(LudicLots.ludicUpTo(0)).isEmpty();
        assertThat(LudicLots.ludicUpTo(1)).containsExactly(1);
        assertThat(LudicLots.ludicUpTo(2)).containsExactly(1, 2);
        assertThat(LudicLots.triplets(6)).isEmpty();
        assertThat(LudicLots.triplets(7)).hasSize(1);
        assertThat(LudicLots.isLudic(4)).isFalse();
        assertThatThrownBy(() -> LudicLots.ludicUpTo(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LudicLots.ludicUpTo(LudicLots.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LudicLots.isLudic(0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(LudicLots.grade(25, true)).isEqualTo(LudicLots.Grade.TURNED);
        assertThat(LudicLots.grade(19, true)).isEqualTo(LudicLots.Grade.SLIPPED);
        assertThat(LudicLots.grade(19, false)).isEqualTo(LudicLots.Grade.TURNED);
        for (LudicLots.Grade g : LudicLots.Grade.values()) {
            assertThat(LudicLots.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(LudicLots.QUEST_ID).isEqualTo("q_ludic_lots");
    }
}
