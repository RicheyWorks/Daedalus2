// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.chantwords;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.chantwords.ChantWords.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class ChantWordsTest {
    /** Brute force: every word checked at every position of the chant. */
    static int brute(ChantWords c) {
        int n = 0;
        for (String w : c.words()) {
            for (int i = 0; i + w.length() <= c.chant().length(); i++) {
                if (c.chant().startsWith(w, i)) {
                    n++;
                }
            }
        }
        return n;
    }

    /** Chant aaab, words a, aa, ab: 6 blessings sung, 3 words found. */
    static ChantWords fixture() {
        return new ChantWords("aaab", List.of("a", "aa", "ab"));
    }

    @Test
    void seededIsDeterministic() {
        assertEquals(ChantWords.seeded(1).words(), ChantWords.seeded(1).words());
        assertEquals(ChantWords.seeded(1).total(), ChantWords.seeded(1).total());
        assertThrows(IllegalArgumentException.class, () -> new ChantWords("ab", List.of()));
        assertThrows(IllegalArgumentException.class, () -> new ChantWords("ab", List.of("a", "a")));
    }

    @Test
    void answerMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            ChantWords r = ChantWords.seeded(seed);
            assertEquals(brute(r), r.total(), "fast == brute force, seed " + seed);
            assertTrue(r.total() >= r.found(), "never fewer blessings than words found, seed " + seed);
        }
    }

    @Test
    void trap() {
        ChantWords r = fixture();
        assertEquals(6, r.total());
        assertEquals(3, r.found());
        assertEquals(Outcome.WRONG, r.count("c0", 3), "count every time, not which words");
        assertEquals(String.format(KeeperChantWords.WRONG, 3), r.talk("t0"));
    }

    @Test
    void wrongAndSpecialEarnNoCredit() {
        ChantWords r = fixture();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 6 + 1));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong answer");
        ChantWords sp = new ChantWords("ccc", List.of("a"));
        assertTrue(sp.silent());
        assertEquals(Outcome.SILENT, sp.count("x", 0));
        assertEquals(KeeperChantWords.SILENT, sp.talk("tx"));
    }

    @Test
    void guards() {
        ChantWords r = fixture();
        assertEquals(Outcome.IGNORED, r.count("", 6));
        assertEquals(Outcome.IGNORED, r.count(null, 6));
        assertEquals(Outcome.RIGHT, r.count("e1", 6));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 6));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        ChantWords r = fixture();
        assertEquals(String.format(KeeperChantWords.GREETING, "aaab", List.of("a", "aa", "ab")), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 3));
        assertEquals(Outcome.RIGHT, r.count("c2", 6));
        assertEquals(KeeperChantWords.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperChantWords.DONE, r.talk("t3"));
    }
}
