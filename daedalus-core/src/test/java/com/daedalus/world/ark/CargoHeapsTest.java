// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class CargoHeapsTest {

    @Test
    void smallHandRun() {
        CargoHeaps f = new CargoHeaps(2);
        f.add(0, 5);
        f.add(0, 2);
        f.add(1, 3);
        f.pour(0, 1);
        assertThat(f.size(0)).isEqualTo(3);
        assertThat(f.size(1)).isZero();
        assertThat(f.take(0)).isEqualTo(2);
        assertThat(f.take(0)).isEqualTo(3);
        assertThat(f.lightest(0)).isEqualTo(5);
        long[][] ops = {{0, 0, 7}, {0, 1, 4}, {2, 0, 1}, {1, 0, 0}, {1, 1, 0}};
        assertThat(CargoHeaps.quest(2, ops, 4)).isTrue();
        assertThat(CargoHeaps.quest(2, ops, 7)).isFalse();
    }

    @Test
    void randomOpsMatchSortedListBruteForce() {
        SplittableRandom r = new SplittableRandom(464);
        for (int it = 0; it < 200; it++) {
            int k = 1 + r.nextInt(5);
            CargoHeaps f = new CargoHeaps(k);
            List<List<Long>> b = new ArrayList<>();
            for (int i = 0; i < k; i++) {
                b.add(new ArrayList<>());
            }
            for (int s = 0; s < 300; s++) {
                int h = r.nextInt(k);
                int op = r.nextInt(4);
                if (op <= 1) {
                    long w = r.nextLong(-50, 50);
                    f.add(h, w);
                    b.get(h).add(w);
                } else if (op == 2 && !b.get(h).isEmpty()) {
                    long m = Collections.min(b.get(h));
                    assertThat(f.take(h)).isEqualTo(m);
                    b.get(h).remove(Long.valueOf(m));
                } else if (op == 3) {
                    int g = r.nextInt(k);
                    f.pour(h, g);
                    if (g != h) {
                        b.get(h).addAll(b.get(g));
                        b.get(g).clear();
                    }
                }
                assertThat(f.size(h)).isEqualTo(b.get(h).size());
                if (!b.get(h).isEmpty()) {
                    assertThat(f.lightest(h)).isEqualTo(Collections.min(b.get(h)));
                }
            }
        }
    }

    @Test
    void largestFleetDrainsSorted() {
        SplittableRandom r = new SplittableRandom(7);
        CargoHeaps f = new CargoHeaps(100);
        for (int i = 0; i < CargoHeaps.MAX_CRATES; i++) {
            f.add(i % 100, r.nextLong());
        }
        for (int h = 1; h < 100; h++) {
            f.pour(0, h);
        }
        long prev = Long.MIN_VALUE;
        for (int i = 0; i < CargoHeaps.MAX_CRATES; i++) {
            long w = f.take(0);
            assertThat(w).isGreaterThanOrEqualTo(prev);
            prev = w;
        }
        assertThatThrownBy(() -> f.add(0, 1)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void emptyHoldsAreGuarded() {
        CargoHeaps f = new CargoHeaps(1);
        assertThatThrownBy(() -> f.take(0)).isInstanceOf(IllegalStateException.class);
        assertThat(CargoHeaps.run(1, new long[][] {{1, 0, 0}})).isZero();
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new CargoHeaps(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CargoHeaps(2).add(2, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CargoHeaps.run(2, new long[][] {{9, 0, 0}}))
            .isInstanceOf(IllegalArgumentException.class);
    }
}