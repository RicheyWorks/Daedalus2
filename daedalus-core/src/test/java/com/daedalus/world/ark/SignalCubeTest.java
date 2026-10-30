// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class SignalCubeTest {

    private static int[] power(String turns, int times) {
        int[] s = SignalCube.solvedState();
        for (int i = 0; i < times; i++) {
            s = SignalCube.apply(s, turns);
        }
        return s;
    }

    private static int order(String turns) {
        int[] s = SignalCube.apply(SignalCube.solvedState(), turns);
        int k = 1;
        while (!SignalCube.solved(s)) {
            s = SignalCube.apply(s, turns);
            k++;
        }
        return k;
    }

    private static boolean reach(int[] s, int d) {
        if (SignalCube.solved(s)) {
            return true;
        }
        if (d == 0) {
            return false;
        }
        for (String t : SignalCube.turns()) {
            if (reach(SignalCube.apply(s, t), d - 1)) {
                return true;
            }
        }
        return false;
    }

    @Test
    void turnOrders() {
        for (String t : new String[] {"R", "U", "F"}) {
            assertThat(order(t)).isEqualTo(4);
            assertThat(SignalCube.apply(SignalCube.apply(SignalCube.solvedState(), t), t + "'"))
                    .isEqualTo(SignalCube.solvedState());
            assertThat(SignalCube.apply(SignalCube.solvedState(), t + " " + t))
                    .isEqualTo(SignalCube.apply(SignalCube.solvedState(), t + "2"));
        }
        assertThat(order("R U R' U'")).isEqualTo(6);
        assertThat(SignalCube.solved(power("R U", 105))).isTrue();
        assertThat(order("R U")).isEqualTo(15);
    }

    @Test
    void distancesMatchIterativeDeepening() {
        SplittableRandom rnd = new SplittableRandom(435);
        for (int t = 0; t < 60; t++) {
            StringBuilder sb = new StringBuilder();
            int len = rnd.nextInt(5);
            for (int i = 0; i < len; i++) {
                sb.append(SignalCube.turns().get(rnd.nextInt(9))).append(' ');
            }
            int[] s = SignalCube.apply(SignalCube.solvedState(), sb.toString());
            int d = 0;
            while (!reach(s, d)) {
                d++;
            }
            assertThat(SignalCube.distance(s, false)).as(sb.toString()).isEqualTo(d);
        }
    }

    @Test
    void solvesReplay() {
        SplittableRandom rnd = new SplittableRandom(4350);
        for (int t = 0; t < 100; t++) {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < 25; i++) {
                sb.append(SignalCube.turns().get(rnd.nextInt(9))).append(' ');
            }
            int[] s = SignalCube.apply(SignalCube.solvedState(), sb.toString());
            String sol = SignalCube.solve(s);
            assertThat(SignalCube.solved(SignalCube.apply(s, sol))).isTrue();
            int n = sol.isEmpty() ? 0 : sol.split(" ").length;
            assertThat(n).isEqualTo(SignalCube.distance(s, false));
            assertThat(SignalCube.distance(s, true)).isGreaterThanOrEqualTo(n);
        }
    }

    @Test
    void countAndGodsNumbers() {
        assertThat(SignalCube.stateCount()).isEqualTo(3_674_160);
        assertThat(SignalCube.godsNumber(false)).isEqualTo(11);
        assertThat(SignalCube.godsNumber(true)).isEqualTo(14);
    }

    @Test
    void questAndBounds() {
        assertThat(SignalCube.quest("R U", 2)).isTrue();
        assertThat(SignalCube.quest("R U", 1)).isFalse();
        assertThat(SignalCube.quest("", 0)).isTrue();
        assertThat(SignalCube.QUEST_ID).isEqualTo("q_signal_cube");
        assertThatThrownBy(() -> SignalCube.apply(SignalCube.solvedState(), "L")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SignalCube.apply(new int[3], "R")).isInstanceOf(IllegalArgumentException.class);
        int[] twisted = SignalCube.solvedState();
        twisted[7] = 1;
        assertThatThrownBy(() -> SignalCube.distance(twisted, false)).isInstanceOf(IllegalArgumentException.class);
    }
}