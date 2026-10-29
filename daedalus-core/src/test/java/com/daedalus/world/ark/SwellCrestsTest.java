// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class SwellCrestsTest {

    private static int bruteCrest(long[] h, int a, int b) {
        int m = a;
        for (int i = a + 1; i <= b; i++) {
            if (h[i] > h[m]) {
                m = i;
            }
        }
        return m;
    }

    @Test
    void smallChartByHand() {
        long[] h = {3, 1, 4, 1, 5, 9, 2, 6};
        SwellCrests s = new SwellCrests(h);
        assertThat(s.root()).isEqualTo(5);
        assertThat(s.parent(5)).isEqualTo(-1);
        assertThat(s.leftChild(5)).isEqualTo(4);
        assertThat(s.rightChild(5)).isEqualTo(7);
        assertThat(s.crest(0, 3)).isEqualTo(2);
        assertThat(s.quest(6, 7)).isEqualTo(7);
        assertThat(s.reignFrom(2)).isZero();
        assertThat(s.reignTo(2)).isEqualTo(3);
        assertThat(s.windowsRuled(5)).isEqualTo(6L * 3);
    }

    @Test
    void randomChartsMatchBruteForce() {
        SplittableRandom r = new SplittableRandom(527L);
        for (int round = 0; round < 200; round++) {
            int n = 1 + r.nextInt(40);
            long[] h = new long[n];
            for (int i = 0; i < n; i++) {
                h[i] = r.nextInt(6);
            }
            SwellCrests s = new SwellCrests(h);
            long[] ruled = new long[n];
            for (int a = 0; a < n; a++) {
                for (int b = a; b < n; b++) {
                    int m = bruteCrest(h, a, b);
                    assertThat(s.crest(a, b)).isEqualTo(m);
                    ruled[m]++;
                }
            }
            for (int i = 0; i < n; i++) {
                assertThat(s.windowsRuled(i)).isEqualTo(ruled[i]);
                assertThat(bruteCrest(h, s.reignFrom(i), s.reignTo(i))).isEqualTo(i);
                int p = s.parent(i);
                if (p >= 0) {
                    assertThat(s.leftChild(p) == i || s.rightChild(p) == i).isTrue();
                }
            }
        }
    }

    @Test
    void longChartsStayFast() {
        int n = SwellCrests.MAX_WAVES;
        long[] up = new long[n];
        long[] down = new long[n];
        for (int i = 0; i < n; i++) {
            up[i] = i;
            down[i] = n - i;
        }
        SwellCrests a = new SwellCrests(up);
        assertThat(a.root()).isEqualTo(n - 1);
        assertThat(a.crest(0, 12_345)).isEqualTo(12_345);
        SwellCrests b = new SwellCrests(down);
        assertThat(b.root()).isZero();
        assertThat(b.crest(1000, n - 1)).isEqualTo(1000);
        assertThat(b.windowsRuled(0)).isEqualTo(n);
    }

    @Test
    void badInputIsRejected() {
        assertThatThrownBy(() -> new SwellCrests(new long[0])).isInstanceOf(IllegalArgumentException.class);
        SwellCrests s = new SwellCrests(new long[] {7, 7});
        assertThat(s.root()).isZero();
        assertThat(s.crest(0, 1)).isZero();
        assertThatThrownBy(() -> s.crest(1, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> s.parent(2)).isInstanceOf(IllegalArgumentException.class);
    }
}
