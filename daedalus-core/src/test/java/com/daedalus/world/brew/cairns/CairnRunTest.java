// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.cairns;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.cairns.CairnRun.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class CairnRunTest {
    /** Brute force: from every number found, extend upward while the next number was found. */
    static int brute(CairnRun c) {
        int best = 0;
        for (int start : c.found()) {
            int len = 0;
            while (c.found().contains(start + len)) {
                len++;
            }
            best = Math.max(best, len);
        }
        return best;
    }

    /** Found 5 1 3 2 9 4: run 1-5 is 5 long; walk order gives only 1. */
    static CairnRun fixture() {
        return new CairnRun(List.of(5, 1, 3, 2, 9, 4));
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(CairnRun.seeded(1).found(), CairnRun.seeded(1).found());
        assertEquals(CairnRun.seeded(1).run(), CairnRun.seeded(1).run());
        assertThrows(IllegalArgumentException.class, () -> new CairnRun(null));
        assertThrows(IllegalArgumentException.class, () -> new CairnRun(java.util.Arrays.asList(1, null)));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            CairnRun r = CairnRun.seeded(seed);
            assertEquals(brute(r), r.run(), "fast == brute force, seed " + seed);
            assertTrue(r.run() >= r.walkRun(), "walk order never beats the run, seed " + seed);
        }
    }

    @Test
    void trap() {
        CairnRun r = fixture();
        assertEquals(5, r.run());
        assertEquals(1, r.walkRun());
        assertEquals(Outcome.WRONG, r.count("c0", 1), "found order doesn't matter");
        assertEquals(String.format(KeeperCairnRun.WRONG, 1), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        CairnRun r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 5 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        CairnRun sp = new CairnRun(List.of());
        assertTrue(sp.none());
        assertEquals(Outcome.NONE, sp.count("x", 0));
        assertEquals(KeeperCairnRun.NONE, sp.talk("tx"));
    }

    @Test
    void guards() {
        CairnRun r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 5));
        assertEquals(Outcome.IGNORED, r.count(null, 5));
        assertEquals(Outcome.RIGHT, r.count("e1", 5));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 5));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        CairnRun r = fixture();
        assertEquals(String.format(KeeperCairnRun.GREETING, List.of(5, 1, 3, 2, 9, 4)), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 1));
        assertEquals(Outcome.RIGHT, r.count("c2", 5));
        assertEquals(KeeperCairnRun.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperCairnRun.DONE, r.talk("t3"));
    }
}
