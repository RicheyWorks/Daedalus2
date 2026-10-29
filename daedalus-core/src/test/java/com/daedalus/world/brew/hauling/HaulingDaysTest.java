// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.hauling;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.hauling.HaulingDays.Outcome;
import org.junit.jupiter.api.Test;

class HaulingDaysTest {
    /** Brute force: every way to cut the line into at most {@code days} runs. */
    static int brute(HaulingDays h) {
        return cut(h, 0, h.days());
    }

    static int cut(HaulingDays h, int from, int daysLeft) {
        if (from == h.sacks()) {
            return 0;
        }
        if (daysLeft == 1) {
            int sum = 0;
            for (int i = from; i < h.sacks(); i++) {
                sum += h.sack(i);
            }
            return sum;
        }
        int best = Integer.MAX_VALUE;
        int sum = 0;
        for (int end = from; end < h.sacks(); end++) {
            sum += h.sack(end);
            best = Math.min(best, Math.max(sum, cut(h, end + 1, daysLeft - 1)));
        }
        return best;
    }

    /** 7, 2, 5, 10, 8 over 2 days: 7+2+5 then 10+8 makes 18. */
    static HaulingDays line() {
        return new HaulingDays(2, 7, 2, 5, 10, 8);
    }

    @Test
    void seededLineIsDeterministic() {
        HaulingDays a = HaulingDays.seeded(2);
        HaulingDays b = HaulingDays.seeded(2);
        assertEquals(a.sacks(), b.sacks());
        assertEquals(a.lightest(), b.lightest());
        assertThrows(IllegalArgumentException.class, () -> new HaulingDays(0, 3));
        assertThrows(IllegalArgumentException.class, () -> new HaulingDays(2, 3, 0));
    }

    @Test
    void lightestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            HaulingDays h = HaulingDays.seeded(seed);
            assertEquals(brute(h), h.lightest(), "binary search == every split, seed " + seed);
        }
    }

    @Test
    void knownLine() {
        assertEquals(18, line().lightest());
        assertEquals(10, new HaulingDays(9, 7, 2, 5, 10, 8).lightest(), "spare days: the biggest sack decides");
    }

    @Test
    void heavyPlanEarnsNoCredit() {
        HaulingDays h = line();
        h.count("c");
        assertEquals(Outcome.HEAVY, h.plan("p1", 0, 0, 1, 1, 1));
        assertEquals(String.format(KeeperHaulLines.HEAVY, 23, 18), h.talk("t1"));
        assertEquals("plan", h.quest().currentStep().type(), "no credit for a heavy plan");
    }

    @Test
    void guards() {
        HaulingDays h = line();
        assertEquals(Outcome.IGNORED, h.plan("", 0, 0, 0, 1, 1));
        assertEquals(Outcome.NOT_THERE, h.plan("e0", 0, 0, 0, 1));
        assertEquals(Outcome.NOT_THERE, h.plan("e0", 0, 1, 0, 1, 1));
        assertEquals(Outcome.NOT_THERE, h.plan("e0", 0, 0, 0, 1, 2));
        assertEquals(Outcome.WELL, h.plan("e1", 0, 0, 0, 1, 1));
        assertEquals(Outcome.DUPLICATE, h.plan("e1", 0, 0, 0, 0, 0));
    }

    @Test
    void questHeavyThenWellThenKeeper() {
        HaulingDays h = line();
        assertEquals(String.format(KeeperHaulLines.GREETING, 5, 2), h.talk("t0"));
        h.count("c0");
        assertEquals(Outcome.HEAVY, h.plan("p1", 0, 0, 0, 0, 1));
        assertEquals(Outcome.WELL, h.plan("p2", 0, 0, 0, 1, 1));
        assertEquals(KeeperHaulLines.THANKS, h.talk("t2"));
        assertNull(h.quest().currentStep());
        assertEquals(KeeperHaulLines.DONE, h.talk("t3"));
    }
}
