// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class BeatCoincidenceTest {
    @Test void matchesBruteForceIncludingNonCoprimePeriods() {
        for (int a = 1; a <= 9; a++) {
            for (int b = 1; b <= 9; b++) {
                for (int oa = 0; oa < a; oa++) {
                    for (int ob = 0; ob < b; ob++) {
                        long brute = -1;
                        for (long t = 1; t <= BeatCoincidence.lcm(a, b); t++) {
                            if (t % a == oa && t % b == ob) {
                                brute = t;
                                break;
                            }
                        }
                        assertThat(BeatCoincidence.next(new int[] {a, b}, new int[] {oa, ob}, 1)).isEqualTo(brute);
                    }
                }
            }
        }
    }

    @Test void threeCyclesAndFrom() {
        int[] p = {3, 4, 5};
        int[] o = {2, 3, 1};
        long t = BeatCoincidence.next(p, o, 0);
        assertThat(t).isEqualTo(11);
        assertThat(BeatCoincidence.next(p, o, 12)).isEqualTo(71);
        assertThat(BeatCoincidence.next(p, o, 11)).isEqualTo(11);
        assertThat(BeatCoincidence.lcm(p)).isEqualTo(60);
    }

    @Test void rejectsBadInput() {
        assertThatThrownBy(() -> BeatCoincidence.lcm(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BeatCoincidence.next(new int[] {2}, new int[] {}, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BeatCoincidence.next(new int[] {}, new int[] {}, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BeatCoincidence.next(new int[] {2}, new int[] {0}, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BeatCoincidence.next(new int[] {2}, new int[] {2}, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}