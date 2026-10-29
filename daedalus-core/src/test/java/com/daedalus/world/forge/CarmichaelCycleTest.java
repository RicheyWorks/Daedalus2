// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class CarmichaelCycleTest {

    private static long gcd(long a, long b) {
        return b == 0 ? a : gcd(b, a % b);
    }

    private static long bruteOrder(long a, long n) {
        long x = a % n;
        long k = 1;
        while (x != 1 % n) {
            x = x * a % n;
            k++;
        }
        return k;
    }

    @Test
    void matchesBruteForceOrders() {
        for (long n = 1; n <= 2000; n++) {
            long max = 1;
            for (long a = 1; a < Math.max(2, n); a++) {
                if (gcd(a, n) == 1) {
                    long o = bruteOrder(a, n);
                    max = Math.max(max, o);
                    if (n % 37 == 0 || n < 200) {
                        assertThat(CarmichaelCycle.order(a, n)).isEqualTo(o);
                    }
                }
            }
            assertThat(CarmichaelCycle.lambda(n)).as("n=%d", n).isEqualTo(max);
        }
    }

    @Test
    void carmichaelNumbersMatchFermatSweep() {
        List<Long> found = new ArrayList<>();
        for (long n = 3; n < 20_000; n += 2) {
            boolean composite = false;
            for (long p = 3; p * p <= n; p += 2) {
                if (n % p == 0) {
                    composite = true;
                    break;
                }
            }
            boolean allLiars = composite;
            for (long a = 2; allLiars && a < n; a++) {
                if (gcd(a, n) == 1 && CarmichaelCycle.pow(a, n - 1, n) != 1) {
                    allLiars = false;
                }
            }
            assertThat(CarmichaelCycle.isCarmichael(n)).as("n=%d", n).isEqualTo(allLiars);
            if (allLiars) {
                found.add(n);
            }
        }
        assertThat(found).startsWith(561L, 1105L, 1729L, 2465L, 2821L, 6601L, 8911L);
        assertThat(CarmichaelCycle.isCarmichael(9_999_109_081L)).isTrue();
        assertThat(CarmichaelCycle.lambda(1_000_000_000_000L)).isEqualTo(50_000_000_000L);
    }

    @Test
    void grades() {
        assertThat(CarmichaelCycle.grade(15, 4)).isEqualTo(CarmichaelCycle.Grade.TURNED);
        assertThat(CarmichaelCycle.grade(15, 8)).isEqualTo(CarmichaelCycle.Grade.SLIPPED);
        assertThat(CarmichaelCycle.forgemasterLine(CarmichaelCycle.Grade.TURNED)).contains("Forgemaster");
        assertThat(CarmichaelCycle.forgemasterLine(CarmichaelCycle.Grade.SLIPPED)).contains("slipped");
        assertThat(CarmichaelCycle.QUEST_ID).isEqualTo("q_carmichael_cycle");
    }
}
