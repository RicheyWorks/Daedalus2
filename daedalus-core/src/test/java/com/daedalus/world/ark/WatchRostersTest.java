// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;

class WatchRostersTest {

    private static List<int[]> allRosters(int n) {
        List<int[]> out = new ArrayList<>();
        int total = 1;
        for (int i = 0; i < n; i++) {
            total *= n;
        }
        for (int code = 0; code < total; code++) {
            int[] a = new int[n];
            int c = code;
            for (int i = n - 1; i >= 0; i--) {
                a[i] = c % n;
                c /= n;
            }
            if (WatchRosters.isRoster(a)) {
                out.add(a);
            }
        }
        return out;
    }

    private static int cycles(int[] p) {
        boolean[] seen = new boolean[p.length];
        int c = 0;
        for (int i = 0; i < p.length; i++) {
            if (!seen[i]) {
                c++;
                for (int j = i; !seen[j]; j = p[j]) {
                    seen[j] = true;
                }
            }
        }
        return c;
    }

    private static void perms(int[] p, int k, long[] byCycles) {
        if (k == p.length) {
            byCycles[cycles(p)]++;
            return;
        }
        for (int i = k; i < p.length; i++) {
            int t = p[k];
            p[k] = p[i];
            p[i] = t;
            perms(p, k + 1, byCycles);
            t = p[k];
            p[k] = p[i];
            p[i] = t;
        }
    }

    @Test
    void countsRankUnrankMatchBruteForce() {
        for (int n = 1; n <= 7; n++) {
            List<int[]> all = allRosters(n);
            assertThat(WatchRosters.bell(n)).isEqualTo(BigInteger.valueOf(all.size()));
            long[] byK = new long[n + 1];
            for (int r = 0; r < all.size(); r++) {
                int[] a = all.get(r);
                byK[Arrays.stream(a).max().getAsInt() + 1]++;
                assertThat(WatchRosters.rank(a)).as("n=%d %s", n, Arrays.toString(a)).isEqualTo(BigInteger.valueOf(r));
                assertThat(WatchRosters.unrank(n, BigInteger.valueOf(r))).isEqualTo(a);
            }
            for (int k = 0; k <= n; k++) {
                assertThat(WatchRosters.stirling2(n, k)).isEqualTo(BigInteger.valueOf(byK[k]));
            }
            int[] p = new int[n];
            for (int i = 0; i < n; i++) {
                p[i] = i;
            }
            long[] byCycles = new long[n + 1];
            perms(p, 0, byCycles);
            for (int k = 0; k <= n; k++) {
                assertThat(WatchRosters.stirling1(n, k)).isEqualTo(BigInteger.valueOf(byCycles[k]));
            }
        }
        assertThat(WatchRosters.bell(20)).isEqualTo(BigInteger.valueOf(51_724_158_235_372L));
        assertThat(WatchRosters.bell(0)).isEqualTo(BigInteger.ONE);
    }

    @Test
    void largeRoundTrip() {
        BigInteger total = WatchRosters.bell(60);
        BigInteger step = total.divide(BigInteger.valueOf(37));
        for (int t = 0; t < 37; t++) {
            BigInteger k = step.multiply(BigInteger.valueOf(t)).add(BigInteger.valueOf(t));
            int[] a = WatchRosters.unrank(60, k);
            assertThat(WatchRosters.isRoster(a)).isTrue();
            assertThat(WatchRosters.rank(a)).isEqualTo(k);
        }
        assertThat(WatchRosters.rank(WatchRosters.unrank(60, total.subtract(BigInteger.ONE)))).isEqualTo(total.subtract(BigInteger.ONE));
    }

    @Test
    void questAndBounds() {
        assertThat(WatchRosters.quest(4, 2, new int[] {0, 1, 0, 1})).isTrue();
        assertThat(WatchRosters.quest(4, 3, new int[] {0, 1, 0, 1})).isFalse();
        assertThat(WatchRosters.quest(4, 2, new int[] {0, 2, 0, 1})).isFalse();
        assertThat(WatchRosters.quest(3, 2, new int[] {0, 1, 0, 1})).isFalse();
        assertThat(WatchRosters.QUEST_ID).isEqualTo("q_watch_rosters");
        assertThatThrownBy(() -> WatchRosters.rank(new int[] {1})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> WatchRosters.unrank(3, BigInteger.valueOf(5))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> WatchRosters.bell(-1)).isInstanceOf(IllegalArgumentException.class);
    }
}