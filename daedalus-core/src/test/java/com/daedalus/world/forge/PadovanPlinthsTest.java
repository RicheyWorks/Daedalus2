// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class PadovanPlinthsTest {

    private static List<BigInteger> brute(int len) {
        List<BigInteger> p = new ArrayList<>();
        for (int i = 0; i < len; i++) {
            p.add(i < 3 ? BigInteger.ONE : p.get(i - 2).add(p.get(i - 3)));
        }
        return p;
    }

    @Test
    void matchesBigIntegerAndStopsAtOverflow() {
        List<BigInteger> b = brute(PadovanPlinths.MAX_INDEX + 2);
        for (int n = 0; n <= PadovanPlinths.MAX_INDEX; n++) {
            assertThat(BigInteger.valueOf(PadovanPlinths.padovan(n))).as("%d", n).isEqualTo(b.get(n));
        }
        assertThat(b.get(PadovanPlinths.MAX_INDEX + 1).bitLength()).isGreaterThan(63);
        assertThat(PadovanPlinths.MAX_INDEX).isGreaterThan(140);
    }

    @Test
    void knownSidesAndIdentities() {
        long[] want = {1, 1, 1, 2, 2, 3, 4, 5, 7, 9, 12, 16, 21, 28, 37, 49, 65, 86, 114, 151};
        for (int i = 0; i < want.length; i++) {
            assertThat(PadovanPlinths.padovan(i)).isEqualTo(want[i]);
        }
        for (int n = 5; n <= PadovanPlinths.MAX_INDEX; n++) {
            assertThat(PadovanPlinths.padovan(n))
                    .isEqualTo(PadovanPlinths.padovan(n - 1) + PadovanPlinths.padovan(n - 5));
        }
        for (int n = 0; n + 5 <= PadovanPlinths.MAX_INDEX; n++) {
            assertThat(PadovanPlinths.runSum(0, n)).isEqualTo(PadovanPlinths.padovan(n + 5) - 2);
        }
    }

    @Test
    void membershipMatchesScan() {
        for (long v = -3; v <= 5000; v++) {
            int want = -1;
            for (int n = 0; n <= PadovanPlinths.MAX_INDEX; n++) {
                if (PadovanPlinths.padovan(n) == v) {
                    want = n;
                    break;
                }
            }
            assertThat(PadovanPlinths.indexOf(v)).as("%d", v).isEqualTo(want);
            assertThat(PadovanPlinths.isPadovan(v)).isEqualTo(want >= 0);
        }
        assertThat(PadovanPlinths.indexOf(1)).isZero();
        assertThat(PadovanPlinths.indexOf(2)).isEqualTo(3);
        assertThat(PadovanPlinths.indexOf(PadovanPlinths.padovan(PadovanPlinths.MAX_INDEX)))
                .isEqualTo(PadovanPlinths.MAX_INDEX);
    }

    @Test
    void randomSweeps() {
        Random r = new Random(526);
        for (int t = 0; t < 2000; t++) {
            int n = 10 + r.nextInt(PadovanPlinths.MAX_INDEX - 10);
            long v = PadovanPlinths.padovan(n);
            assertThat(PadovanPlinths.indexOf(v)).isEqualTo(n);
            assertThat(PadovanPlinths.isPadovan(v + 1)).isFalse();
            int a = r.nextInt(n);
            long s = 0;
            for (int i = a; i <= n; i++) {
                s += PadovanPlinths.padovan(i);
            }
            if (n + 5 <= PadovanPlinths.MAX_INDEX) {
                assertThat(PadovanPlinths.runSum(a, n)).isEqualTo(s);
            }
        }
    }

    @Test
    void edgesGuardsAndGrades() {
        assertThat(PadovanPlinths.runSum(4, 4)).isEqualTo(2);
        assertThat(PadovanPlinths.isPadovan(0)).isFalse();
        assertThat(PadovanPlinths.isPadovan(Long.MAX_VALUE)).isFalse();
        assertThatThrownBy(() -> PadovanPlinths.padovan(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PadovanPlinths.padovan(PadovanPlinths.MAX_INDEX + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PadovanPlinths.runSum(5, 4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PadovanPlinths.runSum(0, PadovanPlinths.MAX_INDEX))
                .isInstanceOf(ArithmeticException.class);
        assertThat(PadovanPlinths.grade(10, 12)).isEqualTo(PadovanPlinths.Grade.TURNED);
        assertThat(PadovanPlinths.grade(10, 13)).isEqualTo(PadovanPlinths.Grade.SLIPPED);
        for (PadovanPlinths.Grade g : PadovanPlinths.Grade.values()) {
            assertThat(PadovanPlinths.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(PadovanPlinths.QUEST_ID).isEqualTo("q_padovan_plinths");
    }
}
