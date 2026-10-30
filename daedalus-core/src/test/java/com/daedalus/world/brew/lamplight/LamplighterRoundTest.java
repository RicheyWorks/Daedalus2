// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lamplight;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.lamplight.LamplighterRound.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class LamplighterRoundTest {
    /** Brute force: walk the ring from every post in turn; the first that never runs dry. */
    static int brute(LamplighterRound r) {
        int n = r.posts();
        for (int s = 0; s < n; s++) {
            long tank = 0;
            boolean ok = true;
            for (int k = 0; k < n && ok; k++) {
                int i = (s + k) % n;
                tank += r.oil().get(i) - r.burn().get(i);
                ok = tank >= 0;
            }
            if (ok) {
                return s;
            }
        }
        return LamplighterRound.NONE;
    }

    /** Oil 1,2,3,4,5 and burn 3,4,5,1,2: only post 3 works; post 4 (most oil) runs dry. */
    static LamplighterRound ring() {
        return new LamplighterRound(List.of(1, 2, 3, 4, 5), List.of(3, 4, 5, 1, 2));
    }

    @Test
    void seededRingIsDeterministic() {
        assertEquals(LamplighterRound.seeded(1).oil(), LamplighterRound.seeded(1).oil());
        assertEquals(LamplighterRound.seeded(1).start(), LamplighterRound.seeded(1).start());
        assertThrows(IllegalArgumentException.class, () -> new LamplighterRound(List.of(), List.of()));
        assertThrows(IllegalArgumentException.class, () -> new LamplighterRound(List.of(1), List.of(1, 2)));
        assertThrows(IllegalArgumentException.class, () -> new LamplighterRound(List.of(-1), List.of(0)));
    }

    @Test
    void startMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            LamplighterRound r = LamplighterRound.seeded(seed);
            assertEquals(brute(r), r.start(), "circular greedy == brute force, seed " + seed);
        }
    }

    @Test
    void mostOilFirstIsATrap() {
        LamplighterRound r = ring();
        assertEquals(3, r.start());
        assertEquals(Outcome.DRY, r.name("n0", 4), "post 4 has the most oil but runs dry");
        assertEquals(String.format(KeeperLamplighter.DRY, 4), r.talk("t0"));
    }

    @Test
    void dryLaterAndShortEarnNoCredit() {
        LamplighterRound r = ring();
        r.walk("w");
        assertEquals(Outcome.DRY, r.name("n1", 0));
        assertEquals(Outcome.MALFORMED, r.name("n2", 5));
        assertEquals("start", r.quest().currentStep().type(), "no credit for a dry start");
        LamplighterRound easy = new LamplighterRound(List.of(2, 2, 2), List.of(1, 1, 1));
        assertEquals(Outcome.LATER, easy.name("e", 2));
        assertEquals(String.format(KeeperLamplighter.LATER, 2, 0), easy.talk("te"));
        LamplighterRound shortRing = new LamplighterRound(List.of(1, 1), List.of(1, 2));
        assertEquals(LamplighterRound.NONE, shortRing.start());
        assertEquals(Outcome.SHORT, shortRing.name("x", 0));
        assertEquals(KeeperLamplighter.SHORT, shortRing.talk("tx"));
    }

    @Test
    void guards() {
        LamplighterRound r = ring();
        assertEquals(Outcome.IGNORED, r.name("", 3));
        assertEquals(Outcome.IGNORED, r.name(null, 3));
        assertEquals(Outcome.MALFORMED, r.name("e0", -1));
        assertEquals(Outcome.FIRST, r.name("e1", 3));
        assertEquals(Outcome.DUPLICATE, r.name("e1", 3));
    }

    @Test
    void questDryThenFirstThenKeeper() {
        LamplighterRound r = ring();
        assertEquals(String.format(KeeperLamplighter.GREETING, 5), r.talk("t0"));
        r.walk("w0");
        assertEquals(Outcome.DRY, r.name("n1", 4));
        assertEquals(Outcome.FIRST, r.name("n2", 3));
        assertEquals(String.format(KeeperLamplighter.THANKS, 3), r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperLamplighter.DONE, r.talk("t3"));
    }
}
