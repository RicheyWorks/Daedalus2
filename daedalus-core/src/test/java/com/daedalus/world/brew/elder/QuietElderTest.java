// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.elder;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.elder.QuietElder.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class QuietElderTest {
    /** Brute force: check every islander against every other. */
    static int brute(QuietElder q) {
        int n = q.islanders();
        for (int c = 0; c < n; c++) {
            boolean ok = true;
            for (int i = 0; i < n; i++) {
                if (i != c && (q.knows(c, i) || !q.knows(i, c))) {
                    ok = false;
                }
            }
            if (ok) {
                return c;
            }
        }
        return QuietElder.NONE;
    }

    /** Four islanders; 2 knows no one and all know 2. Islander 0 is known by the most after 2 but knows 2. */
    static QuietElder fire() {
        return new QuietElder(List.of(List.of(2), List.of(0, 2), List.of(), List.of(0, 1, 2)));
    }

    @Test
    void seededGatheringIsDeterministic() {
        assertEquals(QuietElder.seeded(1).elder(), QuietElder.seeded(1).elder());
        assertEquals(QuietElder.seeded(1).islanders(), QuietElder.seeded(1).islanders());
        assertThrows(IllegalArgumentException.class, () -> new QuietElder(List.of()));
        assertThrows(IllegalArgumentException.class, () -> new QuietElder(List.of(List.of(0))));
    }

    @Test
    void elderMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            QuietElder q = QuietElder.seeded(seed);
            assertEquals(brute(q), q.elder(), "celebrity elimination == brute force, seed " + seed);
            assertTrue(q.questions() <= 3 * (q.islanders() - 1), "few questions, seed " + seed);
        }
    }

    @Test
    void wellKnownIsATrap() {
        QuietElder q = fire();
        assertEquals(2, q.elder());
        assertEquals(Outcome.WRONG, q.name("n0", 0), "0 is well known but knows 2");
        assertEquals(String.format(KeeperQuietElder.WRONG, 0), q.talk("t0"));
    }

    @Test
    void wrongAndNoElderEarnNoCredit() {
        QuietElder q = fire();
        q.gather("g");
        assertEquals(Outcome.WRONG, q.name("n1", 3));
        assertEquals(Outcome.MALFORMED, q.name("n2", 4));
        assertEquals("name", q.quest().currentStep().type(), "no credit for a wrong name");
        QuietElder none = new QuietElder(List.of(List.of(1), List.of(0), List.of(0, 1)));
        assertEquals(QuietElder.NONE, none.elder());
        assertEquals(Outcome.NO_ELDER, none.name("x", 0));
        assertEquals(KeeperQuietElder.NO_ELDER, none.talk("tx"));
    }

    @Test
    void guards() {
        QuietElder q = fire();
        assertEquals(Outcome.IGNORED, q.name("", 2));
        assertEquals(Outcome.IGNORED, q.name(null, 2));
        assertEquals(Outcome.MALFORMED, q.name("e0", -1));
        assertEquals(Outcome.FOUND, q.name("e1", 2));
        assertEquals(Outcome.DUPLICATE, q.name("e1", 2));
    }

    @Test
    void questWrongThenFoundThenKeeper() {
        QuietElder q = fire();
        assertEquals(String.format(KeeperQuietElder.GREETING, 4), q.talk("t0"));
        q.gather("g0");
        assertEquals(Outcome.WRONG, q.name("n1", 0));
        assertEquals(Outcome.FOUND, q.name("n2", 2));
        assertEquals(KeeperQuietElder.THANKS, q.talk("t2"));
        assertNull(q.quest().currentStep());
        assertEquals(KeeperQuietElder.DONE, q.talk("t3"));
    }
}
