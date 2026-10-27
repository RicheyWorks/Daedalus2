// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.TongShuffle.Grade;
import org.junit.jupiter.api.Test;

import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class TongShuffleTest {

    private static boolean nextPerm(int[] a) {
        int i = a.length - 2;
        while (i >= 0 && a[i] >= a[i + 1]) {
            i--;
        }
        if (i < 0) {
            return false;
        }
        int j = a.length - 1;
        while (a[j] <= a[i]) {
            j--;
        }
        int t = a[i];
        a[i] = a[j];
        a[j] = t;
        for (int l = i + 1, r = a.length - 1; l < r; l++, r--) {
            t = a[l];
            a[l] = a[r];
            a[r] = t;
        }
        return true;
    }

    @Test
    void inversionsMatchPairCounting() {
        SplittableRandom r = new SplittableRandom(11);
        for (int s = 0; s < 300; s++) {
            int[] a = new int[s % 50];
            for (int i = 0; i < a.length; i++) {
                a[i] = r.nextInt(1 + s % 7);
            }
            long brute = 0;
            for (int i = 0; i < a.length; i++) {
                for (int j = i + 1; j < a.length; j++) {
                    brute += a[i] > a[j] ? 1 : 0;
                }
            }
            int[] copy = a.clone();
            assertThat(TongShuffle.inversions(a)).as("case %d", s).isEqualTo(brute);
            assertThat(a).isEqualTo(copy);
        }
    }

    @Test
    void rankAndUnrankMatchLexicographicEnumeration() {
        for (int n = 0; n <= 6; n++) {
            int[] p = new int[n];
            for (int i = 0; i < n; i++) {
                p[i] = i;
            }
            long idx = 0;
            do {
                assertThat(TongShuffle.rank(p)).as("n %d", n).isEqualTo(idx);
                assertThat(TongShuffle.unrank(n, idx)).containsExactly(p);
                idx++;
            } while (nextPerm(p));
        }
        for (long seed = 0; seed < 50; seed++) {
            int[] p = TongShuffle.rack(seed, TongShuffle.MAX_RANK_N);
            assertThat(TongShuffle.unrank(p.length, TongShuffle.rank(p))).containsExactly(p);
        }
        int[] last = new int[20];
        for (int i = 0; i < 20; i++) {
            last[i] = 19 - i;
        }
        assertThat(TongShuffle.rank(last)).isEqualTo(2432902008176639999L);
    }

    @Test
    void badInputGradesLinesAndReplay() {
        assertThatThrownBy(() -> TongShuffle.rank(new int[] {0, 0})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TongShuffle.rank(new int[21])).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TongShuffle.unrank(3, 6)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TongShuffle.rack(1, -1)).isInstanceOf(IllegalArgumentException.class);
        int[] p = {2, 0, 1};
        assertThat(TongShuffle.grade(p, 2, 4)).isEqualTo(Grade.TIDY);
        assertThat(TongShuffle.grade(p, 1, 4)).isEqualTo(Grade.TANGLED);
        assertThat(TongShuffle.grade(p, 2, 3)).isEqualTo(Grade.TANGLED);
        for (Grade g : Grade.values()) {
            assertThat(TongShuffle.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(TongShuffle.QUEST_ID).isEqualTo("q_tong_shuffle");
        assertThat(TongShuffle.rack(4, 12)).isEqualTo(TongShuffle.rack(4, 12)).hasSize(12);
    }
}
