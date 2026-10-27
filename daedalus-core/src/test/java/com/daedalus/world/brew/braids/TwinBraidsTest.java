// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.braids;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.braids.TwinBraids.Outcome;
import org.junit.jupiter.api.Test;

class TwinBraidsTest {
    /** Brute force: every subsequence of the left braid; the longest also found in the right braid. */
    static int brute(TwinBraids b) {
        String l = b.left();
        int best = 0;
        for (int mask = 0; mask < 1 << l.length(); mask++) {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < l.length(); i++) {
                if ((mask >> i & 1) == 1) {
                    sb.append(l.charAt(i));
                }
            }
            if (TwinBraids.within(sb.toString(), b.right())) {
                best = Math.max(best, sb.length());
            }
        }
        return best;
    }

    /** RGBRY and GRBYR share RBY, RBR, GBY, GBR (length 3); the matching first beads give only R or G. */
    static TwinBraids braids() {
        return new TwinBraids("RGBRY", "GRBYR");
    }

    @Test
    void seededBraidsAreDeterministic() {
        assertEquals(TwinBraids.seeded(1).left(), TwinBraids.seeded(1).left());
        assertEquals(TwinBraids.seeded(1).right(), TwinBraids.seeded(1).right());
        assertThrows(IllegalArgumentException.class, () -> new TwinBraids("RX", "R"));
        assertThrows(IllegalArgumentException.class, () -> new TwinBraids(null, "R"));
    }

    @Test
    void longestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            TwinBraids b = TwinBraids.seeded(seed);
            assertEquals(brute(b), b.longest(), "LCS == brute force, seed " + seed);
        }
    }

    @Test
    void touchingRunIsATrap() {
        TwinBraids b = braids();
        assertEquals(3, b.longest());
        assertEquals(Outcome.SHORT, b.name("n0", "RB"), "RB touches in both, but 3 beads can be shared");
        assertEquals(String.format(KeeperTwinBraids.SHORT, 2, 3), b.talk("t0"));
    }

    @Test
    void shortNotSharedAndNoCommonEarnNoCredit() {
        TwinBraids b = braids();
        b.compare("c");
        assertEquals(Outcome.NOT_SHARED, b.name("n1", "RGB"));
        assertEquals(KeeperTwinBraids.NOT_SHARED, b.talk("t1"));
        assertEquals(Outcome.MALFORMED, b.name("n2", "RQ"));
        assertEquals(Outcome.MALFORMED, b.name("n3", ""));
        assertEquals("name", b.quest().currentStep().type(), "no credit for a short or unshared run");
        TwinBraids none = new TwinBraids("RRG", "BYY");
        assertEquals(0, none.longest());
        assertEquals(Outcome.NO_COMMON, none.name("x", "R"));
        assertEquals(KeeperTwinBraids.NO_COMMON, none.talk("tx"));
    }

    @Test
    void guards() {
        TwinBraids b = braids();
        assertEquals(Outcome.IGNORED, b.name("", "RBY"));
        assertEquals(Outcome.IGNORED, b.name("e", null));
        assertEquals(Outcome.LONGEST, b.name("e1", "GBY"));
        assertEquals(Outcome.DUPLICATE, b.name("e1", "GBY"));
    }

    @Test
    void questShortThenLongestThenKeeper() {
        TwinBraids b = braids();
        assertEquals(String.format(KeeperTwinBraids.GREETING, "RGBRY", "GRBYR"), b.talk("t0"));
        b.compare("c0");
        assertEquals(Outcome.SHORT, b.name("n1", "RB"));
        assertEquals(Outcome.LONGEST, b.name("n2", "RBY"));
        assertEquals(KeeperTwinBraids.THANKS, b.talk("t2"));
        assertNull(b.quest().currentStep());
        assertEquals(KeeperTwinBraids.DONE, b.talk("t3"));
    }
}
