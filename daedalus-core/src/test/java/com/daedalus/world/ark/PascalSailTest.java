// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import org.junit.jupiter.api.Test;

class PascalSailTest {

    private static BigInteger[][] triangle(int n) {
        BigInteger[][] c = new BigInteger[n + 1][];
        for (int i = 0; i <= n; i++) {
            c[i] = new BigInteger[i + 1];
            c[i][0] = BigInteger.ONE;
            c[i][i] = BigInteger.ONE;
            for (int j = 1; j < i; j++) {
                c[i][j] = c[i - 1][j - 1].add(c[i - 1][j]);
            }
        }
        return c;
    }

    @Test
    void lucasAndKummerMatchExact() {
        BigInteger[][] c = triangle(160);
        for (int p : new int[] {2, 3, 5, 7, 13, 101}) {
            BigInteger bp = BigInteger.valueOf(p);
            for (int n = 0; n <= 160; n++) {
                for (int k = 0; k <= n; k++) {
                    assertThat(PascalSail.binomMod(n, k, p)).as("n=%d k=%d p=%d", n, k, p)
                            .isEqualTo(c[n][k].mod(bp).intValue());
                    int v = 0;
                    BigInteger x = c[n][k];
                    while (x.mod(bp).signum() == 0) {
                        x = x.divide(bp);
                        v++;
                    }
                    assertThat(PascalSail.pPower(n, k, p)).isEqualTo(v);
                }
            }
        }
    }

    @Test
    void oddCellsAndLargeRows() {
        BigInteger[][] c = triangle(200);
        for (int n = 0; n <= 200; n++) {
            long odd = 0;
            for (int k = 0; k <= n; k++) {
                if (c[n][k].testBit(0)) {
                    odd++;
                }
            }
            assertThat(PascalSail.oddCells(n)).isEqualTo(odd);
        }
        BigInteger big = BigInteger.ONE;
        for (int i = 0; i < 500; i++) {
            big = big.multiply(BigInteger.valueOf(1000L - i)).divide(BigInteger.valueOf(i + 1L));
        }
        assertThat(PascalSail.binomMod(1000, 500, 1_000_003)).isEqualTo(big.mod(BigInteger.valueOf(1_000_003)).intValue());
        assertThat(PascalSail.binomMod(Long.MAX_VALUE, 1L << 40, 2)).isEqualTo(1);
        assertThat(PascalSail.binomMod((1L << 39) - 1, 1L << 38, 2)).isEqualTo(1);
        assertThat(PascalSail.binomMod((1L << 40) - 1 - (1L << 39), 1L << 39, 2)).isZero();
    }

    @Test
    void questAndBounds() {
        assertThat(PascalSail.quest(10, 3, 7, 1)).isTrue();
        assertThat(PascalSail.quest(10, 3, 7, 3)).isFalse();
        assertThat(PascalSail.binomMod(5, 7, 3)).isZero();
        assertThat(PascalSail.QUEST_ID).isEqualTo("q_pascal_sail");
        assertThatThrownBy(() -> PascalSail.binomMod(5, 2, 4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PascalSail.pPower(5, 6, 3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PascalSail.oddCells(-1)).isInstanceOf(IllegalArgumentException.class);
    }
}