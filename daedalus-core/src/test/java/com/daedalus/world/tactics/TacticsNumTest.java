// SPDX-License-Identifier: MIT

package com.daedalus.world.tactics;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.Random;
import org.junit.jupiter.api.Test;

/** The fast %.1f path writes the same bytes as the exact BigDecimal path (C's printf), ties and signs included. */
class TacticsNumTest {

    @Test
    void fastPathMatchesTheExactOneOnAMillionValues() {
        Random r = new Random(64);
        for (int i = 0; i < 1_000_000; i++) {
            double w = (r.nextDouble() * 4e6) - 2e6;
            double v = switch (i % 5) {
                case 0 -> Math.rint(w * 4) / 4;          // exact quarter ties (x.25, x.75)
                case 1 -> Math.rint(w * 20) / 20;        // x.x5: near-ties in binary
                case 2 -> Math.rint(w * 10) / 10 + (r.nextBoolean() ? 1e-9 : -1e-9);
                case 3 -> w * 1e3;                       // up to 2e9: past the fast path's 1e9 limit
                default -> w;
            };
            assertEquals(TacticalOrders.slowNum(v), TacticalOrders.num(v), "value " + v);
        }
    }

    @Test
    void edgeValues() {
        for (double v : new double[] {0.0, -0.0, -0.04, 0.05, -0.05, 0.15, 0.25, -0.25, 0.35, 2.5e-7, 999_999_999.95,
            1e9, -1e9 - 0.25, 1e15 + 0.25, 1e300, Double.MIN_VALUE, -Double.MIN_VALUE}) {
            assertEquals(TacticalOrders.slowNum(v), TacticalOrders.num(v), "value " + v);
        }
        assertEquals("-0.0", TacticalOrders.num(-0.04));
        assertEquals("0.2", TacticalOrders.num(0.25));
        assertEquals("-0.2", TacticalOrders.num(-0.25));
    }
}
