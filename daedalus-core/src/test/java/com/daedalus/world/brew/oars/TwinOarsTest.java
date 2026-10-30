// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.oars;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.oars.TwinOars.Outcome;
import org.junit.jupiter.api.Test;

class TwinOarsTest {
    /** Brute force over every pair. */
    static int brute(TwinOars t) {
        int best = -1;
        for (int i = 0; i < t.oars(); i++) {
            for (int j = i + 1; j < t.oars(); j++) {
                int s = t.oar(i) + t.oar(j);
                if (s <= t.span()) {
                    best = Math.max(best, s);
                }
            }
        }
        return best;
    }

    /** 9, 4, 7, 2, 11 for a span of 15: the two longest make 20 (over); 4 + 11 makes 15 exactly. */
    static TwinOars pile() {
        return new TwinOars(15, 9, 4, 7, 2, 11);
    }

    @Test
    void seededPileIsDeterministic() {
        TwinOars a = TwinOars.seeded(5);
        TwinOars b = TwinOars.seeded(5);
        assertEquals(a.oars(), b.oars());
        assertEquals(a.best(), b.best());
        assertThrows(IllegalArgumentException.class, () -> new TwinOars(10, 3));
        assertEquals(-1, new TwinOars(5, 4, 6).best(), "no pair fits");
    }

    @Test
    void bestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            TwinOars t = TwinOars.seeded(seed);
            assertEquals(brute(t), t.best(), "two pointers == every pair, seed " + seed);
        }
    }

    @Test
    void longestPairIsNotBest() {
        TwinOars t = pile();
        assertEquals(15, t.best());
        assertEquals(Outcome.OVER, t.pick("p", 0, 4));
        assertEquals(20, t.picked());
    }

    @Test
    void overSpanEarnsNoCredit() {
        TwinOars t = pile();
        t.sort("s");
        assertEquals(Outcome.OVER, t.pick("p1", 0, 4));
        assertEquals(String.format(KeeperOarLines.OVER, 20), t.talk("t1"));
        assertEquals("pick", t.quest().currentStep().type(), "no credit over the span");
    }

    @Test
    void guards() {
        TwinOars t = pile();
        assertEquals(Outcome.IGNORED, t.pick("", 1, 4));
        assertEquals(Outcome.NOT_THERE, t.pick("e0", 1, 1));
        assertEquals(Outcome.NOT_THERE, t.pick("e0", 1, 5));
        assertEquals(Outcome.SHORT, t.pick("e1", 1, 3));
        assertEquals(Outcome.DUPLICATE, t.pick("e1", 1, 4));
    }

    @Test
    void questShortThenWellThenKeeper() {
        TwinOars t = pile();
        assertEquals(String.format(KeeperOarLines.GREETING, 5, 15), t.talk("t0"));
        t.sort("s0");
        assertEquals(Outcome.SHORT, t.pick("p1", 0, 1));
        assertEquals(String.format(KeeperOarLines.SHORT, 13, 15), t.talk("t1"));
        assertEquals(Outcome.WELL, t.pick("p2", 1, 4));
        assertEquals(KeeperOarLines.THANKS, t.talk("t2"));
        assertNull(t.quest().currentStep());
        assertEquals(KeeperOarLines.DONE, t.talk("t3"));
    }
}
