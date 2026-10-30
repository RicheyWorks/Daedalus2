// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.tidemarks;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.tidemarks.TideMarks.Outcome;
import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

class TideMarksTest {
    /** Brute force: a set of every substring of the run length. */
    static int brute(TideMarks t) {
        Set<String> seen = new HashSet<>();
        for (int i = 0; i + t.len() <= t.marks().length(); i++) {
            seen.add(t.marks().substring(i, i + t.len()));
        }
        return seen.size();
    }

    /** Wall ababa, run length 2: runs ab and ba, but four stretches. */
    static TideMarks fixture() {
        return new TideMarks("ababa", 2);
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(TideMarks.seeded(1).marks(), TideMarks.seeded(1).marks());
        assertEquals(TideMarks.seeded(1).distinct(), TideMarks.seeded(1).distinct());
        assertThrows(IllegalArgumentException.class, () -> new TideMarks("ab", 0));
        assertThrows(IllegalArgumentException.class, () -> new TideMarks("A1", 1));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            TideMarks r = TideMarks.seeded(seed);
            assertEquals(brute(r), r.distinct(), "fast == brute force, seed " + seed);
            assertTrue(r.windows() >= r.distinct(), "stretches never fewer than runs, seed " + seed);
        }
    }

    @Test
    void trap() {
        TideMarks r = fixture();
        assertEquals(2, r.distinct());
        assertEquals(4, r.windows());
        assertEquals(Outcome.WRONG, r.count("c0", 4), "a repeated run is still one run");
        assertEquals(String.format(KeeperTideMarks.WRONG, 4), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        TideMarks r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 2 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        TideMarks sp = new TideMarks("ab", 3);
        assertTrue(sp.shortWall());
        assertEquals(Outcome.SHORT, sp.count("x", 0));
        assertEquals(KeeperTideMarks.SHORT, sp.talk("tx"));
    }

    @Test
    void guards() {
        TideMarks r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 2));
        assertEquals(Outcome.IGNORED, r.count(null, 2));
        assertEquals(Outcome.RIGHT, r.count("e1", 2));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 2));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        TideMarks r = fixture();
        assertEquals(String.format(KeeperTideMarks.GREETING, "ababa", 2), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 4));
        assertEquals(Outcome.RIGHT, r.count("c2", 2));
        assertEquals(KeeperTideMarks.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperTideMarks.DONE, r.talk("t3"));
    }
}
