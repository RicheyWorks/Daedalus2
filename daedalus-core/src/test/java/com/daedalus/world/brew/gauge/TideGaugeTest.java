// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.gauge;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.gauge.TideGauge.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class TideGaugeTest {
    /** Brute force: scan the hours. */
    static int brute(List<Integer> l, int a, int b) {
        int m = Integer.MAX_VALUE;
        for (int i = a; i <= b; i++) {
            m = Math.min(m, l.get(i));
        }
        return m;
    }

    /** Levels 6, 4, 5, 1, 3, 7, 0 and a trip from hour 1 to 5: the ends read 4 and 7, but hour 3 drops to 1. */
    static TideGauge log() {
        return new TideGauge(List.of(6, 4, 5, 1, 3, 7, 0), 1, 5);
    }

    @Test
    void seededLogIsDeterministic() {
        assertEquals(TideGauge.seeded(3).levels(), TideGauge.seeded(3).levels());
        assertEquals(TideGauge.seeded(3).from(), TideGauge.seeded(3).from());
        assertThrows(IllegalArgumentException.class, () -> new TideGauge(List.of(1, 2), 1, 0));
        assertThrows(IllegalArgumentException.class, () -> new TideGauge(List.of(1, 2), 0, 2));
        assertThrows(IllegalArgumentException.class, () -> log().low(3, 7));
    }

    @Test
    void everyRangeMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            TideGauge g = TideGauge.seeded(seed);
            for (int a = 0; a < g.hours(); a++) {
                for (int b = a; b < g.hours(); b++) {
                    assertEquals(brute(g.levels(), a, b), g.low(a, b), "sparse table == scan, seed " + seed);
                }
            }
        }
    }

    @Test
    void endsAreATrap() {
        TideGauge g = log();
        assertEquals(1, g.low(1, 5));
        assertEquals(0, g.low(0, 6), "the 0 is after the boat is home");
        assertEquals(Outcome.WRONG, g.name("n0", 0));
        assertEquals(String.format(KeeperGaugeLines.WRONG, 0, 1), g.talk("t0"));
    }

    @Test
    void wrongEarnsNoCredit() {
        TideGauge g = log();
        g.read("r");
        assertEquals(Outcome.WRONG, g.name("n1", 4));
        assertEquals("name", g.quest().currentStep().type(), "no credit for a wrong low");
    }

    @Test
    void guards() {
        TideGauge g = log();
        assertEquals(Outcome.IGNORED, g.name("", 1));
        assertEquals(Outcome.RIGHT, g.name("e1", 1));
        assertEquals(Outcome.DUPLICATE, g.name("e1", 1));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        TideGauge g = log();
        assertEquals(String.format(KeeperGaugeLines.GREETING, 7, 1, 5), g.talk("t0"));
        g.read("r0");
        assertEquals(Outcome.WRONG, g.name("n1", 4));
        assertEquals(Outcome.RIGHT, g.name("n2", 1));
        assertEquals(KeeperGaugeLines.THANKS, g.talk("t2"));
        assertNull(g.quest().currentStep());
        assertEquals(KeeperGaugeLines.DONE, g.talk("t3"));
    }
}
