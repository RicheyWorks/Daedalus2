// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.scales;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.scales.TreasureScales.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class TreasureScalesTest {
    /** Brute force: every subset by bitmask. */
    static long brute(TreasureScales s) {
        int n = s.weights().size();
        long best = 0;
        for (int m = 0; m < 1 << n; m++) {
            long sum = 0;
            for (int i = 0; i < n; i++) {
                if ((m >> i & 1) == 1) {
                    sum += s.weights().get(i);
                }
            }
            if (sum <= s.cap()) {
                best = Math.max(best, sum);
            }
        }
        return best;
    }

    /** Weights 8, 6, 5, 5 and cap 10: heaviest first takes 8 and stops; 5 + 5 makes 10. */
    static TreasureScales hoard() {
        return new TreasureScales(List.of(8, 6, 5, 5), 10);
    }

    @Test
    void seededHoardIsDeterministic() {
        assertEquals(TreasureScales.seeded(4).weights(), TreasureScales.seeded(4).weights());
        assertEquals(TreasureScales.seeded(4).cap(), TreasureScales.seeded(4).cap());
        assertThrows(IllegalArgumentException.class, () -> new TreasureScales(List.of(), 3));
        assertThrows(IllegalArgumentException.class, () -> new TreasureScales(List.of(0), 3));
    }

    @Test
    void bestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            TreasureScales s = TreasureScales.seeded(seed);
            assertEquals(brute(s), s.best(), "meet-in-the-middle == brute force, seed " + seed);
        }
        assertEquals(0, new TreasureScales(List.of(4), 3).best(), "nothing fits");
    }

    @Test
    void heaviestFirstIsLight() {
        TreasureScales s = hoard();
        assertEquals(10, s.best());
        assertEquals(Outcome.LIGHT, s.load("l0", List.of(0)));
        assertEquals(String.format(KeeperScaleLines.LIGHT, 8, 10), s.talk("t0"));
    }

    @Test
    void overAndMalformedEarnNoCredit() {
        TreasureScales s = hoard();
        s.weigh("w");
        assertEquals(Outcome.OVER, s.load("l1", List.of(0, 1)));
        assertEquals(String.format(KeeperScaleLines.OVER, 14, 10), s.talk("t1"));
        assertEquals(Outcome.MALFORMED, s.load("l2", List.of(2, 2)));
        assertEquals("load", s.quest().currentStep().type(), "no credit for an over or bad load");
    }

    @Test
    void guards() {
        TreasureScales s = hoard();
        assertEquals(Outcome.IGNORED, s.load("", List.of(2, 3)));
        assertEquals(Outcome.IGNORED, s.load("e", null));
        assertEquals(Outcome.MALFORMED, s.load("e0", List.of(4)));
        assertEquals(Outcome.BEST, s.load("e1", List.of(2, 3)));
        assertEquals(Outcome.DUPLICATE, s.load("e1", List.of(2, 3)));
    }

    @Test
    void questLightThenBestThenKeeper() {
        TreasureScales s = hoard();
        assertEquals(String.format(KeeperScaleLines.GREETING, 4, 10, 10), s.talk("t0"));
        s.weigh("w0");
        assertEquals(Outcome.LIGHT, s.load("l1", List.of(0)));
        assertEquals(Outcome.BEST, s.load("l2", List.of(3, 2)));
        assertEquals(KeeperScaleLines.THANKS, s.talk("t2"));
        assertNull(s.quest().currentStep());
        assertEquals(KeeperScaleLines.DONE, s.talk("t3"));
    }
}
